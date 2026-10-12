"""Offscreen JARVIS Workflow Board controls require deliberate GUI clicks."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "the-web/shell"))
try:
    from PyQt5.QtWidgets import QApplication, QMessageBox
    from webbie_workflow_dialog import WebbieWorkflowDialog
    QT = True
except ImportError:
    QT = False


@unittest.skipUnless(QT, "Python Qt dependencies needed")
class WorkflowDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make_dialog(self, opener=None):
        d = WebbieWorkflowDialog(workspace_opener=opener)
        self.addCleanup(d.close)
        return d

    def test_preview_has_no_side_effect_or_implicit_start(self):
        opened = Mock()
        d = self.make_dialog(opened)
        self.assertFalse(d.session.status()["active"])
        self.assertFalse(d.open_button.isEnabled())
        self.assertIn("Preview only", d.details.toPlainText())
        d.templates.setCurrentIndex(1)
        self.assertFalse(d.session.status()["active"])
        opened.assert_not_called()

    def test_refusing_start_never_opens_workspace(self):
        opened = Mock()
        d = self.make_dialog(opened)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.No):
            d.start_button.click()
        self.assertFalse(d.session.status()["active"])
        opened.assert_not_called()

    def test_only_owner_click_requests_selected_fixed_workspace(self):
        opened = Mock()
        d = self.make_dialog(opened)
        d.templates.setCurrentIndex(1)   # School
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            d.start_button.click()
        self.assertEqual(d.session.status()["workspace"], "study")
        opened.assert_not_called()
        d.open_button.click()
        opened.assert_called_once_with("study")
        d.complete_button.click()
        self.assertEqual(d.session.status()["workspace"], "deep-forage")
        opened.assert_called_once()
        d.open_button.click()
        self.assertEqual(opened.call_args.args, ("deep-forage",))
        self.assertEqual(opened.call_count, 2)

    def test_no_callback_means_no_program_open_and_no_false_success(self):
        d = self.make_dialog()
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            d.start_button.click()
        self.assertFalse(d.open_button.isEnabled())
        self.assertTrue(d.complete_button.isEnabled())

    def test_failing_workspace_request_does_not_complete_step(self):
        opened = Mock(side_effect=RuntimeError("not present"))
        d = self.make_dialog(opened)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            d.start_button.click()
        d.open_button.click()
        self.assertEqual(d.session.status()["step"], 1)
        self.assertIn("Could not request", d.state_label.text())

    def test_stop_and_close_cancel_without_any_automation(self):
        opened = Mock()
        d = self.make_dialog(opened)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            d.start_button.click()
        d.stop_button.click()
        self.assertFalse(d.session.status()["active"])
        self.assertFalse(d.open_button.isEnabled())
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            d.start_button.click()
        d.close()
        self.assertFalse(d.session.status()["active"])
        opened.assert_not_called()

    def test_wiring_remains_parent_gui_only(self):
        shell = (ROOT / "the-web/shell/main.py").read_text()
        portrait = (ROOT / "the-web/shell/webbie_panel.py").read_text()
        cognitive = (ROOT / "the-web/shell/webbie_cognitive_center.py").read_text()
        self.assertIn("workspace_navigator = self.open_workspace", shell)
        self.assertIn("workspace_opener=getattr(self, 'workspace_navigator', None)", portrait)
        self.assertIn('"webbieWorkflowBoardButton"', cognitive)
        self.assertIn("WebbieWorkflowDialog", cognitive)


if __name__ == "__main__":
    unittest.main()
