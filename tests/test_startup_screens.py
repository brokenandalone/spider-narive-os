"""Regressions for the staged Spider OS startup-screen collection."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGER = ROOT / "distro/config/branding/install-startup-screens.sh"
EXPECTED = {
    "spider-purple",
    "spider-crimson",
    "spider-nightfall",
}


class StartupScreensTests(unittest.TestCase):
    def test_shell_syntax(self):
        subprocess.run(["bash", "-n", str(STAGER)], check=True)

    def test_all_designed_sets_stage_without_host_changes(self):
        for selected in sorted(EXPECTED):
            with self.subTest(selected=selected):
                with tempfile.TemporaryDirectory(prefix="spider-startup-") as temp:
                    target = Path(temp)
                    subprocess.run(
                        ["bash", str(STAGER), str(target), str(ROOT), selected],
                        check=True, capture_output=True, text=True,
                    )
                    base = target / "usr/share/spider-os"
                    self.assertEqual(
                        (base / "branding/selected-startup-set").read_text().strip(),
                        selected,
                    )
                    self.assertGreater(
                        (base / "branding/startup-background.png").stat().st_size, 1000
                    )
                    self.assertGreater(
                        (base / "branding/spider-os-splash.png").stat().st_size, 1000
                    )
                    self.assertGreater(
                        (target / "usr/share/plymouth/themes/spider-os/spider-os-background.png").stat().st_size, 1000
                    )
                    for name in EXPECTED:
                        self.assertGreater(
                            (base / "startup-sets" / (name + ".png")).stat().st_size, 1000
                        )
                    theme = target / "usr/share/plasma/look-and-feel/org.spider.os"
                    meta = json.loads((theme / "metadata.json").read_text())
                    self.assertEqual(meta["KPackageStructure"], "Plasma/LookAndFeel")
                    self.assertTrue((theme / "contents/splash/Splash.qml").is_file())
                    self.assertEqual(
                        (theme / "contents/splash/images/background.png").read_bytes(),
                        (base / "startup-sets" / (selected + ".png")).read_bytes(),
                    )
                    self.assertIn(
                        "Theme=org.spider.os", (target / "etc/xdg/ksplashrc").read_text()
                    )
                    self.assertIn(
                        "startup-background.png",
                        (target / "usr/share/sddm/themes/breeze/theme.conf.user").read_text(),
                    )
                    self.assertFalse((target / "etc/crypttab").exists())
                    self.assertFalse((target / "etc/default/grub").exists())

    def test_unknown_set_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run(
                ["bash", str(STAGER), temp, str(ROOT), "not-a-real-set"],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Unknown Spider startup set", result.stderr)


if __name__ == "__main__":
    unittest.main()
