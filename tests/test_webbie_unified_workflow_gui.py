"""Offscreen Webbie brain/eyes/hands workflow GUI; no real desktop actions."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"the-web/shell"))
sys.path.insert(0,str(ROOT/"webbie/brain"))
try:
    from PyQt5.QtWidgets import QApplication,QMessageBox,QPushButton
    from webbie_unified_workflow import WebbieUnifiedWorkflowDialog
    from unified_workflow import UnifiedWorkflow
    QT=True
except ImportError:
    QT=False

TASK={"id":"f"*32,"workspace":"studio","title":"Broken Sorrow vocal mix",
      "next_step":"Review active session","status":"active"}

@unittest.skipUnless(QT,"PyQt5 needed for Webbie guided workflow tests")
class GuidedWorkflowUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def test_buttons_and_stage_restrictions(self):
        state=UnifiedWorkflow()
        open_pc=Mock()
        stop=Mock()
        dialog=WebbieUnifiedWorkflowDialog(
            session=state,workspace_callback=lambda:"studio",
            computer_callback=open_pc,stop_callback=stop)
        try:
            for name in ("webbieWorkflowStart","webbieWorkflowComputer",
                         "webbieWorkflowVerify","webbieWorkflowStop"):
                self.assertIsNotNone(dialog.findChild(QPushButton,name))
            self.assertFalse(dialog.confirm_button.isEnabled())
            self.assertFalse(dialog.open_button.isEnabled())
            dialog.open_computer()
            open_pc.assert_not_called()
            with patch("webbie_unified_workflow.current_focus",return_value=TASK):
                dialog.start_task()
            self.assertIn("OBSERVE",dialog.report.toPlainText())
            self.assertTrue(dialog.open_button.isEnabled())
            dialog.open_computer()
            open_pc.assert_called_once()
            self.assertFalse(dialog.confirm_button.isEnabled())
            state.observed_window(from_consented_gui=True,workspace="studio")
            state.record_action("application","requested",
                                from_control_gui=True,workspace="studio")
            dialog.refresh()
            self.assertTrue(dialog.confirm_button.isEnabled())
            self.assertIn("Owner confirmed completion: NO",dialog.report.toPlainText())
            with patch("webbie_unified_workflow.QMessageBox.question",
                       return_value=QMessageBox.No):
                dialog.confirm()
            self.assertEqual(state.snapshot()["phase"],"verify")
            with patch("webbie_unified_workflow.QMessageBox.question",
                       return_value=QMessageBox.Yes):
                dialog.confirm()
            self.assertEqual(state.snapshot()["phase"],"done")
        finally:
            dialog.close()
        stop.assert_called_once()

    def test_stop_revokes_sensitive_permission(self):
        state=UnifiedWorkflow()
        stop=Mock()
        dialog=WebbieUnifiedWorkflowDialog(
            session=state,workspace_callback=lambda:"studio",
            stop_callback=stop)
        try:
            with patch("webbie_unified_workflow.current_focus",return_value=TASK):
                dialog.start_task()
            dialog.cancel()
            self.assertEqual(state.snapshot()["phase"],"canceled")
            stop.assert_called_once()
            dialog.confirm()
            self.assertFalse(state.snapshot()["completed"])
        finally:
            dialog.close()
        self.assertEqual(stop.call_count,2)

    def test_no_focus_task_means_no_system_action(self):
        state=UnifiedWorkflow()
        open_pc=Mock()
        dialog=WebbieUnifiedWorkflowDialog(
            session=state,workspace_callback=lambda:"author",
            computer_callback=open_pc)
        try:
            with patch("webbie_unified_workflow.current_focus",return_value=None):
                dialog.start_task()
            self.assertIn("No active focus task",dialog.report.toPlainText())
            self.assertEqual(state.snapshot()["phase"],"idle")
            dialog.open_computer()
            open_pc.assert_not_called()
        finally:
            dialog.close()

    def test_computer_control_emits_redacted_outcome_signal(self):
        from webbie_computer_panel import WebbieComputerDialog
        self.assertTrue(hasattr(WebbieComputerDialog,"actionOutcome"))

    def test_source_wiring_never_submits_llm_commands_as_approval(self):
        source=(ROOT/"the-web/shell/webbie_panel.py").read_text()
        self.assertIn("actionOutcome.connect(",source)
        self.assertIn("screenObserved.connect(",source)
        self.assertIn("from_consented_gui=True",source)
        self.assertIn("from_control_gui=True",source)
        self.assertIn("self.unified_workflow.stop()",source)

if __name__=="__main__":
    unittest.main()
