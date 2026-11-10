"""Portable SSH downloader; no password storage, no production writes or deletion."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tempfile
import threading
import uuid
import zipfile


def verify_archive(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("duplicate_members")
        for name in names:
            if "\\" in name or ":" in name or PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts:
                raise ValueError("invalid_member")
        manifest = json.loads(archive.read("backup-manifest.json"))
        if manifest.get("format") != 1 or set(names) != set(manifest["files"]) | {"backup-manifest.json"} or "db.sqlite3" not in names:
            raise ValueError("invalid_manifest")
        for name, expected in manifest["files"].items():
            digest = hashlib.sha256()
            with archive.open(name) as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != expected:
                raise ValueError("member_checksum")


def receive(stream, destination):
    header = None
    ended = False
    digest = hashlib.sha256()
    size = 0
    with destination.open("xb") as output:
        for line in stream:
            if line.startswith(b"LAZUNA_HEADER "):
                if header is not None:
                    raise ValueError("duplicate_header")
                header = json.loads(line[len(b"LAZUNA_HEADER "):])
            elif line.startswith(b"LAZUNA_DATA "):
                if header is None or ended:
                    raise ValueError("invalid_stream")
                chunk = base64.b64decode(line[len(b"LAZUNA_DATA "):].strip(), validate=True)
                size += len(chunk)
                if size > header["bytes"]:
                    raise ValueError("oversized_stream")
                output.write(chunk)
                digest.update(chunk)
            elif line.strip() == b"LAZUNA_END":
                if ended:
                    raise ValueError("duplicate_end")
                ended = True
            # Railway CLI status lines never enter the ZIP or terminal output.
        output.flush()
        os.fsync(output.fileno())
    if not ended or header is None or size != header["bytes"] or digest.hexdigest() != header["sha256"]:
        raise ValueError("incomplete_or_corrupt_download")
    verify_archive(destination)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity", type=Path, default=Path.home() / ".ssh/railway_lazuna")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "Respaldos/Railway")
    parser.add_argument("--copy-to", type=Path, help="Existing directory on the external disk")
    parser.add_argument("--unattended", action="store_true", help="Fail instead of asking SSH for a password; requires an unlocked SSH agent")
    args = parser.parse_args()
    if not args.identity.is_file():
        parser.error("SSH identity file missing")
    if args.copy_to and not args.copy_to.is_dir():
        parser.error("External destination must exist; connect the disk first")
    railway = shutil.which("railway")
    if not railway:
        parser.error("Railway CLI missing")
    railway_command = [railway]
    if os.name == "nt" and Path(railway).suffix.lower() in {".cmd", ".bat"}:
        # Invoke npm's JS entry directly; never pass task arguments through cmd.exe.
        entry = Path(railway).parent / "node_modules/@railway/cli/bin/railway.js"
        node = shutil.which("node")
        if not entry.is_file() or not node:
            parser.error("Railway npm entry or Node missing")
        railway_command = [node, str(entry)]
    ssh = shutil.which("ssh")
    if not ssh:
        parser.error("OpenSSH missing")
    args.output.mkdir(parents=True, exist_ok=True, mode=0o700)
    filename = "lazuna-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8] + ".zip"
    destination = args.output / filename
    worker = base64.b64encode(Path(__file__).with_name("railway_backup_worker.py").read_bytes()).decode("ascii")
    remote = 'python -c "import base64;exec(base64.b64decode(\'' + worker + '\'))"'
    config_command = railway_command + ["ssh", "config", "--project", "4138ec85-74ef-44ec-a13c-6e4493cc0574",
               "--service", "b68fee13-87f2-4ea8-a1e0-90dfc5d3cce0", "--environment",
               "e1d83081-7ce3-4829-8184-7d8864ed46a1", "-i", str(args.identity), "--dry-run"]
    config = subprocess.run(config_command, capture_output=True, text=True, timeout=60, check=True)
    fields = {}
    for line in config.stdout.splitlines():
        parts = line.strip().split()
        if len(parts) == 2 and parts[0] in {"HostName", "User"}:
            if parts[0] in fields:
                raise ValueError("ambiguous_ssh_config")
            fields[parts[0]] = parts[1]
    if fields.get("HostName") != "ssh.railway.com":
        raise ValueError("unexpected_ssh_host")
    target_user = str(uuid.UUID(fields.get("User", "")))
    command = [ssh, "-T", "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=20",
               "-o", "ServerAliveInterval=30", "-o", "ServerAliveCountMax=3",
               "-o", "IdentitiesOnly=yes", "-i", str(args.identity)]
    if args.unattended:
        command += ["-o", "BatchMode=yes"]
    command += [target_user + "@ssh.railway.com", remote]
    with tempfile.TemporaryDirectory(prefix=".download-", dir=args.output) as temporary:
        partial = Path(temporary) / "backup.part"
        process = subprocess.Popen(command, stdout=subprocess.PIPE)
        timer = threading.Timer(900, process.kill)
        timer.start()
        try:
            checksum = receive(process.stdout, partial)
            if process.wait(timeout=30) != 0:
                raise ValueError("ssh_failed")
        finally:
            timer.cancel()
            if process.poll() is None:
                process.kill()
                process.wait()
            process.stdout.close()
        partial.rename(destination)
    destination.with_suffix(".zip.sha256").write_text(checksum + "  " + filename + "\n", encoding="ascii")
    print("Verified local backup:", destination)
    if args.copy_to:
        # Publish only a verified, complete secondary copy. Never delete old backups.
        with tempfile.TemporaryDirectory(prefix=".lazuna-copy-", dir=args.copy_to) as temporary:
            copy = Path(temporary) / filename
            shutil.copyfile(destination, copy)
            with copy.open("rb") as source:
                digest = hashlib.sha256()
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != checksum:
                raise ValueError("external_copy_checksum")
            copy.rename(args.copy_to / filename)
        shutil.copyfile(destination.with_suffix(".zip.sha256"), args.copy_to / (filename + ".sha256"))
        print("Verified external copy completed.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError):
        print("Backup failed. No success claimed; existing backups are preserved.")
        raise SystemExit(1)
