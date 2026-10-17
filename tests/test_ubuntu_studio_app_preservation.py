"""Every Ubuntu Studio program remains available; moving it changes only a category."""
import importlib.util
from pathlib import Path
from unittest.mock import patch
import tempfile
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "studio_app_catalog", ROOT / "the-web/shell/app_catalog.py")
catalog = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = catalog
spec.loader.exec_module(catalog)


class StudioAppPreservationTests(unittest.TestCase):
    def test_studio_common_recording_midi_and_video_programs(self):
        for program in ("Ardour", "Qtractor", "Audacity", "Carla",
                        "QjackCtl", "Mixxx", "Hydrogen", "MuseScore",
                        "Rosegarden", "Guitarix", "Yoshimi", "OBS Studio",
                        "Kdenlive", "Shotcut", "OpenShot", "HandBrake",
                        "qpwgraph", "EasyEffects"):
            with self.subTest(program=program):
                self.assertEqual(catalog.workspace_for(
                    program + ".desktop", program, ["AudioVideo"]), "studio")

    def test_art_media_author_development_and_system(self):
        groups = {
            "art-lab": ("Krita", "GIMP", "Inkscape", "Blender",
                        "Darktable", "digiKam", "Scribus", "RawTherapee"),
            "media": ("VLC", "Audacious", "mpv", "Strawberry", "Steam"),
            "author": ("LibreOffice Writer", "FocusWriter", "ghostwriter"),
            "productivity": ("LibreOffice Calc", "LibreOffice Impress",
                             "Okular", "KOrganizer"),
            "communications": ("Thunderbird", "FileZilla", "Konversation"),
            "forage": ("Firefox", "Chromium", "Falkon"),
            "dev-bay": ("Konsole", "Kate", "KDevelop", "VSCodium"),
            "devices": ("KDE Connect", "Bluedevil Bluetooth",
                        "KDE Partition Manager", "pavucontrol"),
            "system": ("Timeshift", "BackInTime", "System Settings"),
        }
        for bay, names in groups.items():
            for program in names:
                with self.subTest(bay=bay, program=program):
                    actual = catalog.workspace_for(
                        program + ".desktop", program, [])
                    self.assertEqual(actual, bay)
                    self.assertTrue(catalog.APP_PURPOSES[bay])

    def test_unknown_distro_apps_not_dropped_and_categories_fallback(self):
        self.assertEqual(
            catalog.workspace_for("mystery.desktop", "Mystery", []), "system")
        self.assertEqual(
            catalog.workspace_for("mystery.desktop", "Mystery", ["Graphics"]), "art-lab")
        self.assertEqual(
            catalog.workspace_for("custom-daw.desktop", "Custom DAW",
                                  ["AudioEditing"]), "studio")
        self.assertEqual(
            catalog.workspace_for("utility.desktop", "Utility", ["Office"]), "productivity")

    def test_installed_entries_remain_visible_after_reassignment_and_reset(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            xdg = root / "applications"
            xdg.mkdir()
            apps = [
                ("ardour.desktop", "Ardour", "AudioVideo;"),
                ("krita.desktop", "Krita", "Graphics;"),
                ("writer.desktop", "LibreOffice Writer", "Office;"),
                ("unknown.desktop", "Unknown Installed Tool", "Utility;"),
            ]
            for identity, name, categories in apps:
                (xdg / identity).write_text(
                    "[Desktop Entry]\nType=Application\nName=" + name +
                    "\nExec=existing-program\nCategories=" + categories + "\n",
                    encoding="utf-8")
            before = {p.name: p.read_bytes() for p in xdg.iterdir()}
            destination = root / "config/app-placement.json"
            with patch.object(catalog.shutil, "which",
                              return_value="/usr/bin/existing-program"):
                original = catalog.discover_apps([xdg], "KDE", assignments={})
                self.assertEqual(len(original), 4)
                self.assertEqual(
                    {a.workspace for a in original},
                    {"studio", "art-lab", "author", "system"})
                catalog.save_app_assignment("krita.desktop", "studio", destination)
                manual = catalog.discover_apps(
                    [xdg], "KDE",
                    assignments=catalog.read_app_assignments(destination))
                self.assertEqual(len(manual), len(original))
                self.assertEqual(
                    next(a.workspace for a in manual if a.desktop_id == "krita.desktop"),
                    "studio")
                catalog.save_app_assignment("krita.desktop", None, destination)
                reverted = catalog.discover_apps(
                    [xdg], "KDE",
                    assignments=catalog.read_app_assignments(destination))
                self.assertEqual(
                    next(a.workspace for a in reverted if a.desktop_id == "krita.desktop"),
                    "art-lab")
            self.assertEqual(before, {p.name: p.read_bytes() for p in xdg.iterdir()})
            self.assertEqual(destination.stat().st_mode & 0o777, 0o600)

    def test_hidden_apps_do_not_bypass_existing_user_desktop_prefs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            xdg = root / "xdg"
            xdg.mkdir()
            (xdg / "hidden.desktop").write_text(
                "[Desktop Entry]\nType=Application\nName=Hidden\n"
                "Exec=existing-program\nNoDisplay=true\n")
            (xdg / "disabled.desktop").write_text(
                "[Desktop Entry]\nType=Application\nName=Disabled\n"
                "Exec=existing-program\nHidden=true\n")
            (xdg / "dbus.desktop").write_text(
                "[Desktop Entry]\nType=Application\nName=DBus App\n"
                "Exec=missing-binary\nDBusActivatable=true\n")
            with patch.object(catalog.shutil, "which", return_value=None):
                available = catalog.discover_apps([xdg], "KDE", assignments={})
            self.assertEqual([a.desktop_id for a in available], ["dbus.desktop"])
            # Neither status removes or modifies a program's real .desktop file.
            self.assertEqual(len(list(xdg.glob("*.desktop"))), 3)

    def test_rejects_bad_bay_and_unsafe_overrides(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "app-placement.json"
            with self.assertRaises(ValueError):
                catalog.save_app_assignment("../../usr/bin/firefox", "studio", path)
            with self.assertRaises(ValueError):
                catalog.save_app_assignment("firefox.desktop", "nonexistent", path)
            with self.assertRaises(ValueError):
                catalog.save_app_assignment("firefox.desktop", "default", path)
            private = Path(folder) / "source"
            private.write_text("PRESERVE")
            alias = Path(folder) / "shortcut.json"
            alias.symlink_to(private)
            with self.assertRaises(OSError):
                catalog.save_app_assignment("firefox.desktop", "forage", alias)
            self.assertEqual(private.read_text(), "PRESERVE")


if __name__ == "__main__":
    unittest.main()
