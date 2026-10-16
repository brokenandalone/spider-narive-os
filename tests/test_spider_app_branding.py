"""Source-stage checks for Spider app identities and real Studio integration."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "branding" / "spider-apps"

class SpiderAppBrandingTests(unittest.TestCase):
    def test_sixteen_distinct_svg_icon_and_background_sets(self):
        icons = sorted((ART / "icons").glob("spider-*.svg"))
        backgrounds = sorted((ART / "backgrounds").glob("spider-*.svg"))
        self.assertEqual(len(icons), 16)
        self.assertEqual([x.name for x in icons], [x.name for x in backgrounds])
        for path in [*icons, *backgrounds]:
            svg = ET.parse(path).getroot()
            self.assertEqual(svg.tag, "{http://www.w3.org/2000/svg}svg")
            self.assertTrue(svg.attrib.get("aria-label"))
            self.assertGreater(len(path.read_bytes()), 250)

    def test_real_studio_embeds_original_instrument_workbench(self):
        main = (ROOT / "studio/main.py").read_text()
        self.assertIn("from .instrument_workbench import InstrumentWorkbench", main)
        self.assertIn("InstrumentWorkbench(self)", main)
        self.assertIn("self.tool_tabs.addTab(instrument_scroll, 'Play Instruments')", main)
        self.assertIn("self.tool_tabs.addTab(ai_scroll, 'Studio AI')", main)
        self.assertIn("self.tool_tabs.addTab(band_scroll, 'Band Mixer')", main)
        for path in ("studio/instruments_engine.py", "studio/instrument_workbench.py",
                     "studio/main.py", "the-web/shell/main.py",
                     "the-web/shell/immersive_bays.py", "the-web/shell/app_visuals.py"):
            source = (ROOT / path).read_text()
            compile(source, path, "exec")

    def test_launch_icon_opens_real_studio_not_just_branding(self):
        desktop = (ROOT / "distro/config/applications/studio.desktop").read_text()
        self.assertIn("Icon=/usr/local/lib/spider-os/branding/spider-apps/icons/spider-audio-studio.svg", desktop)
        self.assertIn("Exec=/usr/local/lib/spider-os/studio/bin/studio", desktop)
        menu = (ROOT / "the-web/shell/main.py").read_text()
        self.assertIn("from app_visuals import app_art", menu)
        self.assertIn("self.shell.open_workspace(ident)", menu)

if __name__ == "__main__":
    unittest.main()
