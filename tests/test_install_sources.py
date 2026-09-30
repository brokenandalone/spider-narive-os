import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "install_sources", Path(__file__).resolve().parents[1] / "distro/update-install-sources.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class InstallSourceTests(unittest.TestCase):
    def test_preserves_ids_paths_and_unrelated_sources(self):
        catalog = {"version": 2, "kernel": {"default": "linux-generic"}, "sources": [
            {"id": "studio", "path": "standard.squashfs", "size": 10, "default": True,
             "variations": {"default": {"path": "standard.squashfs", "size": 10}}},
            {"id": "minimal", "path": "minimal.squashfs", "size": 5},
        ]}
        expected = copy.deepcopy(catalog)
        self.assertEqual(module.update_catalog(catalog, 100), 1)
        expected["sources"][0]["size"] = 100
        expected["sources"][0]["variations"]["default"]["size"] = 100
        self.assertEqual(catalog, expected)

    def test_legacy_list_catalog(self):
        catalog = [{"id": "studio", "path": "standard.squashfs", "size": 10}]
        self.assertEqual(module.update_catalog(catalog, 100), 1)
        self.assertEqual(catalog[0]["size"], 100)

    def test_unknown_install_source_fails_closed(self):
        with self.assertRaises(ValueError):
            module.update_catalog([{"path": "other.squashfs", "size": 10}], 100)


if __name__ == "__main__":
    unittest.main()
