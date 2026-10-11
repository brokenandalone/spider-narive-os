"""Offscreen regression tests for the dedicated Band Mixer user interface."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import wave

from PyQt5.QtWidgets import QApplication
from studio.band_mixer_panel import BandMixerPanel

app = QApplication.instance() or QApplication([])


def make_wav(path):
    with wave.open(str(path), 'wb') as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(22050)
        stream.writeframes(b'\x00\x00' * 200)


class BandMixerPanelTests(unittest.TestCase):
    def test_has_separate_guitar_controls_and_does_not_render_without_sources(self):
        panel = BandMixerPanel()
        self.assertIsNot(panel.track_fields['rhythm_guitar'], panel.track_fields['lead_guitar'])
        self.assertEqual(panel.pans['rhythm_guitar'].value(), -.35)
        self.assertEqual(panel.pans['lead_guitar'].value(), .35)
        self.assertFalse(panel.import_button.isEnabled())
        with patch('studio.band_mixer_panel.BandMixerWorker') as worker:
            panel.start_mix()
            worker.assert_not_called()
        self.assertIn('two to eight', panel.status.text())
        panel.close()

    def test_import_studio_ai_and_pass_independent_levels_balance_mute(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            rhythm, lead = root / 'rhythm.wav', root / 'lead.wav'
            make_wav(rhythm)
            make_wav(lead)
            from PyQt5.QtWidgets import QLineEdit, QDoubleSpinBox
            rh_input = QLineEdit(str(rhythm))
            ld_input = QLineEdit(str(lead))
            rh_gain = QDoubleSpinBox()
            ld_gain = QDoubleSpinBox()
            rh_gain.setValue(1)
            ld_gain.setValue(.7)
            source_ai = Mock()
            source_ai.band_track_fields = {'rhythm_guitar': rh_input, 'lead_guitar': ld_input}
            source_ai.band_track_gains = {'rhythm_guitar': rh_gain, 'lead_guitar': ld_gain}
            panel = BandMixerPanel(ai_panel=source_ai)
            panel.import_ai_selections()
            self.assertEqual(panel.track_fields['lead_guitar'].text(), str(lead))
            self.assertEqual(panel.gains['lead_guitar'].value(), .7)
            panel.pans['lead_guitar'].setValue(.6)
            panel.mutes['rhythm_guitar'].setChecked(True)
            with patch('studio.band_mixer_panel.BandMixerWorker') as worker:
                panel.start_mix()
                worker.assert_called_once()
                args = worker.call_args.args
                self.assertEqual(set(args[0]), {'rhythm_guitar', 'lead_guitar'})
                self.assertEqual(args[1]['lead_guitar'], .7)
                self.assertEqual(args[2]['lead_guitar'], .6)
                self.assertTrue(args[3]['rhythm_guitar'])
                self.assertFalse(panel.mix_button.isEnabled())
                self.assertTrue(panel.cancel_button.isEnabled())
                worker.return_value.start.assert_called_once()
                panel.cancel_mix()
                worker.return_value.stop.set.assert_called_once()
                panel.mix_done(str(root / 'render.wav'), 'Saved')
                self.assertTrue(panel.play_button.isEnabled())
                panel.mix_finished()
                self.assertTrue(panel.mix_button.isEnabled())
            panel.close()

    def test_all_muted_does_not_start_worker(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for role in ('rhythm_guitar', 'lead_guitar'):
                path = root / (role + '.wav')
                make_wav(path)
            panel = BandMixerPanel()
            for role in ('rhythm_guitar', 'lead_guitar'):
                panel.track_fields[role].setText(str(root / (role + '.wav')))
                panel.mutes[role].setChecked(True)
            with patch('studio.band_mixer_panel.BandMixerWorker') as worker:
                panel.start_mix()
                worker.assert_not_called()
            self.assertIn('Unmute', panel.status.text())
            panel.close()


if __name__ == '__main__':
    unittest.main()
