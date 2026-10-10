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

    def test_multiple_singers_and_second_guitar_controls(self):
        with tempfile.TemporaryDirectory() as folder:
            panel = StudioAIPanel(folder)
            self.assertEqual(panel.voice_boxes[0].currentText(), 'Justin Therapy (original baritone)')
            panel.voice_boxes[1].setCurrentText('Original feminine alto')
            panel.voice_boxes[2].setCurrentText('J-Cold (original character voice)')
            self.assertTrue(panel.two_guitarists.isChecked())
            self.assertTrue(panel.guitar_two.isEnabled())
            panel.two_guitarists.setChecked(False)
            self.assertFalse(panel.guitar_two.isEnabled())
            panel.title.setText('Two guitar voices')
            panel.style.setPlainText('Dark metal')
            panel.lyrics.setPlainText('[Singer 1] Verse\\n[Singer 2] Chorus')
            with patch('studio.ai_panel.MusicWorker') as worker:
                panel.start()
                request = worker.call_args.args[1]
                self.assertIn('Original feminine alto', request.vocal_lineup)
                self.assertIn('J-Cold (original character voice)', request.vocal_lineup)
                self.assertEqual(request.guitar_two, '')
                self.assertIn('Guitarist 1', request.payload()['prompt'])
                worker.return_value.stop.set.assert_not_called()
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

    def test_finish_song_chain_requires_backing_and_model_then_calls_mixer(self):
        import wave
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            backing, lead, rendered = (root / name for name in ('instrumental.wav', 'lead.wav', 'converted.wav'))
            for path in (backing, lead, rendered):
                with wave.open(str(path), 'wb') as handle:
                    handle.setnchannels(1); handle.setsampwidth(2); handle.setframerate(8000)
                    handle.writeframes(b'\\0\\0' * 100)
            panel = StudioAIPanel(folder)
            panel.mix_backing.setText(str(backing))
            panel.rvc_vocal.setText(str(lead))
            model = root / 'my-voice.pth'
            model.write_bytes(b'test-model-placeholder')
            panel.rvc_model.setText(str(model))
            with patch.object(panel, 'start_conversion') as conversion, \
                 patch.object(panel, 'start_mix') as mixing:
                panel.start_song_finish()
                conversion.assert_called_once()
                self.assertFalse(panel.finish_song_button.isEnabled())
                panel.conversion_done(str(rendered), 'converted')
                mixing.assert_called_once()
                self.assertEqual(panel.mix_vocal.text(), str(rendered))
                self.assertFalse(panel.finish_after_conversion)
            panel.close()

    def test_finish_song_chain_rejects_untrained_model(self):
        import wave
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            backing, singer = root / 'backing.wav', root / 'isolated.wav'
            for source in (backing, singer):
                with wave.open(str(source), 'wb') as out:
                    out.setnchannels(1); out.setsampwidth(2); out.setframerate(8000)
                    out.writeframes(b'\\0\\0' * 100)
            panel = StudioAIPanel(folder)
            panel.mix_backing.setText(str(backing))
            panel.rvc_vocal.setText(str(singer))
            panel.rvc_model.setText(str(root / 'not-trained.pth'))
            with patch.object(panel, 'start_conversion') as conversion:
                panel.start_song_finish()
                conversion.assert_not_called()
                self.assertTrue(panel.finish_song_button.isEnabled())
                self.assertIn('trained', panel.status.text())
            panel.close()

    def test_engine_check_worker_reports_read_only_cli_result(self):
        from PyQt5.QtTest import QSignalSpy
        from studio.ai_panel import EngineCheckWorker
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'voice-engine.sh'
            path.write_text('#!/bin/bash\\n')
            worker = EngineCheckWorker(path)
            observed = QSignalSpy(worker.result)
            with patch('studio.ai_panel.subprocess.run') as audit:
                audit.return_value.stdout = 'Read-only hardware readiness check'
                worker.run()
                audit.assert_called_once()
                self.assertEqual(audit.call_args.args[0], ['bash', str(path), '--check'])
            self.assertEqual(len(observed), 1)
            self.assertIn('Read-only hardware', observed[0][0])

    def test_voice_training_setup_stays_read_only_and_launcher_requires_consent(self):
        from PyQt5.QtWidgets import QMessageBox
        with tempfile.TemporaryDirectory() as folder:
            panel = StudioAIPanel(folder)
            script = Path(folder) / 'voice-engine.sh'
            panel.training_script = script
            panel.check_training_engine()
            self.assertIn('not been installed', panel.engine_status.text())
            with patch('studio.ai_panel.QProcess') as process:
                panel.launch_trainer()
                process.assert_not_called()
            script.write_text('#!/bin/bash\nexit 0\n')
            with patch('studio.ai_panel.EngineCheckWorker') as audit:
                panel.check_training_engine()
                audit.assert_called_once_with(script)
                audit.return_value.start.assert_called_once()
                self.assertFalse(panel.engine_check_button.isEnabled())
                panel.engine_status.setText('RVC checkout: present; models need review')
                self.assertIn('models need review', panel.engine_status.text())
                panel.engine_check_finished()
                self.assertTrue(panel.engine_check_button.isEnabled())
            with patch('studio.ai_panel.QMessageBox.question', return_value=QMessageBox.No), \
                 patch('studio.ai_panel.QProcess') as process:
                panel.launch_trainer()
                process.assert_not_called()
            with patch('studio.ai_panel.QMessageBox.question', return_value=QMessageBox.Yes), \
                 patch('studio.ai_panel.QProcess') as process:
                panel.launch_trainer()
                process.assert_called_once()
                runner = process.return_value
                runner.setArguments.assert_called_once_with([str(script), '--launch-local'])
                runner.setProgram.assert_called_once_with('bash')
                runner.start.assert_called_once()
                self.assertFalse(panel.training_launch_button.isEnabled())
                panel.trainer_finished(0, 0)
                self.assertTrue(panel.training_launch_button.isEnabled())
            panel.close()

    def test_training_readiness_reports_usable_and_rejected_clips(self):
        with tempfile.TemporaryDirectory() as folder:
            panel = StudioAIPanel(folder)
            panel.voice_readiness_done({
                'total_seconds': 480.0, 'usable_clips': 16, 'rejected_clips': 1,
                'ready_to_prepare': False,
            })
            self.assertIn('8.0 of 10 minutes', panel.readiness_details.text())
            self.assertIn('1 recording(s) rejected', panel.readiness_details.text())
            self.assertIn('2.0 more usable minutes', panel.readiness_details.text())
            panel.voice_readiness_done({
                'total_seconds': 660.0, 'usable_clips': 22, 'rejected_clips': 0,
                'ready_to_prepare': True,
            })
            self.assertIn('Ready to prepare', panel.readiness_details.text())
            self.assertIn('No model has been trained', panel.readiness_details.text())
            panel.voice_readiness_done({'error': 'ffprobe is missing'})
            self.assertIn('ffprobe is missing', panel.readiness_details.text())
            panel.close()

    def test_training_readiness_uses_background_worker(self):
        with tempfile.TemporaryDirectory() as folder:
            panel = StudioAIPanel(folder)
            with patch('studio.ai_panel.TrainingReadinessWorker') as worker:
                panel.check_voice_readiness()
                worker.assert_called_once()
                self.assertFalse(panel.readiness_button.isEnabled())
                self.assertIn('Checking', panel.readiness_details.text())
            panel.close()

    def test_finish_song_chain_rejects_missing_instrumental(self):
        with tempfile.TemporaryDirectory() as folder:
            panel = StudioAIPanel(folder)
            panel.rvc_model.setText(str(Path(folder) / 'model.pth'))
            with patch.object(panel, 'start_conversion') as conversion:
                panel.start_song_finish()
                conversion.assert_not_called()
                self.assertTrue(panel.finish_song_button.isEnabled())
            panel.close()

    def test_voice_mixing_ui_uses_two_distinct_wavs_and_converted_output(self):
        import wave
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            backing, singer = root / 'backing.wav', root / 'voice.wav'
            for path in (backing, singer):
                with wave.open(str(path), 'wb') as wavfile:
                    wavfile.setnchannels(1); wavfile.setsampwidth(2); wavfile.setframerate(8000)
                    wavfile.writeframes(b'\\0\\0' * 100)
            panel = StudioAIPanel(folder)
            panel.mix_backing.setText(str(backing))
            panel.mix_vocal.setText(str(singer))
            panel.mix_voice_gain.setValue(.75)
            with patch('studio.ai_panel.VoiceMixWorker') as worker:
                panel.start_mix()
                worker.assert_called_once_with(str(backing), str(singer), .75, 1.0)
            panel.mix_done(str(root / 'final.wav'), 'Saved')
            self.assertIn('final.wav', panel.status.text())
            panel.conversion_done(str(singer), 'converted')
            self.assertEqual(panel.mix_vocal.text(), str(singer))
            panel.close()

    def test_voice_mix_rejects_missing_and_duplicate_source(self):
        import wave
        with tempfile.TemporaryDirectory() as folder:
            panel = StudioAIPanel(folder)
            with patch('studio.ai_panel.VoiceMixWorker') as worker:
                panel.start_mix()
                worker.assert_not_called()
            song = Path(folder) / 'voice.wav'
            with wave.open(str(song), 'wb') as wavfile:
                wavfile.setnchannels(1); wavfile.setsampwidth(2); wavfile.setframerate(8000)
                wavfile.writeframes(b'\\0\\0' * 100)
            panel.mix_backing.setText(str(song))
            panel.mix_vocal.setText(str(song))
            with patch('studio.ai_panel.VoiceMixWorker') as worker:
                panel.start_mix()
                worker.assert_not_called()
            self.assertIn('different', panel.status.text())
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
