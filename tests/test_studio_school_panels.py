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

    def test_prepared_voice_dataset_can_open_and_copy_private_audio_path(self):
        with tempfile.TemporaryDirectory() as folder:
            panel = StudioAIPanel(folder)
            self.assertFalse(panel.open_dataset_button.isEnabled())
            self.assertFalse(panel.copy_dataset_button.isEnabled())
            prepared = Path(folder) / 'dataset-one'
            (prepared / 'audio').mkdir(parents=True)
            (prepared / 'manifest.json').write_text('{"owner_consent":true}')
            panel.dataset_result(True, str(prepared))
            self.assertTrue(panel.open_dataset_button.isEnabled())
            self.assertTrue(panel.copy_dataset_button.isEnabled())
            with patch('studio.ai_panel.QDesktopServices.openUrl') as opener:
                panel.open_dataset()
                opener.assert_called_once()
                self.assertEqual(opener.call_args.args[0].toLocalFile(), str(prepared))
            with patch('studio.ai_panel.QApplication.clipboard') as clipboard:
                panel.copy_dataset_path()
                clipboard.return_value.setText.assert_called_once_with(str(prepared / 'audio'))
                self.assertIn('copied', panel.voice_status.text())
            panel.dataset_result(False, 'Not enough usable recordings')
            self.assertFalse(panel.open_dataset_button.isEnabled())
            self.assertFalse(panel.copy_dataset_button.isEnabled())
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

    def test_owner_model_save_requires_confirmation_and_never_deserializes(self):
        from PyQt5.QtWidgets import QMessageBox
        with tempfile.TemporaryDirectory() as folder:
            panel = StudioAIPanel(folder)
            panel.rvc_model.setText(str(Path(folder) / 'trained.pth'))
            panel.rvc_index.setText(str(Path(folder) / 'trained.index'))
            with patch('studio.ai_panel.QMessageBox.question', return_value=QMessageBox.No), \
                 patch('studio.ai_panel.remember_owner_model') as saver:
                panel.remember_my_voice_model()
                saver.assert_not_called()
            with patch('studio.ai_panel.QMessageBox.question', return_value=QMessageBox.Yes), \
                 patch('studio.ai_panel.remember_owner_model') as saver:
                panel.remember_my_voice_model()
                saver.assert_called_once_with(
                    str(Path(folder) / 'trained.pth'), str(Path(folder) / 'trained.index'), consent=True)
                self.assertIn('No audio identity verified', panel.saved_model_status.text())
            panel.close()

    def test_owner_model_restore_and_forget_do_not_delete_weights(self):
        with tempfile.TemporaryDirectory() as folder:
            panel = StudioAIPanel(folder)
            paths = {'model': str(Path(folder) / 'owner.pth'),
                     'index': str(Path(folder) / 'owner.index')}
            with patch('studio.ai_panel.load_owner_model', return_value=paths):
                panel.restore_my_voice_model()
                self.assertEqual(panel.rvc_model.text(), paths['model'])
                self.assertEqual(panel.rvc_index.text(), paths['index'])
                self.assertIn('listening test', panel.saved_model_status.text())
            with patch('studio.ai_panel.forget_owner_model') as forgetting:
                panel.forget_my_voice_model()
                forgetting.assert_called_once()
                self.assertEqual(panel.rvc_model.text(), '')
                self.assertEqual(panel.rvc_index.text(), '')
                self.assertIn('remain untouched', panel.saved_model_status.text())
            with patch('studio.ai_panel.load_owner_model', return_value=None):
                panel.restore_my_voice_model()
                self.assertIn('No valid saved owner model', panel.saved_model_status.text())
            panel.close()

    def test_generated_take_handoff_never_starts_heavy_model_automatically(self):
        import wave
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            studio = root / 'songs'
            source_dir = studio / 'song-test'
            source_dir.mkdir(parents=True)
            wav = source_dir / 'take-1.wav'
            with wave.open(str(wav), 'wb') as audio:
                audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(8000)
                audio.writeframes(b'\\0\\0' * 100)
            panel = StudioAIPanel(studio)
            with patch.object(panel, 'selected', return_value=wav), \
                 patch('studio.ai_panel.SeparationWorker') as worker:
                panel.use_take_for_separation()
                self.assertEqual(panel.separation_source.text(), str(wav.resolve()))
                worker.assert_not_called()
                self.assertIn('when ready', panel.status.text())
            outside = root / 'outside.wav'
            outside.write_bytes(wav.read_bytes())
            with patch.object(panel, 'selected', return_value=outside):
                panel.use_take_for_separation()
                self.assertIn('not a saved Spider Studio', panel.status.text())
            panel.close()

    def test_stem_separation_requires_opt_in_and_can_be_stopped(self):
        import wave
        from PyQt5.QtWidgets import QMessageBox
        with tempfile.TemporaryDirectory() as folder:
            wav = Path(folder) / 'song.wav'
            with wave.open(str(wav), 'wb') as audio:
                audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(8000)
                audio.writeframes(b'\\0\\0' * 100)
            panel = StudioAIPanel(folder)
            panel.separation_source.setText(str(wav))
            with patch('studio.ai_panel.QMessageBox.question', return_value=QMessageBox.No), \
                 patch('studio.ai_panel.SeparationWorker') as worker:
                panel.start_separation()
                worker.assert_not_called()
                self.assertFalse(panel.stop_separation_button.isEnabled())
            with patch('studio.ai_panel.QMessageBox.question', return_value=QMessageBox.Yes), \
                 patch('studio.ai_panel.SeparationWorker') as worker:
                panel.start_separation()
                worker.assert_called_once_with(str(wav.resolve()))
                worker.return_value.start.assert_called_once()
                self.assertTrue(panel.stop_separation_button.isEnabled())
                panel.cancel_separation()
                worker.return_value.stop.set.assert_called_once()
                self.assertFalse(panel.stop_separation_button.isEnabled())
                panel.separation_finished()
                self.assertTrue(panel.separate_button.isEnabled())
            panel.close()

    def test_explicit_review_and_assignment_of_separated_stems(self):
        import wave
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            vocal, instrumental, unrelated = (root / name for name in
                                              ('singing.wav', 'backing.wav', 'unrelated.wav'))
            for source in (vocal, instrumental, unrelated):
                with wave.open(str(source), 'wb') as wavfile:
                    wavfile.setnchannels(1); wavfile.setsampwidth(2); wavfile.setframerate(8000)
                    wavfile.writeframes(b'\\0\\0' * 100)
            panel = StudioAIPanel(folder)
            self.assertEqual(panel.stem_candidates.count(), 0)
            panel.separation_done(str(root), [str(vocal), str(instrumental)], 'Stems ready')
            self.assertEqual(panel.stem_candidates.count(), 2)
            self.assertFalse(panel.rvc_vocal.text())
            self.assertFalse(panel.mix_backing.text())
            panel.stem_candidates.setCurrentRow(0)
            with patch('studio.ai_panel.QDesktopServices.openUrl') as player:
                player.return_value = True
                panel.listen_stem()
                player.assert_called_once()
                self.assertEqual(player.call_args.args[0].toLocalFile(), str(vocal))
            panel.assign_vocal_stem()
            self.assertEqual(panel.rvc_vocal.text(), str(vocal))
            panel.assign_instrumental_stem()
            self.assertIn('already assigned', panel.status.text())
            self.assertFalse(panel.mix_backing.text())
            panel.stem_candidates.setCurrentRow(1)
            panel.assign_instrumental_stem()
            self.assertEqual(panel.mix_backing.text(), str(instrumental))
            panel.assign_vocal_stem()
            self.assertIn('already assigned', panel.status.text())
            self.assertEqual(panel.rvc_vocal.text(), str(vocal))
            self.assertNotIn(unrelated.resolve(), panel.separation_files)
            panel.close()

    def test_separated_stem_rejects_out_of_job_and_clears_failed_results(self):
        import wave
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            job = root / 'stems'
            job.mkdir()
            good = job / 'voice.wav'
            elsewhere = root / 'other.wav'
            for source in (good, elsewhere):
                with wave.open(str(source), 'wb') as audio:
                    audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(8000)
                    audio.writeframes(b'\\0\\0' * 100)
            panel = StudioAIPanel(folder)
            panel.separation_done(str(job), [str(good), str(elsewhere)], 'ready')
            self.assertEqual(panel.stem_candidates.count(), 1)
            panel.stem_candidates.setCurrentRow(0)
            panel.assign_vocal_stem()
            self.assertEqual(panel.rvc_vocal.text(), str(good))
            panel.separation_done('', [], 'engine failed')
            self.assertEqual(panel.stem_candidates.count(), 0)
            self.assertIsNone(panel.separation_directory)
            self.assertIn('engine failed', panel.status.text())
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
