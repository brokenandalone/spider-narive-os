"""Wave 3 source continuity: never drop a workspace or bypass owner approval.

Only static code and a repository manifest are examined. No audio, GUI,
model weights, live socket, files in HOME, or privileged services are touched.
"""
import ast
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
NEW_MODULES = (
    "author/master_canon.py",
    "author/master_canon_widget.py",
    "studio/production_board.py",
    "studio/production_board_panel.py",
    "webbie/agent/segment_speaker_gate.py",
    "webbie/agent/speaker_provider_loader.py",
    "webbie/agent/voice_lab.py",
    "webbie/voice/hearing_test.py",
)

class WaveThreeContinuityTests(unittest.TestCase):
    def test_new_components_are_syntax_valid_and_installed_in_one_batch(self):
        batch = (ROOT / "system/release_batch.py").read_text(encoding="utf-8")
        tree = ast.parse(batch)
        const = next(n for n in tree.body if isinstance(n, ast.Assign)
                     and any(isinstance(x, ast.Name) and x.id == "APP_FILES"
                             for x in n.targets))
        entries = ast.literal_eval(const.value)
        self.assertEqual(len(entries), len(set(entries)))
        for path in NEW_MODULES:
            with self.subTest(path=path):
                module = (ROOT / path).read_text(encoding="utf-8")
                ast.parse(module, filename=path)
                self.assertIn(path, entries)
                self.assertNotIn("/home/", path)

    def test_author_master_canon_is_manual_approval_only(self):
        store = (ROOT / "author/store.py").read_text()
        app = (ROOT / "author/main.py").read_text()
        routes = (ROOT / "author/commands.py").read_text()
        for content in (store, app, routes):
            self.assertIn("master_canon", content)
        self.assertIn("MasterCanonWidget", app)
        self.assertIn("open_master_canon", routes)
        self.assertIn("master_canon", (ROOT / "author/control_socket.py").read_text())
        targeted = (ROOT / "the-web/package/install-author-webbie.sh").read_text()
        for path in NEW_MODULES[:2]:
            self.assertIn(path, targeted)
        self.assertIn("Targeted Author/Webbie installs are disabled", targeted)

    def test_studio_board_is_read_only_until_owner_handoff(self):
        app = (ROOT / "studio/main.py").read_text()
        speech = (ROOT / "webbie/agent/webbie.py").read_text()
        board = (ROOT / "studio/production_board_panel.py").read_text()
        self.assertIn("ProductionBoardPanel", app)
        self.assertIn("production_board.py", speech)
        self.assertIn("--summary", speech)
        self.assertIn("owner", board.lower())
        self.assertIn("release_panel=self.release_panel", app)

    def test_webbie_voice_diagnostics_cannot_infer_voice_identity(self):
        agent = (ROOT / "webbie/agent/webbie.py").read_text()
        whisper = (ROOT / "webbie/voice/whisper_listener.py").read_text()
        trust = (ROOT / "webbie/agent/speaker_provider_loader.py").read_text()
        lab = (ROOT / "webbie/voice/hearing_test.py").read_text()
        self.assertIn("speaker_gate_from_config", agent)
        self.assertIn("speaker_verified", agent)
        self.assertIn("verified_workspace_voice_action", agent)
        self.assertIn("verifier", whisper)
        self.assertIn("approved is not True", lab)
        self.assertIn('raw.get("enabled") is not True', trust)
        config = (ROOT / "webbie/config/default.json").read_text()
        self.assertRegex(config, r'"speaker_verification"\s*:\s*\{')
        self.assertRegex(config, r'"enabled"\s*:\s*false')

    def test_daily_release_remains_intentionally_unapproved(self):
        import json
        data = json.loads((ROOT / "system/daily_release_plan_20261011.json").read_text())
        self.assertEqual(data["max_system_installs_per_local_day"], 1)
        self.assertFalse(data["owner_approved_install"])
        self.assertFalse(data["installed_pc_reconciled"])
        self.assertFalse(data["source_ci_verified"])
        self.assertIn("daily_install_guard(backup_root)",
                      (ROOT / "system/release_batch.py").read_text())

if __name__ == "__main__":
    unittest.main()
