"""age-backed encryption helpers. Private keys and passwords never enter logs."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

CONFIG = Path.home() / ".config/lazuna-backup"
RECIPIENT = CONFIG / "recipient.txt"
IDENTITY = CONFIG / "identity.age"


def executable(name="age"):
    installed = shutil.which(name)
    bundled = Path(__file__).resolve().parents[1] / ".backup-tools/v1.3.2/age" / (name + ".exe")
    if installed:
        return installed
    if os.name == "nt" and bundled.is_file():
        return str(bundled)
    raise ValueError("Install official age and age-keygen first")


def recipient(path=RECIPIENT):
    value = path.read_text(encoding="ascii").strip()
    if not value.startswith("age1") or len(value) != 62 or not value.isalnum():
        raise ValueError("Invalid age recipient")
    # Ask age itself to validate the checksum before any network connection.
    subprocess.run([executable(), "-r", value], input=b"", stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, check=True, timeout=15)
    return value


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def setup():
    if IDENTITY.exists() or RECIPIENT.exists():
        raise ValueError("Existing configuration preserved; do not overwrite recovery keys")
    CONFIG.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.TemporaryDirectory(prefix=".setup-", dir=CONFIG) as temporary:
        root = Path(temporary)
        private = subprocess.run([executable("age-keygen")], capture_output=True, check=True).stdout
        public = subprocess.run([executable("age-keygen"), "-y"], input=private,
                                capture_output=True, check=True).stdout.decode("ascii").strip()
        encrypted_identity = root / "identity.age"
        print("Elegí una contraseña para la clave de recuperación y guardala en tu gestor.")
        subprocess.run([executable(), "-p", "-o", str(encrypted_identity)], input=private, check=True)
        del private
        probe = root / "probe.age"
        subprocess.run([executable(), "-r", public, "-o", str(probe)], input=b"Lazuna recovery check", check=True)
        print("Volvé a ingresar la contraseña para comprobar que la clave permite recuperar una copia.")
        recovered = subprocess.run([executable(), "-d", "-i", str(encrypted_identity), str(probe)],
                                   stdout=subprocess.PIPE, check=True).stdout
        if recovered != b"Lazuna recovery check":
            raise ValueError("Recovery verification failed")
        # Publish only after successful recovery; never store the plaintext identity.
        with IDENTITY.open("xb") as target:
            target.write(encrypted_identity.read_bytes())
        with RECIPIENT.open("x", encoding="ascii") as target:
            target.write(public + "\n")
    print("Clave cifrada configurada y recuperación comprobada:", IDENTITY)
    print("Conservá una copia de identity.age por separado y la contraseña en tu gestor.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["setup", "decrypt"])
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--identity", type=Path, default=IDENTITY)
    args = parser.parse_args()
    if args.action == "setup":
        setup()
        return
    if not args.input or not args.output or args.output.exists():
        parser.error("Choose an encrypted input and a new output file")
    from download_railway_backup import verify_archive
    # Decrypt only on explicit request. Output ZIP is sensitive and unencrypted.
    with tempfile.TemporaryDirectory(prefix=".decrypt-", dir=args.output.parent) as temporary:
        plain = Path(temporary) / "backup.zip"
        subprocess.run([executable(), "-d", "-i", str(args.identity), "-o", str(plain), str(args.input)], check=True)
        verify_archive(plain)
        with plain.open("rb") as source, args.output.open("xb") as target:
            shutil.copyfileobj(source, target)
    print("Recovered ZIP verified (unencrypted):", args.output)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError):
        print("Encryption/recovery failed. No success claimed; existing files preserved.")
        raise SystemExit(1)
