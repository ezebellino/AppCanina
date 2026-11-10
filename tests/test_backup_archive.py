"""Negative cases for the offline drill; no Docker or real records required."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location(
    "backup_drill", Path(__file__).resolve().parents[1] / "scripts/check_backup_restore.py")
drill = importlib.util.module_from_spec(spec)
spec.loader.exec_module(drill)


class ArchiveValidationTests(unittest.TestCase):
    def reject(self, names, category):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "test.zip"
            with zipfile.ZipFile(archive, "w") as output:
                for name in names:
                    output.writestr(name, b"not a real database")
            with self.assertRaisesRegex(ValueError, category):
                drill.drill(archive)

    def test_traversal(self):
        self.reject(["../outside"], "unsupported_archive_entry")

    def test_windows_traversal(self):
        self.reject(["..\\outside"], "unsupported_archive_entry")

    def test_absolute(self):
        self.reject(["/outside"], "unsupported_archive_entry")

    def test_normalized_collision(self):
        self.reject(["media/photo", "media\\photo"], "unsupported_archive_entry")

    def test_missing_database(self):
        self.reject(["media/photo"], "database_missing")


if __name__ == "__main__":
    unittest.main()
