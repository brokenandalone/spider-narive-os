"""Test Kali's read-only desktop application discovery with no real container."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[1] / "kali-bay/runtime/kali_apps.py"
SPEC = importlib.util.spec_from_file_location("kali_apps_in_guest", SRC)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class KaliAppCatalogTests(unittest.TestCase):
    def add(self, folder, name, body):
        p = folder / name
        p.write_text("[Desktop Entry]\n" + body, encoding="utf-8")
        return p

    def test_only_visible_system_applications_are_listed(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            self.add(folder, "wireshark.desktop",
                     "Type=Application\nName=Wireshark\nExec=wireshark %f\n"
                     "Categories=Network;X-Kali-InformationGathering;\n"
                     "Comment=Inspect packet captures\n")
            self.add(folder, "hidden.desktop",
                     "Type=Application\nName=Hidden\nExec=hidden\nHidden=true\n")
            self.add(folder, "nodisplay.desktop",
                     "Type=Application\nName=NoDisplay\nExec=not-visible\nNoDisplay=true\n")
            self.add(folder, "folder.desktop",
                     "Type=Directory\nName=Folder\nExec=blah\n")
            self.add(folder, "noexec.desktop", "Type=Application\nName=NoExec\n")
            self.add(folder, "bad;id.desktop",
                     "Type=Application\nName=Bad ID\nExec=bad\n")
            self.add(folder, "missingname.desktop", "Type=Application\nExec=true\n")
            target = self.add(folder, "actual.desktop",
                              "Type=Application\nName=Target\nExec=echo\n")
            (folder / "link.desktop").symlink_to(target)
            with patch.object(module, "SYSTEM_APPS", folder):
                results = module.catalog()
            self.assertEqual([x["id"] for x in results],
                             ["actual.desktop", "wireshark.desktop"])
            self.assertEqual(results[1]["category"],
                             "X-Kali-InformationGathering")
            self.assertEqual(results[1]["name"], "Wireshark")

    def test_missing_directory_returns_empty(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(module, "SYSTEM_APPS", Path(d) / "unavailable"):
                self.assertEqual(module.catalog(), [])

    def test_multiline_labels_have_no_control_text(self):
        self.assertEqual(module.safe_label("name\nother\tpart"), "nameotherpart")
        self.assertLessEqual(len(module.safe_label("x" * 300)), 95)


if __name__ == "__main__":
    unittest.main()
