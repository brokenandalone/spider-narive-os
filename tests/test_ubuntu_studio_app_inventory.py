"""Before/after inventory must distinguish program availability from category."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "spider_app_inventory", ROOT / "tools/ubuntu_studio_app_inventory.py")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class InventoryTests(unittest.TestCase):
    def test_differing_bay_is_not_an_uninstall(self):
        old = {"format": "spider-os-xdg-v1", "entries": [
            {"id": "ardour.desktop", "bay": "studio", "source_sha256": "A"},
            {"id": "writer.desktop", "bay": "productivity", "source_sha256": "B"},
            {"id": "obsolete.desktop", "bay": "system", "source_sha256": "C"},
        ]}
        new = {"format": "spider-os-xdg-v1", "entries": [
            {"id": "ardour.desktop", "bay": "studio", "source_sha256": "A"},
            {"id": "writer.desktop", "bay": "author", "source_sha256": "B"},
            {"id": "vlc.desktop", "bay": "media", "source_sha256": "D"},
        ]}
        result = module.compare(old, new)
        self.assertEqual(result["missing_menu_entries"], ["obsolete.desktop"])
        self.assertEqual(result["added_menu_entries"], ["vlc.desktop"])
        self.assertEqual(result["reclassified_without_removal"], ["writer.desktop"])
        self.assertEqual(result["changed_desktop_metadata"], [])
        self.assertEqual(result["before"], 3)
        self.assertEqual(result["after"], 3)

    def test_critical_system_files_are_never_modified(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            source = base / "ardour.desktop"
            source.write_text("[Desktop Entry]\nName=Ardour\n")
            app = type("App", (), dict(
                desktop_id="ardour.desktop", name="Ardour",
                workspace="studio", path=source))()
            record = module.manifest([app])
            before = source.read_bytes()
            saved = base / "private/inventory.json"
            module.save_manifest(saved, record)
            self.assertEqual(saved.stat().st_mode & 0o777, 0o600)
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(json.loads(saved.read_text()), record)
            alias = base / "alias.json"
            alias.symlink_to(source)
            with self.assertRaises(OSError):
                module.save_manifest(alias, record)

    def test_rejects_unknown_prior_inventory(self):
        with self.assertRaises(ValueError):
            module.compare({"format": "unrelated", "entries": []}, {
                "format": "spider-os-xdg-v1", "entries": []})


if __name__ == "__main__":
    unittest.main()
