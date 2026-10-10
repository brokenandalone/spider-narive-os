"""Exercise the real local HTTP client against a disposable protocol fixture.

The tiny WAV fixture is test data, never a claimed model render.
"""
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'studio'))
spec = importlib.util.spec_from_file_location('music_backend_test', ROOT / 'studio/music_backend.py')
m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m; spec.loader.exec_module(m)


def wav_fixture():
    data = io.BytesIO()
    with wave.open(data, 'wb') as audio:
        audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(8000)
        audio.writeframes(b'\0\0' * 800)
    return data.getvalue()


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.audio = wav_fixture()
        self.status = 1
        self.result_url = '/v1/audio?path=fixture.wav'
        self.fixture = tempfile.TemporaryDirectory(); self.addCleanup(self.fixture.cleanup)
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                owner.calls.append((self.path, None, self.headers.get('Authorization')))
                if self.path.startswith('/v1/audio?'):
                    self.send_response(200); self.end_headers(); self.wfile.write(owner.audio)
                else:
                    self.reply({'status': 'ok'})
            def reply(self, data):
                self.send_response(200); self.end_headers()
                self.wfile.write(json.dumps({'code': 200, 'error': None, 'data': data}).encode())
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                owner.calls.append((self.path, payload, self.headers.get('Authorization')))
                if self.path == '/release_task':
                    self.reply({'task_id': 'fixture-task', 'status': 'queued'})
                else:
                    self.reply([{'task_id': 'fixture-task', 'status': owner.status,
                        'result': json.dumps([{'file': owner.result_url, 'status': 1}])}])
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.addCleanup(self.server.server_close); self.addCleanup(self.server.shutdown)
        self.client = m.LocalMusicClient(f'http://127.0.0.1:{self.server.server_port}', 'test-only-token')
        self.song = m.SongRequest('Test title', 'Piano and baritone', '[Verse]\nFixture lyrics')

    def test_http_submit_poll_validate_and_save(self):
        folder = self.client.generate(self.song, self.fixture.name)
        job = json.loads((folder / 'job.json').read_text())
        self.assertEqual(job['status'], 'completed')
        self.assertEqual((folder / 'take-1.wav').read_bytes(), self.audio)
        self.assertEqual((folder / 'job.json').stat().st_mode & 0o777, 0o600)
        self.assertEqual(folder.stat().st_mode & 0o777, 0o700)
        self.assertNotIn('test-only-token', (folder / 'job.json').read_text())
        self.assertEqual([x[0] for x in self.calls], ['/health', '/release_task', '/query_result', '/v1/audio?path=fixture.wav'])
        self.assertEqual(self.calls[1][1]['lyrics'], self.song.lyrics)
        self.assertFalse(self.calls[1][1]['use_cot_caption'])
        self.assertTrue(all(x[2] == 'Bearer test-only-token' for x in self.calls))

    def test_fresh_variants_never_overwrite(self):
        one = self.client.generate(self.song, self.fixture.name)
        two = self.client.generate(self.song, self.fixture.name)
        self.assertNotEqual(one, two)
        self.assertEqual((one / 'take-1.wav').read_bytes(), self.audio)

    def test_failed_task_does_not_report_audio_success(self):
        self.status = 2
        with self.assertRaises(m.MusicError): self.client.generate(self.song, self.fixture.name)
        job = json.loads(next(Path(self.fixture.name).glob('*/job.json')).read_text())
        self.assertEqual(job['status'], 'error'); self.assertEqual(job['files'], [])

    def test_unsafe_result_url_is_not_requested(self):
        self.result_url = 'https://example.com/steal'
        with self.assertRaises(m.MusicError): self.client.generate(self.song, self.fixture.name)
        self.assertEqual(len(self.calls), 3)

    def test_invalid_audio_never_becomes_a_take(self):
        for content in (b'<html>not audio</html>', wav_fixture()[:-20]):
            self.audio = content
            with self.assertRaises(m.MusicError): self.client.generate(self.song, self.fixture.name)
        self.assertFalse(list(Path(self.fixture.name).glob('*/*.wav')))
        self.assertFalse(list(Path(self.fixture.name).glob('*/*.partial')))

    def test_stop_before_submit_does_not_create_job(self):
        event = threading.Event(); event.set()
        with self.assertRaises(m.StopWaiting): self.client.generate(self.song, self.fixture.name, event)
        self.assertFalse(self.calls)

    def test_stop_after_submit_saves_task_without_claiming_backend_cancel(self):
        event = threading.Event()
        def progress(message):
            if message.startswith('Queued'): event.set()
        with self.assertRaises(m.StopWaiting):
            self.client.generate(self.song, self.fixture.name, event, progress)
        job = json.loads(next(Path(self.fixture.name).glob('*/job.json')).read_text())
        self.assertEqual(job['status'], 'detached'); self.assertEqual(job['task_id'], 'fixture-task')
        self.assertEqual(len(self.calls), 2)

    def test_timeout_keeps_id_and_no_resubmission(self):
        self.status = 0
        with self.assertRaises(m.MusicError): self.client.generate(self.song, self.fixture.name, timeout=0)
        self.assertEqual(sum(path == '/release_task' for path, *_ in self.calls), 1)
        self.assertEqual(json.loads(next(Path(self.fixture.name).glob('*/job.json')).read_text())['task_id'], 'fixture-task')

    def test_request_validation_and_instrumental(self):
        for kwargs in ({'duration': True}, {'takes': 8}, {'bpm': 10}, {'seed': -2}):
            with self.assertRaises(ValueError): m.SongRequest('x', 'y', 'z', **kwargs).payload()
        self.assertEqual(m.SongRequest('x', 'y', instrumental=True).payload()['lyrics'], '[Instrumental]')

    def test_three_original_singers_and_dual_guitars_reach_local_prompt(self):
        song = m.SongRequest('Duet test', 'Dark metal', '[Singer 1] Verse\\n[Singer 2] Chorus',
            vocal_lineup=('Justin Therapy (original baritone)', 'Original feminine alto',
                          'Jason (original character voice)'),
            vocal_notes='Alternate verses with singer labels and share final chorus',
            guitar_one='Heavy rhythm riffs on a seven-string',
            guitar_two='Independent melodic lead harmony and solo',
            other_instruments='Bass, drums and piano')
        prompt = song.payload()['prompt']
        self.assertIn('feminine alto', prompt)
        self.assertIn('Jason', prompt)
        self.assertIn('Guitarist 1', prompt)
        self.assertIn('Guitarist 2', prompt)
        self.assertIn('Bass, drums and piano', prompt)
        self.assertIn('Dark metal', prompt)
        # A named text role is not proof that actual voice identity is replicated.
        self.assertIn('invented rather than cloned', prompt)

    def test_lineup_roles_are_validated_without_voice_cloning(self):
        for singers in (('Unknown real vocalist',),
                        ('Original feminine alto',) * 4):
            with self.assertRaises(ValueError):
                m.SongRequest('Test', 'Rock', 'lyrics', vocal_lineup=singers).payload()
        with self.assertRaises(ValueError):
            m.SongRequest('Test', 'Rock', 'lyrics', guitar_one='a' * 401).payload()
        duet = m.SongRequest('Test', 'Rock', 'lyrics',
            vocal_lineup=('Original feminine alto', 'Original feminine alto')).payload()
        self.assertIn('Singer 2', duet['prompt'])
        default = m.SongRequest('Test', 'Rock', 'lyrics').payload()
        self.assertEqual(default['prompt'], 'Rock')

    def test_no_remote_endpoint_credentials_or_proxy(self):
        for url in ('http://example.com:8001', 'http://user:pass@127.0.0.1:8001',
                    'http://127.0.0.1:8001/path', 'http://localhost:8001', 'file:///tmp'):
            with self.assertRaises(ValueError): m.LocalMusicClient(url)


if __name__ == '__main__': unittest.main()
