import importlib.util
from contextlib import closing
import io
from pathlib import Path
import sqlite3
import tempfile
import unittest
import zipfile


def module(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parents[1] / "scripts" / (name + ".py"))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


worker = module("railway_backup_worker")
downloader = module("download_railway_backup")


class RailwayBackupTests(unittest.TestCase):
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
