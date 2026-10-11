"""Offscreen Qt regression coverage for Spider Studio Release Desk."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import wave

from PyQt5.QtWidgets import QApplication
from studio.release_panel import ReleasePanel

app = QApplication.instance() or QApplication([])


def wav(path):
    with wave.open(str(path), 'wb') as stream:
        stream.setnchannels(2)
        stream.setsampwidth(2)
        stream.setframerate(48000)
        stream.writeframes(bytes(400))


class ReleaseDeskTests(unittest.TestCase):
    def test_defaults_are_private_studio_quality_and_never_auto_render(self):
        with patch('studio.release_panel.list_releases', return_value=[]), \
             patch('studio.release_panel.recent_mixes', return_value=[]):
            panel = ReleasePanel()
        self.assertFalse(panel.use_last_mix.isEnabled())
        self.assertEqual(panel.selected_profiles(), ('studio_wav',))
        self.assertFalse(panel.folder_button.isEnabled())
        with patch('studio.release_panel.ReleaseWorker') as worker:
            panel.start_export()
            worker.assert_not_called()
        self.assertIn('WAV', panel.status.text())
        panel.close()

    def test_last_mix_import_is_explicit_and_worker_gets_selected_profiles(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            finished = root / 'finished.wav'
            wav(finished)
            mixer = Mock()
            mixer.last_mix = finished
            with patch('studio.release_panel.list_releases', return_value=[]), \
                 patch('studio.release_panel.recent_mixes', return_value=[]):
                panel = ReleasePanel(band_mixer=mixer)
            self.assertEqual(panel.source.text(), '')
            panel.import_last_mix()
            self.assertEqual(panel.source.text(), str(finished))
            panel.profile_boxes['mp3_320'].setChecked(True)
            panel.profile_boxes['studio_wav'].setChecked(False)
            with patch('studio.release_panel.ReleaseWorker') as worker:
                panel.start_export()
                self.assertEqual(worker.call_args.args[0], finished)
                self.assertEqual(worker.call_args.args[1], ('mp3_320',))
                worker.return_value.start.assert_called_once()
                self.assertFalse(panel.start_button.isEnabled())
                self.assertTrue(panel.stop_button.isEnabled())
                panel.stop_export()
                worker.return_value.stop.set.assert_called_once()
                panel.export_done(str(root / 'release'), 'Saved')
                self.assertTrue(panel.folder_button.isEnabled())
                panel.export_finished()
                self.assertTrue(panel.start_button.isEnabled())
            panel.close()

    def test_no_formats_does_not_start_worker(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / 'mix.wav'
            wav(path)
            panel = ReleasePanel()
            panel.source.setText(str(path))
            for box in panel.profile_boxes.values():
                box.setChecked(False)
            with patch('studio.release_panel.ReleaseWorker') as worker:
                panel.start_export()
                worker.assert_not_called()
            self.assertIn('Select at least one', panel.status.text())
            panel.close()

    def test_mix_comparison_uses_manual_open_not_automatic_playback(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wav1 = root / 'a.wav'
            wav2 = root / 'b.wav'
            wav(wav1)
            wav(wav2)
            recent = [
                {'file': str(wav1), 'created_at_unix': 123, 'track_count': 3},
                {'file': str(wav2), 'created_at_unix': 124, 'track_count': 4},
            ]
            with patch('studio.release_panel.recent_mixes', return_value=recent):
                panel = ReleasePanel()
            self.assertEqual(panel.compare_a.currentData(), str(wav1))
            self.assertEqual(panel.compare_b.currentData(), str(wav2))
            with patch('studio.release_panel.QDesktopServices.openUrl', return_value=True) as opener:
                panel.audition(panel.compare_a.currentData())
                panel.audition(panel.compare_b.currentData())
                self.assertEqual(opener.call_count, 2)
            panel.close()

    def test_release_history_requires_existing_verified_bundle(self):
        completed = [{
            'folder': '/tmp/spider-release-123',
            'created_at_unix': 12345, 'exports': [{'profile': 'studio_wav'}],
        }]
        with patch('studio.release_panel.list_releases', return_value=completed):
            panel = ReleasePanel()
        self.assertEqual(panel.release_history.count(), 1)
        self.assertTrue(panel.open_release_button.isEnabled())
        self.assertEqual(panel.release_history.currentData(), '/tmp/spider-release-123')
        panel.close()


if __name__ == '__main__':
    unittest.main()
