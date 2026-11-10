"""Read-only Railway export worker, sent over authenticated SSH by the downloader."""
import base64
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import zipfile


def export(data, stream):
    data = Path(data).resolve()
    database = data / "db.sqlite3"
    if not database.is_file() or database.is_symlink():
        raise ValueError("database_missing_or_link")
    deadline = time.monotonic() + 180

    def progress(status, remaining, total):
        if time.monotonic() > deadline:
            raise TimeoutError("snapshot_timeout")

    with tempfile.TemporaryDirectory(prefix="lazuna-export-") as temporary:
        snapshot = Path(temporary) / "db.sqlite3"
        with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as source:
            with closing(sqlite3.connect(snapshot)) as target:
                source.backup(target, pages=256, progress=progress)
                if target.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                    raise ValueError("database_integrity")
        archive = Path(temporary) / "backup.zip"
        files = [(snapshot, "db.sqlite3")]
        media = data / "media"
        if media.is_symlink():
            raise ValueError("media_link")
        if media.exists():
            for folder, directories, names in os.walk(media, followlinks=False):
                for name in directories + names:
                    path = Path(folder) / name
                    if path.is_symlink():
                        raise ValueError("media_link")
                    if path.is_file():
                        files.append((path, path.relative_to(data).as_posix()))
        secret = data / ".django_secret_key"
        if secret.is_symlink():
            raise ValueError("secret_link")
        if secret.is_file():
            files.append((secret, secret.name))
        manifest = {}
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
            for path, name in files:
                before = path.stat()
                digest = hashlib.sha256()
                with path.open("rb") as source, output.open(name, "w", force_zip64=True) as target:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        target.write(chunk)
                        digest.update(chunk)
                after = path.stat()
                if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
                    raise ValueError("file_changed_retry")
                manifest[name] = digest.hexdigest()
            output.writestr("backup-manifest.json", json.dumps({"format": 1, "files": manifest}))
        digest = hashlib.sha256()
        with archive.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        stream.write("LAZUNA_HEADER " + json.dumps({"sha256": digest.hexdigest(), "bytes": archive.stat().st_size}) + "\n")
        with archive.open("rb") as source:
            for chunk in iter(lambda: source.read(49152), b""):
                stream.write("LAZUNA_DATA " + base64.b64encode(chunk).decode("ascii") + "\n")
        stream.write("LAZUNA_END\n")
        stream.flush()


if __name__ == "__main__":
    import sys
    try:
        export("/data", sys.stdout)
    except Exception:
        print("Backup export failed; retry or inspect server locally.", file=sys.stderr)
        raise SystemExit(1)
