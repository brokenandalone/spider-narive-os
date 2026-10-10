"""Offline confirmation and versioning tests for school OneDrive handoff."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PyQt5.QtWidgets import QApplication, QMessageBox
from study.school_upload import SchoolDraftUploadDialog, versioned_upload_path

app = QApplication.instance() or QApplication([])


class SchoolDraftUploadTests(unittest.TestCase):
    def test_remote_filename_has_a_unique_version_and_course_path(self):
        name = versioned_upload_path("SOC-112/Module 6", "Essay with spaces.docx",
                                     timestamp="20261010T163000Z", token="deadbeef")
        self.assertEqual(name, "SOC-112/Module 6/Essay-with-spaces-20261010T163000Z-deadbeef.docx")
        self.assertNotIn("webbie_onedrive", name)
        with self.assertRaises(ValueError):
            versioned_upload_path("../other", "Essay.docx",
                                  timestamp="20261010T163000Z", token="abcd1234")
        with self.assertRaises(ValueError):
            versioned_upload_path("", "Essay.pdf",
                                  timestamp="20261010T163000Z", token="abcd1234")

    def test_upload_requires_confirmed_school_account_and_explicit_approval(self):
        with tempfile.TemporaryDirectory() as root:
            file = Path(root) / "paper.docx"
            file.write_bytes(b"Word-test-file")
            with patch("study.school_onedrive.remote_ready", return_value=False):
                dialog = SchoolDraftUploadDialog(None, root, file)
                dialog.upload_export()
                self.assertIn("Connect", dialog.status.text())
                dialog.close()
            with patch("study.school_onedrive.remote_ready", return_value=True), \
                 patch("study.school_upload.remote_ready", return_value=True):
                dialog = SchoolDraftUploadDialog(None, root, file)
                dialog.remote_folder = "PSY-328"
                with patch("study.school_upload.QMessageBox.question",
                           return_value=QMessageBox.No), \
                     patch("study.school_upload.QProcess") as process:
                    dialog.upload_export()
                    process.assert_not_called()
                    self.assertIn("cancelled", dialog.status.text())
                dialog.close()

    def test_confirmed_upload_uses_single_copy_and_non_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            file = Path(root) / "paper.docx"
            file.write_bytes(b"Word-test-file")
            with patch("study.school_onedrive.remote_ready", return_value=True), \
                 patch("study.school_upload.remote_ready", return_value=True):
                dialog = SchoolDraftUploadDialog(None, root, file)
                dialog.remote_folder = "SOC-112/Module 6"
                with patch("study.school_upload.QMessageBox.question",
                           return_value=QMessageBox.Yes), \
                     patch("study.school_upload.QProcess") as process_class:
                    proc = process_class.return_value
                    dialog.upload_export()
                    args = proc.setArguments.call_args.args[0]
                    self.assertEqual(args[0:2], ["copyto", str(file)])
                    self.assertTrue(args[2].startswith(
                        "school_onedrive:SOC-112/Module 6/paper-"))
                    self.assertIn("--ignore-existing", args)
                    self.assertNotIn("--delete-excluded", args)
                    proc.start.assert_called_once()
                dialog.process = None
                dialog.close()


if __name__ == "__main__":
    unittest.main()
