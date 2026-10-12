"""Offscreen Qt: Studio v11 Quality Panel, safe DAW and cross-tab navigation."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import wave

from PyQt5.QtWidgets import QApplication, QLineEdit, QTabWidget, QWidget
from studio.audio_quality_panel import AudioQualityPanel
from studio.production_board_panel import ProductionBoardPanel

app = QApplication.instance() or QApplication([])


def make_wav(path):
    with wave.open(str(path), 'wb') as audio:
        audio.setframerate(16000)
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.writeframes(bytes(3200))


class AudioQualityPanelTests(unittest.TestCase):
    def test_no_unrequested_audio_analysis_or_capture(self):
        panel = AudioQualityPanel()
        self.assertFalse(panel.import_button.isEnabled())
        self.assertIsNone(panel.worker)
        with patch('studio.audio_quality_panel.AudioQualityWorker') as worker:
            panel.start_check()
            worker.assert_not_called()
        self.assertIn('Select', panel.status.text())
        panel.close()

    def test_explicit_import_and_async_worker_controls(self):
        with tempfile.TemporaryDirectory() as temp:
            wav_path = Path(temp) / 'guitar.wav'
            make_wav(wav_path)
            board = Mock()
            board.sources = {'rhythm_guitar': QLineEdit(str(wav_path))}
            # Real panel copies each known Production Board role.
            from studio.production_board import ROLES
            for role in ROLES:
                board.sources.setdefault(role, QLineEdit())
            panel = AudioQualityPanel(production_board=board)
            panel.import_board()
            self.assertEqual(panel.sources['rhythm_guitar'].text(), str(wav_path))
            with patch('studio.audio_quality_panel.AudioQualityWorker') as worker:
                panel.start_check()
                worker.assert_called_once()
                self.assertEqual(worker.call_args.args[0], {'rhythm_guitar': str(wav_path)})
                self.assertTrue(panel.cancel_button.isEnabled())
                panel.cancel_check()
                worker.return_value.stop.set.assert_called_once()
                panel.check_finished()
                self.assertTrue(panel.start_button.isEnabled())
            panel.close()

    def test_reports_measured_metrics_with_explicit_sampling_limits(self):
        panel = AudioQualityPanel()
        info = {
            'tracks': {'drums': {
                'sample_rate': 48000, 'channels': 2, 'sample_width_bits': 24,
                'duration_seconds': 121.0, 'sample_peak_dbfs': -0.15,
                'rms_dbfs': -15.4, 'near_full_scale_samples': 0,
                'warnings': ['Review by ear.'],
            }},
            'session_warnings': ['Track lengths differ.'],
        }
        panel.check_done(info, '')
        self.assertIn('first and last 8 seconds', panel.report.toPlainText().lower())
        self.assertIn('-15.4', panel.report.toPlainText())
        self.assertIn('Track lengths differ', panel.report.toPlainText())
        panel.close()

    def test_production_board_daw_handoff_never_autocopies_or_renders(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'lead.wav'
            make_wav(source)
            with patch('studio.production_board_panel.list_sessions', return_value=[]):
                board = ProductionBoardPanel()
            board.song_title.setText('Broken Sorrow Session')
            board.sources['lead_guitar'].setText(str(source))
            board.reviewed['lead_guitar'].setChecked(True)
            with patch('studio.production_board_panel.MultitrackDialog') as dialog:
                board.prepare_daw()
                dialog.assert_called_once()
                entries = dialog.call_args.args[0]
                self.assertEqual([x['role'] for x in entries], ['lead_guitar'])
                self.assertEqual(dialog.call_args.kwargs['title'], 'Broken Sorrow Session')
                dialog.return_value.exec_.assert_called_once()
                dialog.return_value.start_export.assert_not_called()
            board.close()

    def test_unreviewed_stems_are_excluded_and_quality_switch_does_not_start_scan(self):
        tabs = QTabWidget()
        for name in ('AI', 'Band', 'Release', 'Production', 'Audio QC'):
            tabs.addTab(QWidget(), name)
        with patch('studio.production_board_panel.list_sessions', return_value=[]):
            board = ProductionBoardPanel(tool_tabs=tabs)
        quality = Mock()
        quality.worker = None
        board.quality_panel = quality
        board.quality_tab = tabs.widget(4)
        board.open_quality()
        quality.import_board.assert_called_once()
        self.assertEqual(tabs.currentIndex(), 4)
        quality.start_check.assert_not_called()
        board.prepare_daw()
        self.assertIn('Review at least one', board.status.text())
        board.close()


if __name__ == '__main__':
    unittest.main()
