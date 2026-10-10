"""Barge-in tests: microphone continues listening for STOP while TTS runs."""
import importlib.util
import tempfile
from pathlib import Path
from unittest.mock import patch
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'webbie/voice/whisper_listener.py'
spec = importlib.util.spec_from_file_location('webbie_whisper_barge_test', SOURCE)
listener = importlib.util.module_from_spec(spec)
spec.loader.exec_module(listener)


class BargeInListenerTests(unittest.TestCase):
    def test_playback_audio_only_routes_to_stop_callback(self):
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder) / 'speaking'
            marker.write_text('speaking')
            ordinary, interrupt = [], []
            counter = iter([True, False])
            with (patch.object(listener, 'ready', return_value=True),
                  patch.object(listener, 'RUNTIME_DIR', Path(folder)),
                  patch.object(listener, 'SPEAKING_MARKER', marker),
                  patch.object(listener, 'record_chunk', return_value=True) as record,
                  patch.object(listener, 'transcribe', return_value='Webby stop')):
                listener.listen_forever(
                    on_text=ordinary.append, should_continue=lambda: next(counter),
                    on_interrupt=interrupt.append)
            self.assertEqual(ordinary, [])
            self.assertEqual(interrupt, ['Webby stop'])
            self.assertEqual(record.call_args.kwargs['seconds'], 2)

    def test_normal_speech_remains_in_regular_command_path(self):
        with tempfile.TemporaryDirectory() as folder:
            counter = iter([True, False])
            commands, interrupts = [], []
            with (patch.object(listener, 'ready', return_value=True),
                  patch.object(listener, 'RUNTIME_DIR', Path(folder)),
                  patch.object(listener, 'SPEAKING_MARKER', Path(folder)/'absent'),
                  patch.object(listener, 'record_chunk', return_value=True),
                  patch.object(listener, 'transcribe', return_value='Webbie open Audacity')):
                listener.listen_forever(
                    on_text=commands.append, should_continue=lambda: next(counter),
                    on_interrupt=interrupts.append)
            self.assertEqual(commands, ['Webbie open Audacity'])
            self.assertEqual(interrupts, [])


if __name__ == '__main__':
    unittest.main()
