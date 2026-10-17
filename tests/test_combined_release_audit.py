"""Source gate tests use disposable fixtures and never touch Spider OS devices."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "spider_combined_release_gate", HERE / "tools/combined_release_audit.py"
)
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


class CombinedReleaseGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.root = base / "checkout"
        self.installed = base / "pc"
        self.root.mkdir()
        self.installed.mkdir()
        needed = sorted({p for paths in gate.COMPONENTS.values() for p in paths})
        for relative in needed:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            markers = gate.WIRING.get(relative, ())
            # Syntax-valid Python stubs or placeholder shell scripts.
            target.write_text(
                "# fixture\n" + "".join("# " + marker + "\n" for marker in markers),
                encoding="utf-8"
            )
        release = self.root / "system/release_batch.py"
        release.parent.mkdir(parents=True, exist_ok=True)
        release.write_text("APP_FILES = " + repr(tuple(needed)) + "\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_complete_disposable_candidate_passes_source_gate(self):
        blocks, notes = gate.audit(self.root, self.installed)
        self.assertEqual(blocks, [])
        self.assertTrue(any("Study" in x for x in notes))

    def test_missing_school_module_blocks_release(self):
        (self.root / "study/homework_ui.py").unlink()
        blockers, _ = gate.audit(self.root, self.installed)
        self.assertIn("MISSING SOURCE: study/homework_ui.py", blockers)

    def test_installer_omission_blocks_release(self):
        (self.root / "system/release_batch.py").write_text(
            "APP_FILES = ('author/main.py',)\n", encoding="utf-8"
        )
        blockers, _ = gate.audit(self.root, self.installed)
        self.assertIn("NOT IN BATCH INSTALLER: study/study.py", blockers)

    def test_missing_voice_route_blocks_release(self):
        (self.root / "webbie/agent/webbie.py").write_text(
            "# ask_vision but no other routes\n", encoding="utf-8"
        )
        blockers, _ = gate.audit(self.root, self.installed)
        self.assertTrue(any("author_voice_bridge" in x for x in blockers))

    def test_installed_customizations_are_observed_not_modified(self):
        installed = self.installed / "webbie/agent/webbie.py"
        installed.parent.mkdir(parents=True, exist_ok=True)
        installed.write_text("print('custom PC feature')\n", encoding="utf-8")
        before = installed.read_bytes()
        blockers, notes = gate.audit(self.root, self.installed)
        self.assertEqual(blockers, [])
        self.assertIn(
            "PC DIFFERS (PRESERVE AND RECONCILE): webbie/agent/webbie.py",
            notes,
        )
        self.assertEqual(installed.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
