"""Offscreen Production Board integration: source-stage approvals and tab handoffs."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import wave

from PyQt5.QtWidgets import QApplication, QLineEdit, QTabWidget, QWidget, QMessageBox
from studio.band_mix import ROLES as MIX_ROLES
from studio.production_board_panel import ProductionBoardPanel

app = QApplication.instance() or QApplication([])


def wav(path):
    with wave.open(str(path), 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(22050)
        audio.writeframes(bytes(4096))


def make_panel():
    ai = Mock()
    ai.selected.return_value = None
    ai.separation_worker = None
    ai.separation_source = QLineEdit()
    band = Mock()
    band.worker = None
    band.last_mix = None
    band.track_fields = {role: QLineEdit() for role in MIX_ROLES}
    release = Mock()
    release.worker = None
    release.source = QLineEdit()
    tabs = QTabWidget()
    for name in ('Studio AI', 'Band Mixer', 'Release Desk', 'Production Board'):
        tabs.addTab(QWidget(), name)
    with patch('studio.production_board_panel.list_sessions', return_value=[]):
        panel = ProductionBoardPanel(
            ai_panel=ai, band_mixer=band, release_panel=release, tool_tabs=tabs)
    return panel, ai, band, release, tabs


class ProductionBoardPanelTests(unittest.TestCase):
    def test_reference_is_not_verified_audio_and_does_not_start_model(self):
        with tempfile.TemporaryDirectory() as temp:
            full_mix = Path(temp) / 'full.wav'
            wav(full_mix)
            panel, ai, band, release, tabs = make_panel()
            ai.selected.return_value = full_mix
            panel.import_ai_take()
            self.assertEqual(panel.sources['reference_mix'].text(), str(full_mix))
            self.assertFalse(panel.reviewed['lead_vocal'].isChecked())
            panel.prepare_separation()
            self.assertEqual(ai.separation_source.text(), str(full_mix))
            self.assertEqual(tabs.currentIndex(), 0)
            ai.start_separation.assert_not_called()
            ai.start.assert_not_called()
            panel.close()

    def test_manual_source_edits_revoke_review_confirmation(self):
        panel, *_ = make_panel()
        panel.sources['rhythm_guitar'].setText('/tmp/first.wav')
        panel.reviewed['rhythm_guitar'].setChecked(True)
        panel.sources['rhythm_guitar'].setText('/tmp/second.wav')
        self.assertFalse(panel.reviewed['rhythm_guitar'].isChecked())
        panel.close()

    def test_send_two_approved_stems_requires_confirm_and_never_renders(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            files = [root / 'guitar.wav', root / 'drums.wav']
            for file in files: wav(file)
            panel, ai, band, release, tabs = make_panel()
            for role, file in zip(('rhythm_guitar', 'drums'), files):
                panel.sources[role].setText(str(file))
                panel.reviewed[role].setChecked(True)
            band.track_fields['keys'].setText('/tmp/previous.wav')
            with patch('studio.production_board_panel.QMessageBox.question',
                       return_value=QMessageBox.No):
                panel.prepare_mixer()
            self.assertEqual(band.track_fields['keys'].text(), '/tmp/previous.wav')
            with patch('studio.production_board_panel.QMessageBox.question',
                       return_value=QMessageBox.Yes):
                panel.prepare_mixer()
            self.assertEqual(band.track_fields['rhythm_guitar'].text(), str(files[0]))
            self.assertEqual(band.track_fields['drums'].text(), str(files[1]))
            self.assertEqual(band.track_fields['keys'].text(), '')
            self.assertEqual(tabs.currentIndex(), 1)
            band.start_mix.assert_not_called()
            panel.close()

    def test_send_final_wav_to_release_only_selects_no_export(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'finished.wav'
            wav(source)
            panel, ai, band, release, tabs = make_panel()
            band.last_mix = source
            panel.import_mix()
            self.assertEqual(panel.sources['final_mix'].text(), str(source))
            panel.prepare_release()
            self.assertEqual(release.source.text(), str(source))
            self.assertEqual(tabs.currentIndex(), 2)
            release.start_export.assert_not_called()
            panel.close()

    def test_save_produces_new_checkpoint_only_on_button(self):
        panel, *_ = make_panel()
        with (patch('studio.production_board_panel.create_session',
                    return_value='session-' + 'a' * 32) as create,
              patch('studio.production_board_panel.save_revision',
                    return_value=Path('/tmp/checkpoint.json')) as save):
            create.assert_not_called()
            save.assert_not_called()
            panel.song_title.setText('New Broken Sorrow Song')
            panel.save_checkpoint()
            create.assert_called_once()
            save.assert_called_once()
        panel.close()

    def test_load_session_approval_is_reestablished_only_from_saved_revision(self):
        panel, *_ = make_panel()
        token = 'session-' + 'b' * 32
        panel.session_list.addItem('Session', token)
        panel.session_list.setCurrentIndex(panel.session_list.count()-1)
        values = {'title': 'Reopen song', 'notes': 'Version 2',
                  'assets': {'lead_guitar': '/tmp/reviewed.wav'},
                  'reviewed_stems': {'lead_guitar': True},
                  'missing': ['lead_guitar']}
        with patch('studio.production_board_panel.load_session', return_value=values):
            panel.load_selected()
        self.assertEqual(panel.song_title.text(), 'Reopen song')
        self.assertTrue(panel.reviewed['lead_guitar'].isChecked())
        self.assertIn('Missing WAV', panel.status.text())
        panel.close()


if __name__ == '__main__':
    unittest.main()
