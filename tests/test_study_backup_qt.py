"""Native UI smoke for Study backup, without touching a real database."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from unittest.mock import patch
import unittest
from PyQt5.QtWidgets import QApplication
from study.study_backup_ui import StudyBackupDialog, BackupWorker

app = QApplication.instance() or QApplication([])


class BackupPanelQtTests(unittest.TestCase):
    def test_panel_displays_private_storage_warning(self):
        panel = StudyBackupDialog()
        self.assertIn("private", panel.windowTitle().lower())
        self.assertIn("Ready", panel.status.text())
        panel.close()

    def test_verification_worker_reports_validation_only(self):
        worker = BackupWorker("verify", "/nonexistent/archive.zip")
        messages = []
        worker.failed.connect(messages.append)
        worker.run()
        self.assertEqual(len(messages), 1)
        self.assertIn("ZIP", messages[0])


if __name__ == "__main__":
    unittest.main()
