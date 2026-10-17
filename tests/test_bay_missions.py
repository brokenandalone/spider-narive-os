"""Native Spider OS bay storage and transitions are tested without a desktop."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bay_missions", ROOT / "the-web/shell/bay_missions.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class MissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.storage = self.root / "state/missions.json"
        self.store = mod.MissionStore(self.storage)

    def test_all_fifteen_native_bays_have_real_missions(self):
        self.assertEqual(len(mod.BAYS), 15)
        self.assertEqual(set(mod.BAYS), set(mod.BLUEPRINTS))
        for bay in mod.BAYS:
            self.assertTrue(all(mod.BLUEPRINTS[bay][1]))

    def test_create_progress_cross_bay_and_delete_never_touches_folder(self):
        folder = self.root / "album"
        folder.mkdir()
        original = folder / "master.wav"
        original.write_bytes(b"original music")
        mission = self.store.add("studio", "Record guitars", str(folder))
        self.assertEqual(len(self.store.for_bay("studio")), 1)
        self.store.update(mission["id"], status="active")
        self.store.update(mission["id"], destination="media")
        self.assertEqual(self.store.for_bay("studio"), [])
        self.assertEqual(self.store.for_bay("media")[0]["status"], "active")
        self.store.remove(mission["id"])
        self.assertEqual(self.store.read(), [])
        self.assertEqual(original.read_bytes(), b"original music")

    def test_invalid_workspaces_and_paths_rejected(self):
        with self.assertRaises(ValueError):
            self.store.add("unknown", "No")
        with self.assertRaises(ValueError):
            self.store.add("studio", "")
        with self.assertRaises(ValueError):
            self.store.add("studio", "Bad folder", "/no/such/dir")
        mission = self.store.add("author", "Continuity")
        with self.assertRaises(ValueError):
            self.store.update(mission["id"], status="invalid")
        with self.assertRaises(ValueError):
            self.store.update(mission["id"], destination="unknown")

    def test_private_atomic_store_and_symlink_protection(self):
        self.store.add("study", "Check rubric")
        self.assertEqual(self.storage.stat().st_mode & 0o777, 0o600)
        symlink = self.root / "alias.json"
        symlink.symlink_to(self.storage)
        with self.assertRaises(OSError):
            mod.MissionStore(symlink).read()
        with self.assertRaises(OSError):
            mod.MissionStore(symlink).add("webbie", "Avoid overwrite")

    def test_does_not_execute_or_read_linked_documents(self):
        content = (ROOT / "the-web/shell/bay_missions.py").read_text()
        for forbidden in ("subprocess", "eval(", "exec(", "os.system", "requests.", "urlopen"):
            self.assertNotIn(forbidden, content)


if __name__ == "__main__":
    unittest.main()
