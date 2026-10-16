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
        from studio.auto_performer_panel import AutoPerformerPanel
        cls.score_class = AutoPerformerPanel

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
        self.assertIn("self.song_production_panel,", source)
        self.assertIn("self.waveform_edit_panel, self.dj_deck_panel", source)
        self.assertIn("midi.disconnect()", source)
        self.assertIn("self.tool_tabs.addTab(auto_scroll, 'Auto Performer · Scores & TAB')", source)
        self.assertIn("self.tool_tabs.addTab(capture_scroll, 'Record Audio · Multitrack')", source)
        self.assertIn("self.tool_tabs.addTab(self.score_timeline_panel", source)
        self.assertNotIn("self.tool_tabs.addTab(auto_scroll, 'Sheet Music & TAB Autoplay')", source)
        self.assertIn("from .song_production_panel import SongProductionPanel", source)
        self.assertIn("from .waveform_edit_panel import WaveformEditPanel", source)
        w = self.wave_class()
        try:
            self.assertIsNone(w.original_clip)
            self.assertIsNone(w.clip)
            self.assertGreaterEqual(w.canvas.minimumHeight(), 220)
            from PyQt5.QtGui import QImage, QPainter
            w.canvas.set_peaks([(-.35, .45)] * 180)
            bitmap = QImage(720, 260, QImage.Format_ARGB32)
            bitmap.fill(0)
            painter = QPainter(bitmap)
            w.canvas.render(painter)
            painter.end()
            self.assertFalse(bitmap.isNull())
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
        panel = self.score_class()
        try:
            panel.interpret_tab()
            self.assertIsNotNone(panel.performance)
            self.assertEqual(panel.performance.parts[0].name, "Guitar")
            self.assertGreater(len(panel.performance.notes), 12)
            self.assertEqual(panel.part_select.count(), 1)
            self.assertEqual(panel.patch_select.currentIndex(), 24)
            panel.patch_select.setCurrentIndex(30)
            self.assertEqual(panel.performance.parts[0].program, 30)
            panel.tab_text.setPlainText("Am | F | C | G")
            panel.interpret_chords()
            self.assertEqual(len(panel.performance.parts), 4)
            self.assertEqual(panel.performance.beats, 16)
            self.assertGreater(len(panel.performance.notes), 100)
            self.assertEqual(len(panel.mix_channels), 4)
            self.assertEqual(panel.groove.currentText(), "Natural player")
            self.assertTrue(panel.studio_mix.isChecked())
            panel.part_select.setCurrentIndex(1)
            panel.part_gain.setValue(62)
            panel.part_pan.setValue(-40)
            panel.part_mute.setChecked(True)
            self.assertEqual(panel.mix_channels[1].gain, 62)
            self.assertEqual(panel.mix_channels[1].pan, -40)
            self.assertTrue(panel.mix_channels[1].mute)
            panel.part_select.setCurrentIndex(0)
            self.assertEqual(panel.part_gain.value(), 90)
            self.assertEqual(panel.part_pan.value(), 0)
            self.assertFalse(panel.part_mute.isChecked())
            panel.rate_select.setCurrentIndex(1)
            self.assertEqual(panel.rate_select.currentData(), 44100)
        finally:
            panel.close()

    def test_recording_console_never_opens_input_automatically(self):
        from unittest.mock import patch
        with patch("studio.audio_capture_panel.available_inputs",
                   side_effect=AssertionError("startup enumerated an audio input")):
            from studio.audio_capture_panel import AudioCapturePanel
            panel=AudioCapturePanel()
            try:
                self.assertEqual(panel.input.count(),0)
                self.assertEqual(panel.output_device.count(),0)
                self.assertFalse(panel.record_btn.isEnabled())
                self.assertFalse(panel.overdub_btn.isEnabled())
                self.assertFalse(panel.include_cue.isChecked())
                self.assertFalse(panel.stop_btn.isEnabled())
                self.assertEqual(panel.takes,[])
                self.assertIsNone(panel.worker)
                self.assertEqual(panel.peak.value(),0)
                self.assertIn("No microphone has been opened",panel.status.text())
                panel.record()
                panel.record_overdub()
                self.assertIsNone(panel.worker)
                panel._levels(-6.,-13.,2.5)
                self.assertGreater(panel.peak.value(),85)
                from tempfile import TemporaryDirectory
                with TemporaryDirectory() as root:
                    panel._recorded({
                        "path":root+"/take01.wav","role":"lead_vocal",
                        "duration_seconds":2.5,"sample_rate":48000,
                        "channels":1,"sample_width_bits":24}, "")
                    self.assertEqual(len(panel.takes),1)
                    self.assertEqual(panel.take_list.count(),1)
                    cue=Path(root)/"Backing.wav"
                    cue.write_bytes(b"cue list fixture; backend validation not run")
                    panel.cue_file.setText(str(cue))
                    self.assertEqual(len(panel._selected_session_tracks()),1)
                    panel.include_cue.setChecked(True)
                    chosen=panel._selected_session_tracks()
                    self.assertEqual(len(chosen),2)
                    self.assertEqual(chosen[0]["role"],"instrumental_bed")
                    self.assertFalse(panel.mix_btn.isEnabled())
                    panel._recorded(root,"")
                    self.assertTrue(panel.mix_btn.isEnabled())
                    self.assertIsNotNone(panel.last_session)
            finally:
                panel.close()

    def test_note_editor_actually_changes_auto_performer_with_undo(self):
        from studio.score_timeline_panel import ScoreTimelinePanel
        from studio.auto_performer_panel import AutoPerformerPanel
        from fractions import Fraction
        performer=AutoPerformerPanel()
        editor=ScoreTimelinePanel(performer.apply_edited_score)
        performer.attach_editor(editor, lambda:None)
        try:
            performer.interpret_tab()
            original=performer.performance.notes[0]
            self.assertIsNotNone(editor.editor)
            self.assertGreater(len(editor.piano.notes), 0)
            from PyQt5.QtGui import QImage, QPainter
            editor.piano.resize(760,220)
            canvas=QImage(760,220,QImage.Format_ARGB32)
            canvas.fill(0)
            painter=QPainter(canvas)
            editor.piano.render(painter)
            painter.end()
            self.assertFalse(canvas.isNull())
            self.assertEqual(len(editor.piano._hit),len(editor.piano.notes))
            self.assertEqual(editor.editor.score.notes[0].pitch,original.pitch)
            editor.table.selectRow(0)
            editor.pitch.setValue(original.pitch+1)
            editor.apply_note()
            self.assertTrue(any(n.pitch==original.pitch+1 and n.start==original.start
                                for n in performer.performance.notes))
            self.assertTrue(editor.editor.can_undo)
            editor.undo()
            self.assertEqual(performer.performance.notes[0].pitch,original.pitch)
            editor.part.setCurrentIndex(1)
            editor.transpose_amount.setValue(2)
            editor.transpose_part()
            self.assertTrue(editor.editor.can_undo)
            self.assertTrue(any(n.pitch==original.pitch+2
                                for n in performer.performance.notes))
            performer.patch_select.setCurrentIndex(30)
            self.assertEqual(performer.performance.parts[0].program,30)
            editor.undo()
            self.assertEqual(performer.performance.parts[0].program,24)
            self.assertEqual(performer.patch_select.currentIndex(),24)
        finally:
            editor.close()
            performer.close()

if __name__ == "__main__":
    unittest.main()
