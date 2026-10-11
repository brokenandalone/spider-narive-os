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


    def test_solo_only_renders_selected_role_without_changing_user_mutes(self):
        panel = BandMixerPanel()
        for role in ('lead_vocal', 'rhythm_guitar', 'lead_guitar'):
            panel.track_fields[role].setText('/tmp/' + role + '.wav')
        panel.solos['lead_guitar'].setChecked(True)
        panel.mutes['lead_guitar'].setChecked(True)
        _, _, effective_mutes, _ = panel.render_options(panel.current_tracks())
        self.assertEqual(effective_mutes, {
            'lead_vocal': True, 'rhythm_guitar': True, 'lead_guitar': False,
        })
        self.assertTrue(panel.mutes['lead_guitar'].isChecked())
        panel.close()

    def test_ui_passes_alignment_offsets_to_worker(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            panel = BandMixerPanel()
            for role in ('rhythm_guitar', 'lead_guitar'):
                wav_file = root / (role + '.wav')
                make_wav(wav_file)
                panel.track_fields[role].setText(str(wav_file))
            panel.offsets['lead_guitar'].setValue(320)
            with patch('studio.band_mixer_panel.BandMixerWorker') as worker:
                panel.start_mix()
                self.assertEqual(worker.call_args.args[4]['lead_guitar'], 320)
                panel.cancel_mix()
                panel.mix_finished()
            panel.close()

    def test_save_project_is_explicit_and_includes_all_ui_settings(self):
        panel = BandMixerPanel()
        panel.project_title.setText('New Song Chapter')
        panel.track_fields['lead_vocal'].setText('/tmp/private-owner.wav')
        panel.gains['lead_vocal'].setValue(.8)
        panel.pans['lead_vocal'].setValue(-.1)
        panel.solos['lead_vocal'].setChecked(True)
        panel.offsets['lead_vocal'].setValue(260)
        with patch('studio.band_mixer_panel.save_project', return_value=Path('/tmp/private/project-xyz/project.json')) as saver:
            panel.save_current_project()
            self.assertEqual(saver.call_args.args[0], 'New Song Chapter')
            track = saver.call_args.args[1]['lead_vocal']
            self.assertEqual(track['gain'], .8)
            self.assertEqual(track['pan'], -.1)
            self.assertEqual(track['offset_ms'], 260)
            self.assertTrue(track['solo'])
        panel.close()

    def test_load_project_replaces_previous_role_settings_and_displays_missing_stems(self):
        panel = BandMixerPanel()
        panel.project_library.addItem('Saved version', '/tmp/project-xyz/project.json')
        panel.project_library.setCurrentIndex(panel.project_library.count() - 1)
        state = {
            'title': 'Broken City: Take 4',
            'tracks': {'lead_guitar': {'path': '/tmp/lead.wav', 'gain': .5,
                      'pan': .4, 'muted': True, 'solo': False, 'offset_ms': 170}},
            'missing_sources': ['lead_guitar'],
        }
        with patch('studio.band_mixer_panel.load_project', return_value=state):
            panel.load_selected_project()
        self.assertEqual(panel.project_title.text(), 'Broken City: Take 4')
        self.assertEqual(panel.track_fields['lead_guitar'].text(), '/tmp/lead.wav')
        self.assertEqual(panel.gains['lead_guitar'].value(), .5)
        self.assertEqual(panel.offsets['lead_guitar'].value(), 170)
        self.assertTrue(panel.mutes['lead_guitar'].isChecked())
        self.assertEqual(panel.track_fields['rhythm_guitar'].text(), '')
        self.assertIn('Missing WAV stems', panel.status.text())
        panel.close()

    def test_history_and_daw_handoff_are_explicit_non_generating_actions(self):
        panel = BandMixerPanel()
        panel.track_fields['rhythm_guitar'].setText('/tmp/rhythm.wav')
        panel.track_fields['guest_vocal'].setText('/tmp/guest.wav')
        with patch('studio.band_mixer_panel.MultitrackDialog') as dialog:
            panel.open_daw_session()
            entries = dialog.call_args.args[0]
            self.assertEqual([r['role'] for r in entries], ['backing_vocal', 'rhythm_guitar'])
            dialog.return_value.exec_.assert_called_once()
        with patch('studio.band_mixer_panel.recent_mixes', return_value=[
            {'file': '/tmp/previous.wav', 'created_at_unix': 123456,
             'track_count': 2}]):
            panel.refresh_history()
        self.assertEqual(panel.mix_history.count(), 1)
        self.assertEqual(panel.mix_history.currentData(), '/tmp/previous.wav')
        panel.close()


if __name__ == '__main__':
    unittest.main()
