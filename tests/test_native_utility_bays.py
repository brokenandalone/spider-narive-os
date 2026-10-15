"""Bounded local hardware and development inspections."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "the-web/shell"))
spec = importlib.util.spec_from_file_location(
    "native_utility_bays", ROOT / "the-web/shell/native_utility_bays.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class NativeUtilityTests(unittest.TestCase):
    def test_hardware_inventory_needs_no_privileged_commands(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            network = root / "class/net"
            network.mkdir(parents=True)
            (network / "eth0").touch()
            self.assertEqual(mod.hardware_summary(root)["Network interfaces"], ["eth0"])
            self.assertEqual(mod.hardware_summary(root)["Cameras"], [])

    def test_git_status_readonly_from_selected_repo(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            with self.assertRaises(ValueError):
                mod.git_status(root / "absent")
            (root / "example.py").write_text("print('safe')")
            self.assertIn("clean", mod.git_status(root))

    def test_no_program_install_and_no_privilege_increase(self):
        text = (ROOT / "the-web/shell/native_utility_bays.py").read_text()
        for string in ("sudo ", "systemctl restart", "apt install", "do-release-upgrade",
                       "git push", "git reset --hard", "shutil.rmtree"):
            self.assertNotIn(string, text)


if __name__ == "__main__":
    unittest.main()
