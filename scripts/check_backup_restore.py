"""Offline restoration drill. Run only in the isolated container in BACKUPS.md.

Never mounts or writes a live data volume. Does not print records or secrets.
"""
import hashlib
import json
import os
import shutil
from pathlib import Path, PurePosixPath
import sqlite3
import stat
import subprocess
import tempfile
import zipfile


def drill(archive):
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix="lazuna-restore-") as temporary:
        root = Path(temporary)
        with zipfile.ZipFile(archive) as backup:
            entries = backup.infolist()
            if len(entries) > 100000 or sum(e.file_size for e in entries) > 256 * 1024**2:
                raise ValueError("archive_limits")
            seen = set()
            for entry in entries:
                name = entry.filename.replace("\\", "/")
                path = PurePosixPath(name)
                mode = entry.external_attr >> 16
                if (not name or ":" in name or path.is_absolute()
                        or ".." in path.parts or str(path) in seen
                        or stat.S_ISLNK(mode) or entry.flag_bits & 1):
                    raise ValueError("unsupported_archive_entry")
                seen.add(str(path))
            # Validation precedes all extraction; root is a fresh private directory.
            for entry in entries:
                target = root / entry.filename.replace("\\", "/")
                if entry.is_dir() or entry.filename.endswith("\\"):
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with backup.open(entry) as source, target.open("xb") as destination:
                        shutil.copyfileobj(source, destination)
        database = root / "db.sqlite3"
        if not database.is_file():
            raise ValueError("database_missing")
        with sqlite3.connect(database) as connection:
            if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise ValueError("database_integrity")
            if connection.execute("PRAGMA foreign_key_check").fetchone():
                raise ValueError("database_foreign_keys")
        media = root / "media"
        media_count = sum(p.is_file() for p in media.rglob("*")) if media.exists() else 0
        env = dict(os.environ, DJANGO_DB_PATH=str(database), DJANGO_MEDIA_ROOT=str(media),
                   DJANGO_SECRET_KEY="isolated-drill-only-not-a-production-secret",
                   DJANGO_ALLOWED_HOSTS="testserver,localhost", DJANGO_DEBUG="0",
                   DJANGO_SERVE_MEDIA="1")
        for command in (["migrate", "--noinput"], ["check"], ["collectstatic", "--noinput"]):
            result = subprocess.run(["python", "manage.py", *command], env=env,
                                    capture_output=True, timeout=120)
            if result.returncode:
                raise ValueError("django_" + command[0] + "_failed")
        smoke = (
            "from django.test import Client; "
            "r=Client().get('/cuenta/ingresar/', secure=True); "
            "assert r.status_code == 200, 'login_not_available'"
        )
        result = subprocess.run(["python", "manage.py", "shell", "-c", smoke],
                                env=env, capture_output=True, timeout=30)
        if result.returncode:
            raise ValueError("login_smoke_failed")
        with sqlite3.connect(database) as connection:
            if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise ValueError("post_migration_integrity")
            if connection.execute("PRAGMA foreign_key_check").fetchone():
                raise ValueError("post_migration_foreign_keys")
        print(json.dumps({"result": "ok", "archive_sha256": digest,
                          "archive_files": len(entries), "media_files": media_count,
                          "persisted_secret_present": (root / ".django_secret_key").is_file(),
                          "migrations": "ok", "django_check": "ok", "login_http": 200}))


if __name__ == "__main__":
    try:
        drill(Path("/backup.zip"))
    except Exception as error:
        # Fixed categories only: no record contents, paths from archive or secrets.
        allowed = {"archive_limits", "unsupported_archive_entry", "database_missing",
                   "database_integrity", "database_foreign_keys", "django_migrate_failed",
                   "django_check_failed", "django_collectstatic_failed", "login_smoke_failed", "post_migration_integrity",
                   "post_migration_foreign_keys"}
        category = str(error) if isinstance(error, ValueError) and str(error) in allowed else "invalid_backup_or_runtime"
        print(json.dumps({"result": "failed", "category": category}))
        raise SystemExit(1)
