"""Offscreen cognitive center and sleep-revoke tests; no camera or network."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"the-web/shell"))
try:
    from PyQt5.QtWidgets import QApplication, QPushButton
    from webbie_cognitive_center import WebbieCognitiveDialog
    from webbie_panel import WebbiePanel
    QT=True
except ImportError:
    QT=False


@unittest.skipUnless(QT,"PyQt5 needed for native Webbie cognitive control tests")
class CognitiveCenterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def test_control_center_buttons_and_local_only_default(self):
        center=WebbieCognitiveDialog(workspace_callback=lambda:"studio")
        try:
            for identifier in (
                "webbieFocusTaskButton","webbieInspectModelsButton",
                "webbiePrivateSessionButton","webbieClearRecentChatButton",
                "webbieSensitiveStopButton"):
                button=center.findChild(QPushButton,identifier)
                self.assertIsNotNone(button)
            self.assertIn("No PC task has been executed",
                          center.report.toPlainText())
        finally:
            center.close()

    def test_sleep_revokes_desktop_grant_and_turns_camera_off(self):
        mock=SimpleNamespace(
            awareness=SimpleNamespace(sleep=Mock()),
            computer_dialog=SimpleNamespace(stop=Mock()),
            stop_camera=Mock(),
            face=SimpleNamespace(sleeping=False,update=Mock()),
            refresh_state=Mock(),
        )
        WebbiePanel.set_face_sleeping(mock,True)
        mock.computer_dialog.stop.assert_called_once()
        mock.stop_camera.assert_called_once()
        mock.awareness.sleep.assert_called_once_with(True)
        self.assertTrue(mock.face.sleeping)

    def test_stop_sensitive_invokes_parent_action_only_on_confirm(self):
        callback=Mock()
        center=WebbieCognitiveDialog(workspace_callback=lambda:"default",
                                     emergency_callback=callback)
        try:
            from PyQt5.QtWidgets import QMessageBox
            with patch("webbie_cognitive_center.QMessageBox.question",
                       return_value=QMessageBox.No):
                center.stop_sensitive()
            callback.assert_not_called()
            with patch("webbie_cognitive_center.QMessageBox.question",
                       return_value=QMessageBox.Yes):
                center.stop_sensitive()
            callback.assert_called_once()
        finally:
            center.close()

    def test_model_inventory_wiring_does_not_download(self):
        center=WebbieCognitiveDialog(workspace_callback=lambda:"default")
        try:
            with patch("webbie_cognitive_center.configured_choice",
                       return_value="qwen3:8b"),patch(
                       "webbie_cognitive_center.inspect_local_models",
                       return_value={
                            "online":True,"installed":["qwen3:8b"],
                            "running":[],"brain":{"requested":"qwen3:8b",
                                                 "ready":True},
                            "vision":{"requested":"qwen3:8b","ready":True},
                       }):
                worker=center.model_worker
                # Exercise diagnostics synchronously, not a real QThread.
                from webbie_cognitive_center import ModelInventoryWorker
                item=ModelInventoryWorker()
                messages=[]
                item.finishedReport.connect(messages.append)
                item.run()
                self.assertIn("qwen3:8b",messages[0])
        finally:
            center.close()


if __name__=="__main__":
    unittest.main()
