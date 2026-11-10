import importlib.util
from contextlib import closing
import io
from pathlib import Path
import sqlite3
import tempfile
import subprocess
import sys
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from backup_encryption import executable, sha256


def module(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parents[1] / "scripts" / (name + ".py"))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


worker = module("railway_backup_worker")
downloader = module("download_railway_backup")


class RailwayBackupTests(unittest.TestCase):
    def test_encrypted_roundtrip_and_tamper_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            connection = self.fixture(root)
            try:
                exported = io.StringIO()
                worker.export(root, exported)
            finally:
                connection.close()
            key = subprocess.run([executable("age-keygen")], capture_output=True, check=True).stdout
            public = subprocess.run([executable("age-keygen"), "-y"], input=key, capture_output=True, check=True).stdout.decode().strip()
            identity = root / "synthetic-test-key.txt"
            identity.write_bytes(key)
            encrypted = root / "backup.zip.age"
            checksum = downloader.receive_encrypted(io.BytesIO(exported.getvalue().encode()), encrypted, public)
            self.assertEqual(checksum, sha256(encrypted))
            self.assertTrue(encrypted.read_bytes().startswith(b"age-encryption.org/v1"))
            self.assertNotIn(b"synthetic photo", encrypted.read_bytes())
            self.assertFalse(zipfile.is_zipfile(encrypted))
            restored = root / "verified.zip"
            subprocess.run([executable(), "-d", "-i", str(identity), "-o", str(restored), str(encrypted)], check=True, capture_output=True)
            downloader.verify_archive(restored)
            damaged = bytearray(encrypted.read_bytes())
            damaged[-1] ^= 1
            encrypted.write_bytes(damaged)
            rejected = subprocess.run([executable(), "-d", "-i", str(identity), str(encrypted)], capture_output=True)
            self.assertNotEqual(rejected.returncode, 0)

    def test_invalid_encryption_recipient_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises((ValueError, OSError)):
                downloader.receive_encrypted(io.BytesIO(b""), Path(directory) / "partial.age", "invalid")

    def fixture(self, root):
        connection = sqlite3.connect(root / "db.sqlite3")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE example(value TEXT)")
        connection.execute("INSERT INTO example VALUES ('synthetic')")
        connection.commit()
        (root / "media").mkdir()
        (root / "media/photo.txt").write_text("synthetic photo")
        (root / ".django_secret_key").write_text("synthetic-secret")
        return connection

    def test_roundtrip_with_live_wal_and_hidden_key(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            connection = self.fixture(root)
            try:
                output = io.StringIO()
                worker.export(root, output)
                received = root / "received.zip"
                downloader.receive(io.BytesIO(output.getvalue().encode("ascii")), received)
                with zipfile.ZipFile(received) as archive:
                    self.assertEqual(archive.read(".django_secret_key"), b"synthetic-secret")
                    self.assertEqual(archive.read("media/photo.txt"), b"synthetic photo")
                    snapshot = root / "restored.sqlite3"
                    snapshot.write_bytes(archive.read("db.sqlite3"))
                with closing(sqlite3.connect(snapshot)) as restored:
                    self.assertEqual(restored.execute("SELECT value FROM example").fetchone(), ("synthetic",))
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM example").fetchone(), (1,))
            finally:
                connection.close()

    def test_truncated_transfer_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "incomplete"):
                downloader.receive(io.BytesIO(b'LAZUNA_HEADER {"bytes": 10, "sha256": "no"}\n'), Path(directory) / "partial")

    def test_corrupt_transfer_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            payload = b'LAZUNA_HEADER {"bytes": 1, "sha256": "incorrect"}\nLAZUNA_DATA YQ==\nLAZUNA_END\n'
            with self.assertRaisesRegex(ValueError, "corrupt"):
                downloader.receive(io.BytesIO(payload), Path(directory) / "partial")

    def test_missing_database_does_not_create_one(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "database_missing"):
                worker.export(directory, io.StringIO())
            self.assertFalse((Path(directory) / "db.sqlite3").exists())


if __name__ == "__main__":
    unittest.main()
