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
    from PyQt5.QtGui import QPixmap, QImage, QPainter
    from PyQt5.QtCore import Qt
    from webbie_cognitive_center import WebbieCognitiveDialog
    from webbie_panel import WebbiePanel, SpeakingPortrait
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
                "webbieReadinessButton",
                "webbieUnifiedWorkflowCognitiveButton",
                "webbieVoiceLabButton", "webbieHearingTestButton",
                "webbiePrivateSessionButton","webbieClearRecentChatButton",
                "webbieSensitiveStopButton"):
                button=center.findChild(QPushButton,identifier)
                self.assertIsNotNone(button)
            self.assertIn("No PC task has been executed",
                          center.report.toPlainText())
        finally:
            center.close()

    def test_preserved_owner_workflow_slots_are_distinct_from_workspace_getter(self):
        opened = Mock()
        guided = Mock()
        getter = Mock(return_value="studio")
        center = WebbieCognitiveDialog(
            workspace_callback=getter, workspace_opener=opened,
            workflow_callback=guided)
        try:
            self.assertIs(center.workspace_opener, opened)
            self.assertIsNone(center.workflow_dialog)
            self.assertEqual(center.workspace_callback(), "studio")
            center.open_workflow()
            guided.assert_called_once_with()
            opened.assert_not_called()
            # Old workspace-opener and active supervised workflow slots can
            # coexist without triggering any navigation on constructor entry.
        finally:
            center.close()

    def test_cognitive_does_not_treat_workspace_getter_as_navigation_grant(self):
        getter = Mock(return_value="webbie")
        center = WebbieCognitiveDialog(workspace_callback=getter)
        try:
            self.assertIsNone(center.workspace_opener)
            self.assertIsNone(center.workflow_dialog)
        finally:
            center.close()

    def test_stop_sensitive_verifies_persisted_pause_after_stopping_each_surface(self):
        state = {"authorized": True, "paused": False}
        def pause(action):
            self.assertEqual(action, "pause")
            state["paused"] = True
        fake = SimpleNamespace(
            unified_workflow=SimpleNamespace(stop=Mock()),
            jarvis_mission_dialog=SimpleNamespace(core=SimpleNamespace(stop=Mock())),
            computer_dialog=SimpleNamespace(stop=Mock()),
            stop_camera=Mock(),
            awareness=SimpleNamespace(revoke_observation=Mock()),
            publish_jarvis_context=Mock(),
            append_message=Mock(),
        )
        with patch("webbie_panel.read_policy",
                   side_effect=lambda: dict(state)) as read, patch(
                       "webbie_panel.update_policy", side_effect=pause) as change:
            WebbiePanel.stop_sensitive_actions(fake)
        fake.unified_workflow.stop.assert_called_once()
        fake.jarvis_mission_dialog.core.stop.assert_called_once()
        fake.computer_dialog.stop.assert_called_once()
        fake.stop_camera.assert_called_once()
        fake.awareness.revoke_observation.assert_called_once_with("screen")
        fake.publish_jarvis_context.assert_called_once()
        self.assertGreaterEqual(read.call_count, 2)
        change.assert_called_once_with("pause")
        self.assertEqual(fake.append_message.call_args.args[0], "Webbie")
        self.assertIn("STOP confirmed", fake.append_message.call_args.args[1])

    def test_stop_sensitive_never_false_confirms_failed_persistence(self):
        state = {"authorized": True, "paused": False}
        fake = SimpleNamespace(
            unified_workflow=SimpleNamespace(stop=Mock()),
            jarvis_mission_dialog=None,
            computer_dialog=None,
            stop_camera=Mock(),
            awareness=SimpleNamespace(revoke_observation=Mock()),
            publish_jarvis_context=Mock(),
            append_message=Mock(),
        )
        with patch("webbie_panel.read_policy",
                   side_effect=lambda: dict(state)), patch(
                       "webbie_panel.update_policy",
                       side_effect=PermissionError("private permission failure")):
            WebbiePanel.stop_sensitive_actions(fake)
        fake.stop_camera.assert_called_once()
        fake.awareness.revoke_observation.assert_called_once_with("screen")
        self.assertEqual(fake.append_message.call_args.args[0], "Security")
        self.assertIn("NOT verified", fake.append_message.call_args.args[1])

    def test_stop_sensitive_attempts_remaining_surfaces_after_individual_failures(self):
        state = {"authorized": False, "paused": True}
        fake = SimpleNamespace(
            unified_workflow=SimpleNamespace(
                stop=Mock(side_effect=RuntimeError("workflow busy"))),
            jarvis_mission_dialog=SimpleNamespace(core=SimpleNamespace(stop=Mock())),
            computer_dialog=SimpleNamespace(stop=Mock()),
            stop_camera=Mock(side_effect=RuntimeError("camera busy")),
            awareness=SimpleNamespace(revoke_observation=Mock()),
            publish_jarvis_context=Mock(),
            append_message=Mock(),
        )
        with patch("webbie_panel.read_policy", return_value=state), patch(
                "webbie_panel.update_policy") as change:
            WebbiePanel.stop_sensitive_actions(fake)
        fake.jarvis_mission_dialog.core.stop.assert_called_once()
        fake.computer_dialog.stop.assert_called_once()
        fake.awareness.revoke_observation.assert_called_once_with("screen")
        fake.publish_jarvis_context.assert_called_once()
        change.assert_not_called()
        self.assertEqual(fake.append_message.call_args.args[0], "Security")

    def test_sleep_revokes_desktop_grant_and_turns_camera_off(self):
        mock=SimpleNamespace(
            awareness=SimpleNamespace(sleep=Mock()),
            computer_dialog=SimpleNamespace(stop=Mock()),
            unified_workflow=SimpleNamespace(stop=Mock()),
            stop_camera=Mock(),
            face=SimpleNamespace(sleeping=False,update=Mock()),
            refresh_state=Mock(),
        )
        WebbiePanel.set_face_sleeping(mock,True)
        mock.computer_dialog.stop.assert_called_once()
        mock.stop_camera.assert_called_once()
        mock.unified_workflow.stop.assert_called_once()
        mock.awareness.sleep.assert_called_once_with(True)
        self.assertTrue(mock.face.sleeping)

    def test_sleep_portrait_actually_masks_open_eye_area(self):
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            portrait=SpeakingPortrait(root)
            bright=QPixmap(192,192)
            bright.fill(Qt.white)
            portrait.closed=bright
            portrait.opened=QPixmap()
            def image():
                result=QImage(192,192,QImage.Format_ARGB32)
                result.fill(Qt.transparent)
                painter=QPainter(result)
                portrait.render(painter)
                painter.end()
                return result
            portrait.sleeping=False
            awake=image()
            portrait.sleeping=True
            sleep=image()
            # Eye positions were previously only overlaid with thin lines.
            # Filled masks should change pixels across the eye regions.
            for x in (72,118):
                self.assertNotEqual(awake.pixelColor(x,83),
                                    sleep.pixelColor(x,83))
            self.assertEqual(awake.pixelColor(72,83),
                             awake.pixelColor(118,83))

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

    def test_readiness_display_is_readonly(self):
        center=WebbieCognitiveDialog(workspace_callback=lambda:"studio")
        try:
            from runtime_readiness import Observation
            with patch("webbie_cognitive_center.inspect_readiness",
                       return_value=(Observation(
                           "agent","unknown","No recent heartbeat"),)):
                center.inspect_readiness()
            self.assertIn("No recent heartbeat",center.report.toPlainText())
            self.assertIn("No hardware was activated",center.report.toPlainText())
        finally:
            center.close()

    def test_voice_lab_is_readonly_by_default(self):
        center=WebbieCognitiveDialog(workspace_callback=lambda:"studio")
        try:
            info={
                "whisper_available":True,"whisper_model_available":True,
                "arecord_available":True,"voiceprint_opted_in":False,
                "voiceprint_file_present":False,"voiceprint_verified":False,
            }
            with patch("webbie_cognitive_center.inspect_voice_lab",
                       return_value=info):
                center.inspect_voice_lab()
            self.assertIn("NOT VERIFIED",center.report.toPlainText())
            self.assertIn("No microphone audio",center.report.toPlainText())
        finally:
            center.close()

    def test_hearing_test_requires_explicit_gui_approval(self):
        center=WebbieCognitiveDialog(workspace_callback=lambda:"studio")
        try:
            from PyQt5.QtWidgets import QMessageBox
            with patch("webbie_cognitive_center.QMessageBox.question",
                       return_value=QMessageBox.No),patch(
                       "webbie_cognitive_center.HearingTestWorker.start") as start:
                center.test_hearing()
            start.assert_not_called()
            self.assertIsNone(center.hearing_worker)
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
