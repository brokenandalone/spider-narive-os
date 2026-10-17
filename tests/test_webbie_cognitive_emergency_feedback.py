"""Offline checks of Cognitive Center STOP reporting; no camera/Qt or service access."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "the-web/shell/webbie_cognitive_center.py"


def isolated_stop():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    dialog = next(node for node in tree.body
                  if isinstance(node, ast.ClassDef) and
                  node.name == "WebbieCognitiveDialog")
    method = next(node for node in dialog.body
                  if isinstance(node, ast.FunctionDef)
                  and node.name == "stop_sensitive")
    # Run *only* the one extracted method with stand-in objects. Loading
    # Webbie, the camera, GUI, or services is intentionally forbidden.
    module = ast.fix_missing_locations(
        ast.Module(body=[method], type_ignores=[]))
    namespace = {}
    exec(compile(module, "<isolated-stop-method>", "exec"), namespace)
    return namespace["stop_sensitive"]


class FakeReport:
    def __init__(self):
        self.message = ""

    def setPlainText(self, value):
        self.message = value


class Confirmation:
    Yes = 1
    No = 2
    choice = Yes

    @classmethod
    def question(cls, *args):
        return cls.choice


class FakeDialog:
    def __init__(self, callback):
        self.emergency_callback = callback
        self.report = FakeReport()


class CognitiveEmergencyFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.fn = isolated_stop()
        self.fn.__globals__["QMessageBox"] = Confirmation
        Confirmation.choice = Confirmation.Yes

    def tearDown(self):
        Confirmation.choice = Confirmation.Yes

    def test_missing_emergency_handler_never_claims_stop(self):
        dialog = FakeDialog(None)
        self.fn(dialog)
        self.assertIn("STOP NOT VERIFIED", dialog.report.message)
        self.assertIn("may still be active", dialog.report.message)

    def test_handler_failure_never_claims_stop(self):
        def failed():
            raise RuntimeError("simulated failing handler")
        dialog = FakeDialog(failed)
        self.fn(dialog)
        self.assertIn("STOP NOT VERIFIED", dialog.report.message)
        self.assertNotIn("simulated", dialog.report.message)

    def test_successful_callback_is_only_a_request_not_confirmation(self):
        calls = []
        dialog = FakeDialog(lambda: calls.append("stop"))
        self.fn(dialog)
        self.assertEqual(calls, ["stop"])
        self.assertIn("stop requested", dialog.report.message)
        self.assertIn("cannot independently confirm", dialog.report.message)

    def test_declining_dialog_does_not_invoke_handler(self):
        Confirmation.choice = Confirmation.No
        calls = []
        dialog = FakeDialog(lambda: calls.append("stop"))
        self.fn(dialog)
        self.assertFalse(calls)
        self.assertEqual(dialog.report.message, "")


if __name__ == "__main__":
    unittest.main()
