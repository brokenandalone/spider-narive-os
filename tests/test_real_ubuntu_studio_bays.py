"""Host-observed Ubuntu Studio 26.04 application IDs, not guessed packages.

These representative names came from the owner's read-only 174-entry
application-menu inventory on 2026-10-15. The full private snapshot stays
on that computer. Tests assert routing only, never delete launcher entries.
"""
import importlib.util
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "observed_app_catalog", ROOT / "the-web/shell/app_catalog.py")
catalog = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = catalog
spec.loader.exec_module(catalog)


CONFIRMED = {
    "studio": {
        "spider-studio.desktop": "Spider Studio",
        "studio.desktop": "Spider Studio",
        "aeolus.desktop": "Aeolus",
        "zita-at1.desktop": "AT1",
        "devede_ng.py.desktop": "DevedeNG",
        "dgedit.desktop": "DGEdit",
        "din.desktop": "DIN",
        "qlcplus-fixtureeditor.desktop": "Fixture Definition Editor - QLC+",
        "fluidsynth-dssi.desktop": "Fluidsynth DSSI",
        "fmit.desktop": "FMIT",
        "freewheeling.desktop": "FreeWheeling",
        "hexter.desktop": "Hexter",
        "jack_mixer.desktop": "Jack Mixer",
        "meterbridge.desktop": "Meterbridge",
        "patchance.desktop": "Patchance",
        "phasex.desktop": "PHASEX",
        "qlcplus.desktop": "Q Light Controller Plus - QLC+",
        "com.cuperino.qprompt.desktop": "QPrompt",
        "org.kde.krecorder.desktop": "Recorder",
        "setbfree.desktop": "setBfree",
        "sooperlooper.desktop": "SooperLooper",
        "xjadeo.desktop": "Xjadeo",
        "zita-mu1.desktop": "Zita-mu1",
        "zita-rev1.desktop": "Zita-Rev1",
        "org.jacktrip.JackTrip.desktop": "JackTrip",
        "ubuntustudio-audio-config.desktop": "Ubuntu Studio Audio Configuration",
    },
    "devices": {
        "envy24control.desktop": "Envy24 Control",
        "org.ffado.FfadoMixer.desktop": "FFADO Mixer",
        "hdajackretask.desktop": "HDAJackRetask",
        "hdspconf.desktop": "HDSPConf",
        "hdspmixer.desktop": "HDSPMixer",
        "mudita24.desktop": "Mudita24",
        "qasconfig.desktop": "QasConfig",
        "qashctl.desktop": "QasHCtl",
        "qasmixer.desktop": "QasMixer",
        "org.kde.qrca.desktop": "Qrca",
        "kde_wacom_tabletfinder.desktop": "Wacom Tablet finder",
    },
    "media": {
        "idjc.desktop": "Internet DJ Console",
        "org.kde.kid3.desktop": "Kid3",
        "org.kde.kid3-qt.desktop": "Kid3-qt",
        "freeshow_freeshow.desktop": "FreeShow",
        "openlp.desktop": "OpenLP",
        "spider-media-player.desktop": "Spider Media Center",
    },
    "art-lab": {
        "org.kde.spectacle.desktop": "Spectacle",
        "org.gnome.ColorProfileViewer.desktop": "Color Profile Viewer",
    },
    "author": {"author.desktop": "Author"},
    "forage": {"forage.desktop": "Forage"},
    "deep-forage": {"deep-forage.desktop": "Deep Forage"},
    "study": {"study.desktop": "School"},
    "webbie": {
        "webbie.desktop": "Webbie",
        "webbie-face-sleep-tonight.desktop": "Webbie: Sleep Quietly",
        "webbie-face-wake.desktop": "Webbie: Wake Face",
        "webbie-onedrive-connect.desktop": "Webbie: Connect OneDrive",
        "spider-webbie-intelligence.desktop": "Webbie Intelligence Center (Private)",
    },
    "kali-bay": {"kali-bay.desktop": "Kali-bay"},
    "system": {
        "spider-os-universal.desktop": "Spider OS Universal Control Center v3 (Private)",
        "spider-os-workspace-max.desktop": "Spider OS Workspace MAX Control Center v4 (Private)",
    },
    "dev-bay": {"virt-manager.desktop": "Virtual Machine Manager"},
}


class ObservedNativeAppRouting(unittest.TestCase):
    def test_every_explicit_id_is_unique(self):
        ids = [entry for rows in CONFIRMED.values() for entry in rows]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 58)

    def test_observed_nonobvious_mappings(self):
        for bay, programs in CONFIRMED.items():
            for desktop_id, name in programs.items():
                with self.subTest(app=desktop_id, destination=bay):
                    actual = catalog.workspace_for(
                        desktop_id, name, ["AudioVideo", "Graphics"])
                    self.assertEqual(actual, bay)

    def test_owner_choices_take_priority_without_uninstalling(self):
        original = catalog.workspace_for("aeolus.desktop", "Aeolus", ["AudioVideo"])
        self.assertEqual(original, "studio")
        # The store override is respected by discovery for any available app.
        self.assertEqual(
            catalog.EXACT_BAYS["webbie.desktop"], "webbie")
        self.assertNotIn("os.system", (
            ROOT / "the-web/shell/app_catalog.py").read_text())

    def test_known_app_purpose_explains_why_in_native_bay(self):
        examples = (
            ("aeolus.desktop", "Aeolus", "studio", "organ"),
            ("idjc.desktop", "Internet DJ Console", "media", "radio"),
            ("org.hydrogenmusic.Hydrogen.desktop", "Hydrogen",
             "studio", "drum"),
            ("org.kde.kid3.desktop", "Kid3", "media", "music metadata"),
            ("org.ffado.FfadoMixer.desktop", "FFADO Mixer",
             "devices", "FireWire"),
            ("webbie-face-sleep-tonight.desktop", "Webbie: Sleep Quietly",
             "webbie", "quiet mode"),
        )
        for ident, name, bay, description in examples:
            with self.subTest(app=ident):
                application = catalog.InstalledApp(
                    ident, Path("/not/accessed/" + ident), name, "",
                    "", bay)
                self.assertIn(description.casefold(),
                              catalog.app_purpose(application).casefold())

    def test_apps_with_normal_id_still_route_by_category(self):
        self.assertEqual(
            catalog.workspace_for("my-lighting-tool.desktop", "Unknown",
                                  ["Graphics"]), "art-lab")
        self.assertEqual(
            catalog.workspace_for("my-daw.desktop", "Unknown",
                                  ["AudioEditing"]), "studio")


if __name__ == "__main__":
    unittest.main()
