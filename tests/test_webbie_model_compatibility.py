"""Offline tests for Webbie model compatibility safety gate."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/webbie_model_compatibility.py"
spec = importlib.util.spec_from_file_location("webbie_model_compatibility_tested", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

BRAIN = """
from pathlib import Path
import json
CONFIG_FILE = Path("webbie/config/default.json")
DEFAULT_MODEL = "qwen3:1.7b"
def preferred_model(path=CONFIG_FILE):
    config = json.loads(Path(path).read_text())
    name = config.get("ollama", {}).get("model")
    if isinstance(name, str):
        return name
    return DEFAULT_MODEL
"""


class ModelCompatTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.installed = self.root / "installed"
        self.candidate = self.root / "candidate"
        for root in (self.installed, self.candidate):
            brain = root / "webbie/brain/brain.py"
            brain.parent.mkdir(parents=True)
            brain.write_text(BRAIN)
        config = self.installed / "webbie/config/default.json"
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({"ollama": {
            "model": "qwen3:4b", "url": "http://127.0.0.1:11434/api/chat"
        }, "other_private_owner_value": "never-report"}))
        pkg = self.candidate / "system/release_batch.py"
        pkg.parent.mkdir()
        pkg.write_text("APP_FILES = ('webbie/brain/brain.py',)\n")
        self.config = config
        self.pkg = pkg

    def inspect(self, *, models=("qwen3:4b", "qwen3:1.7b"), smoke=None, run_smoke=False):
        return module.review(installed_root=self.installed,
                             candidate_root=self.candidate, tags=list(models),
                             smoke=smoke, run_smoke=run_smoke, environment={})

    def test_newer_owner_model_remains_authoritative(self):
        result = self.inspect()
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["installed_chat_model"], "qwen3:4b")
        self.assertEqual(result["candidate_default_fallback"], "qwen3:1.7b")
        self.assertEqual(result["chat_smoke"], "not_requested")
        self.assertTrue(result["installed_model_present"])
        self.assertNotIn("never-report", json.dumps(result))
        self.assertTrue(any("fallback differs" in x for x in result["notes"]))

    def test_missing_or_invalid_model_blocks(self):
        self.assertEqual(self.inspect(models=("qwen3:1.7b",))["status"], "BLOCKED")
        self.config.unlink()
        self.assertEqual(self.inspect()["status"], "BLOCKED")

    def test_candidate_must_preserve_owner_config(self):
        self.pkg.write_text("APP_FILES = ('webbie/config/default.json',)\n")
        self.assertEqual(self.inspect()["status"], "BLOCKED")

    def test_silent_model_selector_regression_blocks(self):
        (self.candidate / "webbie/brain/brain.py").write_text(
            "DEFAULT_MODEL = 'qwen3:1.7b'\ndef preferred_model():\n    return DEFAULT_MODEL\n")
        self.assertEqual(self.inspect()["status"], "BLOCKED")

    def test_opt_in_smoke_uses_exact_selected_model(self):
        calls = []
        def test(name):
            calls.append(name)
            return True
        result = self.inspect(run_smoke=True, smoke=test)
        self.assertEqual(calls, ["qwen3:4b"])
        self.assertEqual(result["chat_smoke"], "passed")
        self.assertEqual(result["status"], "MODEL_SMOKE_PASSED_REVIEW_STILL_REQUIRED")
        failed = self.inspect(run_smoke=True, smoke=lambda name: False)
        self.assertEqual(failed["status"], "BLOCKED")

    def test_override_mismatch_blocks_without_exposing_configuration(self):
        result = module.review(installed_root=self.installed, candidate_root=self.candidate,
                               tags=["qwen3:4b"], environment={"WEBBIE_BRAIN_MODEL": "qwen3:1.7b"})
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("override differs" in s for s in result["blockers"]))

    def test_unsafe_config_symlink_blocks(self):
        self.config.unlink()
        self.config.symlink_to(self.root / "not-read")
        self.assertEqual(self.inspect()["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
