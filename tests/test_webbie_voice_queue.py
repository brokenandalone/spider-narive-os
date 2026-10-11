"""No-hardware regression tests for Webbie's single-slot voice correction queue."""
import importlib.util
from pathlib import Path
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


queue = load("webbie/agent/voice_queue.py", "webbie_voice_queue_test")
turns = load("webbie/agent/voice_turns.py", "webbie_voice_turns_queue_test")


class VoiceQueueTests(unittest.TestCase):
    def test_latest_followup_replaces_older_pending_turn(self):
        entered = threading.Event()
        release = threading.Event()
        finished = threading.Event()
        received = []

        def run(command, generation, verified):
            received.append((command, verified))
            if command == "first":
                entered.set()
                self.assertTrue(release.wait(2))
            if command == "third":
                finished.set()

        coordinator = queue.VoiceTurnCoordinator(run, turns.VoiceTurnTracker())
        self.assertEqual(coordinator.submit("first"), "started")
        self.assertTrue(entered.wait(2))
        self.assertEqual(coordinator.submit("second"), "queued")
        self.assertEqual(coordinator.submit("third"), "queued")
        self.assertEqual(coordinator.snapshot(), {"busy": True, "queued": True})
        release.set()
        self.assertTrue(finished.wait(2))
        self.assertEqual(received, [("first", False), ("third", False)])

    def test_new_correction_invalidates_old_generation_immediately(self):
        entered=threading.Event()
        release=threading.Event()
        replacement_done=threading.Event()
        generations=[]
        stopped=[]
        tracker=turns.VoiceTurnTracker()

        def run(command,generation,verified):
            generations.append((command,generation))
            if command=="slow":
                entered.set()
                self.assertTrue(release.wait(3))
            if command=="latest":
                replacement_done.set()

        coordinator=queue.VoiceTurnCoordinator(
            run,tracker,on_supersede=lambda:stopped.append("speech stopped"))
        self.assertEqual(coordinator.submit("slow"),"started")
        self.assertTrue(entered.wait(2))
        old_generation=generations[0][1]
        self.assertEqual(coordinator.submit("intermediate"),"queued")
        self.assertFalse(tracker.current(old_generation))
        self.assertEqual(coordinator.submit("latest"),"queued")
        self.assertEqual(len(stopped),2)
        release.set()
        self.assertTrue(replacement_done.wait(3))
        self.assertEqual([x[0] for x in generations],["slow","latest"])
        self.assertNotEqual(generations[0][1],generations[1][1])

    def test_stop_discards_old_turn_then_accepts_correction(self):
        entered = threading.Event()
        release = threading.Event()
        corrected = threading.Event()
        received = []
        tracker = turns.VoiceTurnTracker()

        def run(command, generation, verified):
            received.append((command, generation))
            if command == "old":
                entered.set()
                self.assertTrue(release.wait(2))
            if command == "corrected":
                corrected.set()

        coordinator = queue.VoiceTurnCoordinator(run, tracker)
        coordinator.submit("old")
        self.assertTrue(entered.wait(2))
        self.assertEqual(coordinator.submit("obsolete"), "queued")
        coordinator.cancel()
        self.assertFalse(coordinator.snapshot()["queued"])
        self.assertEqual(coordinator.submit("corrected"), "queued")
        release.set()
        self.assertTrue(corrected.wait(2))
        self.assertEqual([item[0] for item in received], ["old", "corrected"])
        self.assertNotEqual(received[0][1], received[1][1])

    def test_sleep_prevents_pending_turn_from_executing(self):
        entered = threading.Event()
        release = threading.Event()
        idle = threading.Event()
        allowed = [True]
        received = []

        def run(command, generation, verified):
            received.append(command)
            if command == "first":
                entered.set()
                release.wait(2)
                idle.set()

        coordinator = queue.VoiceTurnCoordinator(
            run, turns.VoiceTurnTracker(), can_run=lambda: allowed[0])
        coordinator.submit("first")
        self.assertTrue(entered.wait(2))
        coordinator.submit("unwanted")
        allowed[0] = False
        release.set()
        self.assertTrue(idle.wait(2))
        # Joining the worker isn't necessary: the pending item fails can_run.
        self.assertEqual(received, ["first"])
        self.assertEqual(coordinator.submit("asleep"), "ignored")

    def test_expired_correction_does_not_run_late(self):
        entered = threading.Event()
        release = threading.Event()
        done = threading.Event()
        clock = [100.0]
        received = []

        def run(command, generation, verified):
            received.append(command)
            entered.set()
            release.wait(2)
            done.set()

        coordinator = queue.VoiceTurnCoordinator(
            run, turns.VoiceTurnTracker(), clock=lambda: clock[0])
        coordinator.submit("first")
        self.assertTrue(entered.wait(2))
        coordinator.submit("too late")
        clock[0] = 146.0
        release.set()
        self.assertTrue(done.wait(2))
        self.assertEqual(received, ["first"])

    def test_untrusted_truthy_values_never_become_verified(self):
        done = threading.Event()
        received = []

        def run(command, generation, verified):
            received.append(verified)
            done.set()

        coordinator = queue.VoiceTurnCoordinator(run, turns.VoiceTurnTracker())
        coordinator.submit("read only", speaker_verified=1)
        self.assertTrue(done.wait(2))
        self.assertEqual(received, [False])

    def test_worker_errors_do_not_trap_followup_state(self):
        done = threading.Event()
        errors = []

        def run(command, generation, verified):
            done.set()
            raise RuntimeError("test failure")

        coordinator = queue.VoiceTurnCoordinator(
            run, turns.VoiceTurnTracker(), on_error=errors.append)
        coordinator.submit("one")
        self.assertTrue(done.wait(2))
        # Error callback is invoked synchronously in the same worker.
        for _ in range(50):
            if errors:
                break
            threading.Event().wait(.01)
        self.assertEqual(len(errors), 1)
        self.assertFalse(coordinator.snapshot()["busy"])

    def test_bad_ttl_and_blank_commands_are_rejected(self):
        with self.assertRaises(ValueError):
            queue.VoiceTurnCoordinator(lambda *_: None, turns.VoiceTurnTracker(), queue_ttl=60)
        coordinator = queue.VoiceTurnCoordinator(lambda *_: None, turns.VoiceTurnTracker())
        self.assertEqual(coordinator.submit("  "), "ignored")


if __name__ == "__main__":
    unittest.main()
