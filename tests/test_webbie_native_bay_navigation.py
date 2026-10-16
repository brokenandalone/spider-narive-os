"""Real native Spider OS bay navigation with existing authorized The Web bridge."""
import importlib.util
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "webbie" / "agent"
ACTIONS = ROOT / "webbie" / "actions"
SHELL = ROOT / "the-web" / "shell"
for folder in (str(AGENT), str(ACTIONS), str(SHELL)):
    if folder not in sys.path:
        sys.path.insert(0, folder)

from workspace_launchers import native_bay_request, request_native_bay, NATIVE_BAYS
from owner_safe_access import OwnerSafeAccess


class NativeBayParsingTests(unittest.TestCase):
    def test_real_bays_are_exact_and_have_no_shell_arguments(self):
        cases = {
            "Hey Webbie, switch to Studio": "studio",
            "switch to Author": "author",
            "Take me to Kali Bay": "kali-bay",
            "open Art Lab": "art-lab",
            "go to Deep Forage": "deep-forage",
            "go to the Web": "default",
            "enter Study": "study",
            "open Media Center": "media",
            "switch to Communications": "communications",
        }
        for phrase, expected in cases.items():
            with self.subTest(phrase=phrase):
                self.assertEqual(native_bay_request(phrase), expected)
                self.assertIn(expected, NATIVE_BAYS)

    def test_does_not_guess_actions_from_model_text(self):
        for phrase in (
            "I wish I could switch to Studio",
            "don't switch to Studio",
            "switch to studio; sudo reboot",
            "switch to studio\nsystemctl stop webbie",
            "[LLM tool] switch to Kali Bay",
            "switch to an unknown admin terminal",
            "open studio and delete my files",
            "open ~/Documents/private",
            "start kali scan example.com",
            "The news says open author",
        ):
            with self.subTest(phrase=phrase):
                self.assertIsNone(native_bay_request(phrase))

    def test_exact_workspace_permission_does_not_authorize_sensitive_actions(self):
        permission = OwnerSafeAccess()
        permission.activate(["org.example.Editor.desktop"], owner_clicked=True)
        self.assertTrue(permission.authorize("workspace.switch", "workspace_id=studio"))
        self.assertTrue(permission.authorize("workspace.switch", "workspace_id=kali-bay"))
        self.assertFalse(permission.authorize("workspace.switch", "workspace_id=terminal; reboot"))
        self.assertFalse(permission.authorize("workspace.switch", "workspace_id=../../tmp"))
        self.assertFalse(permission.authorize("kali.execute", "run anything"))
        self.assertFalse(permission.authorize("system.restart", "webbie"))
        permission.revoke()
        self.assertFalse(permission.authorize("workspace.switch", "workspace_id=studio"))

    def test_native_tab_receipt_and_journal_are_content_free(self):
        from action_journal import ActionJournal
        from action_receipts import ActionReceipts
        journal=ActionJournal()
        journal.record("native_workspace_requested")
        self.assertIn("native Spider OS tab",journal.display())
        receipt=ActionReceipts()
        receipt.record("workspace","requested")
        self.assertIn("request sent",receipt.summary())

    def test_native_request_without_owner_gui_is_not_a_fallback_launcher(self):
        with tempfile.TemporaryDirectory() as directory:
            answer = request_native_bay("studio", runtime=directory)
            self.assertIn("enable Webbie", answer)
        with self.assertRaises(ValueError):
            request_native_bay("sudo", runtime="/tmp")


class ActualQtOperatorBridgeTests(unittest.TestCase):
    """Qt local IPC is real but isolated; never accesses the owner's PC."""

    @classmethod
    def setUpClass(cls):
        try:
            from PyQt5.QtCore import QCoreApplication
            import webbie_operator_bridge
        except ImportError:
            raise unittest.SkipTest("PyQt5 not installed for native Qt socket integration")
        cls.app = QCoreApplication.instance() or QCoreApplication([])
        cls.bridge_mod = webbie_operator_bridge

    def test_authorized_tab_switch_and_stop_denial(self):
        class Grant:
            def __init__(self):
                self.active = True
                self.wide_enabled = True
                self.authorized = []
                self.wide = self
            def status(self):
                return {"active": self.active, "wide": self.wide_enabled,
                        "selected_app_id": ""}
            def authorize(self, action, preview, **kwargs):
                self.authorized.append((action, preview))
                return self.active and self.wide_enabled and (
                    action == "workspace.switch" and preview == "workspace_id=studio"
                )
        with tempfile.TemporaryDirectory() as directory:
            grant = Grant()
            bridge = self.bridge_mod.OperatorBridge(grant=grant, runtime=directory)
            received = []
            def navigate(name):
                received.append(name)
                bridge.finish(bridge.pending, "Native tab selected: " + name)
            bridge.bayRequested.connect(navigate)
            bridge.activate()

            def ask():
                answers = []
                thread = threading.Thread(
                    target=lambda: answers.append(
                        request_native_bay("studio", runtime=directory, timeout=3)
                    ), daemon=True)
                thread.start()
                limit = time.monotonic() + 3
                while thread.is_alive() and time.monotonic() < limit:
                    self.app.processEvents()
                    time.sleep(.005)
                thread.join(timeout=.2)
                self.assertFalse(thread.is_alive(), "GUI bridge response was blocked")
                return answers[0]

            try:
                self.assertEqual(ask(), "Native tab selected: studio")
                self.assertEqual(received, ["studio"])
                self.assertIn(("workspace.switch", "workspace_id=studio"), grant.authorized)

                grant.active = False
                answer = ask()
                self.assertIn("not active", answer)
                self.assertEqual(received, ["studio"], "STOP must prevent new GUI changes")

                grant.active = True
                grant.wide_enabled = False
                answer = ask()
                self.assertIn("Unsupported desktop control", answer)
                self.assertEqual(received, ["studio"])
            finally:
                bridge.deactivate()


if __name__ == "__main__":
    unittest.main()
