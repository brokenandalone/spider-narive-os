"""No-microphone tests for bounded Webbie listener restarts."""
import importlib.util
from pathlib import Path
import unittest

source = Path(__file__).resolve().parents[1] / "webbie/agent/voice_supervisor.py"
spec = importlib.util.spec_from_file_location("voice_supervisor_tests", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class VoiceSupervisorTests(unittest.TestCase):
    def test_unexpected_exit_retries_with_backoff(self):
        active = [True]
        calls = []
        delays = []
        def listen():
            calls.append("listen")
            if len(calls) >= 3:
                active[0] = False
        def sleeper(seconds):
            delays.append(seconds)
        supervisor = module.VoiceSupervisor(
            listen, lambda: active[0], sleeper=sleeper,
            min_delay=2, max_delay=4)
        supervisor.serve()
        self.assertEqual(calls, ["listen"] * 3)
        self.assertEqual(delays, [1, 1, 1, 1, 1, 1])

    def test_listener_failure_does_not_kill_supervisor(self):
        active = [True]
        events = []
        def listen():
            events.append("called")
            if len(events) >= 2:
                active[0] = False
            raise RuntimeError("test device unavailable")
        supervisor = module.VoiceSupervisor(
            listen, lambda: active[0],
            notify=lambda reason, wait: events.append((reason, wait)),
            sleeper=lambda seconds: None, min_delay=1, max_delay=2)
        supervisor.serve()
        self.assertEqual(events[1], ("listener_error", 1))
        self.assertEqual(events.count("called"), 2)

    def test_no_retry_on_clean_shutdown(self):
        active = [True]
        delayed = []
        def listen():
            active[0] = False
        supervisor = module.VoiceSupervisor(
            listen, lambda: active[0], sleeper=delayed.append)
        supervisor.serve()
        self.assertEqual(delayed, [])

    def test_stable_listener_resets_retry_window(self):
        active = [True]
        time = [0.0]
        events = []
        count = [0]
        def listen():
            count[0] += 1
            if count[0] == 2:
                time[0] += 150
            if count[0] >= 3:
                active[0] = False
        def sleeper(seconds):
            time[0] += seconds
        supervisor = module.VoiceSupervisor(
            listen, lambda: active[0], notify=lambda *args: events.append(args),
            sleeper=sleeper, clock=lambda: time[0], min_delay=2, max_delay=16)
        supervisor.serve()
        self.assertEqual(events, [
            ("listener_exited", 2), ("listener_exited", 2)])

    def test_rejects_broken_backoff(self):
        with self.assertRaises(ValueError):
            module.VoiceSupervisor(lambda: None, lambda: False, min_delay=0)
        with self.assertRaises(ValueError):
            module.VoiceSupervisor(lambda: None, lambda: False, min_delay=60,
                                   max_delay=4)

    def test_notify_errors_are_contained(self):
        active = [True]
        count = [0]
        def listen():
            count[0] += 1
            if count[0] == 2:
                active[0] = False
        def broken(*args):
            raise RuntimeError("down")
        module.VoiceSupervisor(
            listen, lambda: active[0], notify=broken,
            sleeper=lambda seconds: None, min_delay=1).serve()
        self.assertEqual(count[0], 2)


if __name__ == "__main__":
    unittest.main()
