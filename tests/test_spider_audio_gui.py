"""Headless GUI smoke tests for real Spider Audio Studio workspaces.

No sound card, microphone, project import, network or subprocess is involved.
"""
import os
from pathlib import Path
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_ACCESSIBILITY", "0")

try:
    from PyQt5.QtWidgets import QApplication
except ImportError:
    QApplication = None

@unittest.skipUnless(QApplication, "PyQt5 not available")
class StudioProductionGUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        from studio.instrument_workbench import InstrumentWorkbench
        from studio.song_production_panel import SongProductionPanel
        from studio.waveform_edit_panel import WaveformEditPanel
        cls.workbench_class = InstrumentWorkbench
        cls.arranger_class = SongProductionPanel
        cls.wave_class = WaveformEditPanel
        from studio.dj_deck_panel import DJDeckPanel
        cls.dj_class = DJDeckPanel

    def test_capture_edit_and_mixer_controls(self):
        workbench = self.workbench_class()
        arranger = self.arranger_class(workbench)
        try:
            self.assertEqual(workbench.tabs.count(), 5)
            self.assertIsNotNone(workbench.midi_input)
            workbench.pattern.set("guitar", 0, 64)
            arranger.capture_bar()
            self.assertEqual(len(arranger.song.bars), 1)
            self.assertEqual(arranger.song.bars[0].pattern.events["guitar"][0], 64)
            workbench.pattern.set("bass", 0, 40)
            self.assertIsNone(arranger.song.bars[0].pattern.events["bass"][0])
            arranger.bars.setCurrentRow(0)
            arranger.update_bar()
            self.assertEqual(arranger.song.bars[0].pattern.events["bass"][0], 40)
            gain, pan, mute, solo = arranger.controls["guitar"]
            gain.setValue(45)
            pan.setValue(-50)
            mute.setChecked(True)
            solo.setChecked(True)
            self.assertEqual(arranger.song.mixer["guitar"].gain, 45)
            self.assertEqual(arranger.song.mixer["guitar"].pan, -50)
            self.assertTrue(arranger.song.mixer["guitar"].mute)
            self.assertTrue(arranger.song.mixer["guitar"].solo)
            arranger.duplicate_bar()
            self.assertEqual(len(arranger.song.bars), 2)
            arranger.move_bar(-1)
            arranger.remove_bar()
            self.assertEqual(len(arranger.song.bars), 1)
        finally:
            arranger.close()
            workbench.close()

    def test_waveform_editor_is_integrated_in_studio_source(self):
        source = (Path(__file__).resolve().parents[1] / "studio/main.py").read_text()
        self.assertIn("self.tool_tabs.addTab(song_scroll, 'Song Arranger & Mixer')", source)
        self.assertIn("self.tool_tabs.addTab(waveform_scroll, 'Waveform Editor')", source)
        self.assertIn("self.tool_tabs.addTab(dj_scroll, 'DJ Decks')", source)
        self.assertIn("self.tool_tabs.setCurrentWidget(self.instrument_page)", source)
        self.assertIn("from .song_production_panel import SongProductionPanel", source)
        self.assertIn("from .waveform_edit_panel import WaveformEditPanel", source)
        w = self.wave_class()
        try:
            self.assertIsNone(w.original_clip)
            self.assertIsNone(w.clip)
            self.assertGreaterEqual(w.canvas.minimumHeight(), 220)
        finally:
            w.close()
        deck = self.dj_class()
        try:
            self.assertEqual(deck.decks, [None, None])
            self.assertEqual(deck.cross.value(), 0)
            deck.cross.setValue(100)
            self.assertEqual(deck.cross.value(), 100)
            self.assertEqual(deck.gains[0].value(), 100)
        finally:
            deck.close()

if __name__ == "__main__":
    unittest.main()
