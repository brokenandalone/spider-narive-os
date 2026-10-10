"""Stoppable, safely bound TTS process tests; no speech is played."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock

SOURCE = Path(__file__).resolve().parents[1] / 'webbie/voice/interruptible_speech.py'
spec = importlib.util.spec_from_file_location('interruptible_speech', SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class FakeProcess:
    def __init__(self):
        self.terminated = False
        self.killed = False
    def poll(self):
        return None if not self.terminated else -15
    def terminate(self):
        self.terminated = True
    def kill(self):
        self.killed = True
    def wait(self, timeout=None):
        return -15 if self.terminated else 0


class InterruptSpeechTests(unittest.TestCase):
    def test_offline_uses_exact_arguments_no_shell(self):
        process = FakeProcess()
        launcher = Mock(return_value=process)
        engine = mod.InterruptibleSpeech(
            popen=launcher, which=lambda name: '/usr/bin/espeak-ng'
            if name == 'espeak-ng' else None, edge_tts=False)
        self.assertTrue(engine.speak('Good morning'))
        argv, kwargs = launcher.call_args
        self.assertEqual(argv[0][-1], 'Good morning')
        self.assertNotIn('shell', kwargs)

    def test_stop_signals_and_terminates_active_speech(self):
        process = FakeProcess()
        engine = mod.InterruptibleSpeech(
            popen=lambda *a, **k: process,
            which=lambda name: '/usr/bin/espeak-ng' if name == 'espeak-ng' else None,
            edge_tts=False)
        engine._active = process
        self.assertTrue(engine.stop()['stop_requested'])
        self.assertTrue(engine.cancelled.is_set())
        self.assertTrue(process.terminated)
        engine.cancelled.set()
        self.assertFalse(engine._execute(['espeak-ng', 'test']))


if __name__ == '__main__':
    unittest.main()
