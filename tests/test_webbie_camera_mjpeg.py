"""Regression tests for the owner's onn 4K webcam capture settings.

Only subprocess mocks are used. No camera, microphone or cloud service is touched.
"""
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "the-web/shell/webbie_camera.py"
spec = importlib.util.spec_from_file_location("webbie_camera_mjpeg_test", SOURCE)
camera = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = camera
spec.loader.exec_module(camera)
JPEG = b"\xff\xd8" + b"simulated jpeg content" + b"\xff\xd9"


class OnnWebcamTests(unittest.TestCase):
    def test_validated_device_uses_640x480_mjpeg_at_15_fps(self):
        class Result:
            returncode = 0
            stdout = JPEG
        with patch.object(camera, "valid_camera_path", return_value="/dev/video0"):
            with patch.object(camera.subprocess, "run", return_value=Result()) as runner:
                self.assertEqual(camera.capture_jpeg("/dev/video0"), JPEG)
        argv = runner.call_args.args[0]
        for switch, value in (
            ("-input_format", "mjpeg"),
            ("-video_size", "640x480"),
            ("-framerate", "15"),
            ("-i", "/dev/video0"),
            ("-frames:v", "1"),
        ):
            self.assertEqual(argv[argv.index(switch) + 1], value)
        self.assertEqual(argv[-1], "pipe:1")

    def test_capture_timeout_is_reported_clearly(self):
        with patch.object(camera, "valid_camera_path", return_value="/dev/video0"):
            with patch.object(camera.subprocess, "run", side_effect=subprocess.TimeoutExpired("ffmpeg", 12)):
                with self.assertRaisesRegex(RuntimeError, "timed out at 640x480 MJPEG"):
                    camera.capture_jpeg("/dev/video0")

    def test_failed_camera_still_does_not_return_corrupted_image(self):
        class Result:
            returncode = 1
            stdout = b""
        with patch.object(camera, "valid_camera_path", return_value="/dev/video0"):
            with patch.object(camera.subprocess, "run", return_value=Result()):
                with self.assertRaisesRegex(RuntimeError, "Unable to read webcam"):
                    camera.capture_jpeg("/dev/video0")


if __name__ == "__main__":
    unittest.main()
