"""Tests for short-lived local recognition captions under Webbie's portrait."""
import importlib.util
import os
from pathlib import Path
import stat
import tempfile
import time
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "webbie/agent/heard_caption.py"
spec = importlib.util.spec_from_file_location("webbie_heard_caption_test", MODULE)
caption = importlib.util.module_from_spec(spec)
spec.loader.exec_module(caption)


class WebbieHeardCaptionTests(unittest.TestCase):
    def test_caption_only_in_private_runtime_and_expires(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"XDG_RUNTIME_DIR": directory}):
                self.assertEqual(caption.latest_heard(), "")
                self.assertTrue(caption.publish_heard("Hey Webby, hello"))
                self.assertEqual(caption.latest_heard(), "Hey Webby, hello")
                mode = stat.S_IMODE(caption.caption_path().stat().st_mode)
                self.assertEqual(mode, 0o600)
                future = time.time() + caption.DISPLAY_SECONDS + 1
                self.assertEqual(caption.latest_heard(now=future), "")

    def test_ready_requires_recent_overlay_heartbeat(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"XDG_RUNTIME_DIR": directory}):
                self.assertFalse(caption.overlay_ready())
                caption.pulse_overlay()
                self.assertTrue(caption.overlay_ready())
                self.assertFalse(caption.overlay_ready(now=time.time() + 9))

    def test_empty_caption_is_not_published(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"XDG_RUNTIME_DIR": directory}):
                self.assertFalse(caption.publish_heard("  "))
                self.assertFalse(caption.caption_path().exists())


if __name__ == "__main__":
    unittest.main()
