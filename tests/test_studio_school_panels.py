"""Native workspace checks with no school login or model service."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import QUrl
from PyQt5.QtTest import QTest
import time
from studio.ai_panel import StudioAIPanel, BROKEN_SORROW
from study.school_portal import SchoolPortal, SCHOOL_URL

app = QApplication.instance() or QApplication([])


class NativeWorkspaceTests(unittest.TestCase):
    def test_invalid_song_never_starts_worker(self):
        with tempfile.TemporaryDirectory() as folder:
            panel = StudioAIPanel(folder)
            with patch('studio.ai_panel.MusicWorker') as worker:
                panel.start()
                worker.assert_not_called()
            self.assertIn('title', panel.status.text())
            panel.preset.click()
            self.assertEqual(panel.style.toPlainText(), BROKEN_SORROW)
            panel.instrumental.setChecked(True)
            self.assertFalse(panel.lyrics.isEnabled())
            panel.close()

    def test_worker_runs_without_blocking_panel_and_reenables_controls(self):
        with tempfile.TemporaryDirectory() as folder:
            panel = StudioAIPanel(folder)
            client = Mock()
            client.health.side_effect = lambda: time.sleep(0.05)
            with patch('studio.ai_panel.LocalMusicClient', return_value=client):
                panel.start(check_only=True)
                worker = panel.worker
                self.assertIsNotNone(worker)
                self.assertFalse(panel.generate.isEnabled())
                panel.start(check_only=True)
                self.assertIs(panel.worker, worker)
                deadline = time.monotonic() + 3
                while panel.worker is not None and time.monotonic() < deadline:
                    QTest.qWait(10)
                worker = panel.worker
                if worker is not None:
                    worker.shutdown()
                self.assertIsNone(panel.worker)
                self.assertTrue(panel.generate.isEnabled())
                client.health.assert_called_once()
            panel.close()

    def test_saved_take_handoff_uses_existing_tool_resolver(self):
        with tempfile.TemporaryDirectory() as folder:
            job = Path(folder) / 'song-test'; job.mkdir()
            take = job / 'take-1.wav'; take.write_bytes(b'test-fixture')
            (job / 'job.json').write_text(json.dumps({'request': {'title':'Song'}, 'files':['take-1.wav', '../outside.wav']}))
            panel = StudioAIPanel(folder)
            self.assertEqual(panel.library.count(), 1)
            panel.library.setCurrentRow(0)
            with patch('studio.ai_panel.resolve_tool', return_value=['/usr/bin/audacity']), patch('studio.ai_panel.subprocess.Popen') as launch:
                panel.edit_audio()
                launch.assert_called_once_with(['/usr/bin/audacity', str(take)])
            panel.close()

    def test_portal_opens_once_and_browser_fallback_uses_stable_entry(self):
        with tempfile.TemporaryDirectory() as folder:
            panel = SchoolPortal(lambda: Path(folder))
            view = Mock()
            def create():
                panel.views.append(view)
                return view
            with patch.object(panel, 'ensure_browser', return_value=True), patch.object(panel, 'new_view', side_effect=create):
                panel.open(); panel.open()
                view.setUrl.assert_called_once_with(QUrl(SCHOOL_URL))
            with patch('study.school_portal.QDesktopServices.openUrl', return_value=True) as launch:
                panel.external(); launch.assert_called_once_with(QUrl(SCHOOL_URL))
            panel.close()

    def test_download_follows_current_course_and_cancel_does_not_accept(self):
        with tempfile.TemporaryDirectory() as folder:
            course = Path(folder) / 'Course A'
            panel = SchoolPortal(lambda: course)
            item = Mock(); item.path.return_value = '/remote/assignment.pdf'
            target = str(course / 'Downloads/assignment.pdf')
            with patch('study.school_portal.QFileDialog.getSaveFileName', return_value=(target,'')) as save:
                panel.download(item)
                self.assertEqual(save.call_args.args[2], target)
                item.setPath.assert_called_once_with(target); item.accept.assert_called_once()
            course = Path(folder) / 'Course B'
            item.reset_mock()
            with patch('study.school_portal.QFileDialog.getSaveFileName', return_value=('','')) as save:
                panel.download(item)
                self.assertIn('Course B', save.call_args.args[2])
                item.cancel.assert_called_once(); item.accept.assert_not_called()
            panel.close()
