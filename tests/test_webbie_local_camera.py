"""No startup webcam access, no cloud destinations, one-frame consent semantics."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('local_camera', ROOT / 'webbie/vision/local_camera.py')
camera = importlib.util.module_from_spec(spec)
spec.loader.exec_module(camera)
SAMPLE = b'\xff\xd8private-in-memory-test-frame\xff\xd9'


class CameraTests(unittest.TestCase):
    def test_import_status_and_invalid_device_never_capture(self):
        with patch.object(camera.subprocess, 'run') as runner:
            with patch.object(camera.Path, 'exists', return_value=False):
                self.assertEqual(camera.camera_status(), 'not found')
            with self.assertRaises(ValueError):
                camera.capture_one('/tmp/private-file', runner=runner)
            with self.assertRaises(ValueError):
                camera.capture_one('/dev/video0;rm -rf HOME', runner=runner)
            runner.assert_not_called()

    def test_one_frame_only_in_memory(self):
        class Result:
            returncode = 0
            stdout = SAMPLE
        calls = []
        def fake(args, **kwargs):
            calls.append((args, kwargs))
            return Result()
        with tempfile.TemporaryDirectory() as temporary:
            original = tuple(Path(temporary).iterdir())
            image = camera.capture_one('/dev/video2', runner=fake)
            self.assertEqual(image, SAMPLE)
            argv, kwargs = calls[0]
            self.assertEqual(argv[argv.index('-i') + 1], '/dev/video2')
            self.assertEqual(argv[argv.index('-frames:v') + 1], '1')
            self.assertEqual(argv[-1], 'pipe:1')
            self.assertEqual(kwargs['timeout'], 12)
            self.assertEqual(tuple(Path(temporary).iterdir()), original)

    def test_model_receives_only_loopback_image_and_no_cloud(self):
        message = json.dumps({'response': 'A desk and a lamp.'}).encode('utf-8')
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return None
            def read(self, n): return message
        class Opener:
            def __init__(self): self.calls = []
            def open(self, request, timeout):
                self.calls.append((request, timeout))
                return Response()
        client = Opener()
        self.assertEqual(camera.describe(SAMPLE, 'qwen2.5vl:3b', client), 'A desk and a lamp.')
        self.assertEqual(len(client.calls), 1)
        request, timeout = client.calls[0]
        self.assertEqual(request.full_url, 'http://127.0.0.1:11434/api/generate')
        self.assertEqual(timeout, 90)
        payload = json.loads(request.data)
        self.assertEqual(payload['model'], 'qwen2.5vl:3b')
        self.assertFalse(payload['stream'])
        self.assertEqual(len(payload['images']), 1)
        self.assertIn('single moment', payload['prompt'])

    def test_bad_models_and_frames_cannot_hit_network(self):
        with self.assertRaises(ValueError):
            camera.describe(SAMPLE, 'bad model')
        with self.assertRaises(ValueError):
            camera.describe(b'NOT_A_JPEG', 'qwen2.5vl:3b')
        with self.assertRaises(ValueError):
            camera.describe(b'\xff\xd8' + b'x' * camera.MAX_JPEG_BYTES + b'\xff\xd9',
                            'qwen2.5vl:3b')


if __name__ == '__main__':
    unittest.main()
