"""Local ACE-Step client. No model downloads, cloud fallback or Suno API use.

Protocol: https://github.com/ace-step/ACE-Step-1.5/blob/main/docs/en/API.md
This adapter implements text-to-song only. V6 comparison features are tracked
separately; no untested creative-slider mapping or voice cloning is implied.
"""
from dataclasses import asdict, dataclass
import ipaddress
import json
import os
import secrets
import shutil
from pathlib import Path
import tempfile
import threading
import mimetypes
import time
from urllib.parse import urlsplit, urljoin
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler
import wave

try:
    from .arrangement import arrangement_text
except ImportError:
    from arrangement import arrangement_text


class MusicError(RuntimeError):
    pass


class StopWaiting(MusicError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise MusicError('The local music service redirected the request; refusing it.')


@dataclass(frozen=True)
class SongRequest:
    title: str
    style: str
    lyrics: str = ''
    instrumental: bool = False
    duration: int = 180
    takes: int = 2
    bpm: int = 0
    seed: int = -1
    vocal_lineup: tuple = ()
    vocal_notes: str = ''
    guitar_one: str = ''
    guitar_two: str = ''
    other_instruments: str = ''
    vocal_mode: str = 'ai_lead'
    source_audio: str = ''

    def payload(self):
        for name, limit in (('title', 200), ('style', 8000), ('lyrics', 20000)):
            value = getattr(self, name)
            if not isinstance(value, str) or len(value) > limit:
                raise ValueError(f'{name} must be text with at most {limit} characters')
        if not self.title.strip() or not self.style.strip():
            raise ValueError('Enter a title and musical style.')
        if type(self.instrumental) is not bool:
            raise ValueError('Instrumental must be true or false.')
        if not self.instrumental and not self.lyrics.strip():
            raise ValueError('Enter lyrics or select instrumental.')
        for name, low, high in (('duration', 10, 600), ('takes', 1, 2), ('seed', -1, 2147483647)):
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f'{name} must be an integer between {low} and {high}')
        if type(self.bpm) is not int or (self.bpm != 0 and not 30 <= self.bpm <= 300):
            raise ValueError('Tempo must be 0 (automatic) or 30–300 BPM.')
        band = arrangement_text(self.vocal_lineup, self.vocal_notes,
                                self.guitar_one, self.guitar_two, self.other_instruments)
        prompt = self.style.strip() + ('\n\n' + band if band else '')
        if len(prompt) > 12000:
            raise ValueError('Combined arrangement is too long.')
        if self.vocal_mode not in ('ai_lead', 'with_my_vocal', 'backing_for_my_vocal'):
            raise ValueError('Choose AI singers, guest vocals, or backing for your recording.')
        if self.instrumental and self.vocal_mode == 'with_my_vocal':
            raise ValueError('Guest singers and instrumental-only cannot be selected together.')
        if self.vocal_mode != 'ai_lead':
            check_audio_input(self.source_audio)
            prompt += ('\nPreserve the human source singer and arrange additional original co-vocalists around the recorded lead where possible.'
                       if self.vocal_mode == 'with_my_vocal' else
                       '\nCreate complementary musical backing around the supplied source vocal.')
        elif self.source_audio:
            raise ValueError('Source audio is only used in a recording-assisted mode.')
        result = {
            'prompt': prompt,
            'lyrics': '[Instrumental]' if self.instrumental else self.lyrics,
            'audio_duration': self.duration, 'batch_size': self.takes,
            'seed': self.seed, 'use_random_seed': self.seed == -1,
            'audio_format': 'wav',
            'task_type': {'ai_lead': 'text2music', 'with_my_vocal': 'cover',
                          'backing_for_my_vocal': 'complete'}[self.vocal_mode],
            'use_format': False, 'use_cot_caption': False,
        }
        if self.vocal_mode == 'with_my_vocal':
            result['audio_cover_strength'] = 0.8
        if self.bpm:
            result['bpm'] = self.bpm
        return result


AUDIO_MAX = 64 * 1024 * 1024
AUDIO_TYPES = {'.wav': 'audio/wav', '.mp3': 'audio/mpeg', '.flac': 'audio/flac'}


def check_audio_input(path):
    if not isinstance(path, str) or not path.strip():
        raise ValueError('Select a recording of your vocals first.')
    src = Path(path).expanduser()
    if src.suffix.lower() not in AUDIO_TYPES or not src.is_file() or src.is_symlink():
        raise ValueError('Choose a regular WAV, MP3 or FLAC recording.')
    size = src.stat().st_size
    if not 0 < size <= AUDIO_MAX:
        raise ValueError('The recording must be between 1 byte and 64 MiB.')
    return src


def write_manifest(path, data):
    fd, name = tempfile.mkstemp(prefix='.job-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, indent=2, ensure_ascii=False)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


class LocalMusicClient:
    def __init__(self, base_url='http://127.0.0.1:8001', api_key=None):
        parsed = urlsplit(base_url)
        try:
            loopback = ipaddress.ip_address(parsed.hostname).is_loopback
            port = parsed.port
        except (ValueError, TypeError):
            loopback = False
            port = None
        if (not loopback or parsed.scheme != 'http' or parsed.username or parsed.password
                or parsed.path not in ('', '/') or parsed.query or parsed.fragment or not port):
            raise ValueError('Use a numeric loopback service URL, such as http://127.0.0.1:8001.')
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key or ''
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def _request(self, path, payload=None):
        headers = {}
        if self.api_key:
            headers['Authorization'] = 'Bearer ' + self.api_key
        body = None
        if payload is not None:
            body = json.dumps(payload).encode()
            headers['Content-Type'] = 'application/json'
        return Request(self.base_url + path, data=body, headers=headers)

    def _json(self, path, payload=None):
        try:
            with self.opener.open(self._request(path, payload), timeout=10) as response:
                raw = response.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise MusicError('Oversized response from local music service.')
            result = json.loads(raw)
        except MusicError:
            raise
        except Exception as error:
            # Do not include requests, tokens or service bodies in UI error logs.
            raise MusicError('Local music service unavailable or returned invalid data. '
                             'Check that ACE-Step is running on the configured port.') from error
        if not isinstance(result, dict) or result.get('code') != 200 or result.get('error'):
            raise MusicError('Local music service rejected the request. Check its local log.')
        return result.get('data')

    def health(self):
        health = self._json('/health')
        if not isinstance(health, dict) or health.get('status') != 'ok':
            raise MusicError('Local music service is not ready.')
        return health

    def audio_path(self, url):
        parsed = urlsplit(urljoin(self.base_url + '/', url))
        base = urlsplit(self.base_url)
        if ((parsed.scheme, parsed.netloc) != (base.scheme, base.netloc)
                or parsed.path != '/v1/audio' or not parsed.query or parsed.fragment):
            raise MusicError('Music service returned an unexpected audio URL.')
        return parsed.path + '?' + parsed.query

    def download(self, url, target, stop):
        path = self.audio_path(url)
        # The target lives in a newly created private per-job folder.
        partial = target.with_suffix('.partial')
        try:
            with self.opener.open(self._request(path), timeout=10) as response, \
                    partial.open('xb') as output:
                os.chmod(partial, 0o600)
                total = 0
                while True:
                    if stop.is_set():
                        raise StopWaiting('Stopped waiting; the backend task may continue.')
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > 256 * 1024 * 1024:
                        raise MusicError('Audio output exceeded the per-take size limit.')
                    output.write(chunk)
            with wave.open(str(partial), 'rb') as audio:
                if not audio.getnframes() or not audio.getframerate():
                    raise MusicError('The music service returned empty audio.')
                expected = audio.getnframes() * audio.getnchannels() * audio.getsampwidth()
                actual = 0
                while True:
                    data = audio.readframes(65536)
                    if not data:
                        break
                    actual += len(data)
                if actual != expected:
                    raise MusicError('The music service returned truncated audio.')
            os.replace(partial, target)
        except (wave.Error, EOFError) as error:
            raise MusicError('The music service did not return a valid PCM WAV take.') from error
        finally:
            partial.unlink(missing_ok=True)

    def generate(self, request, output_root, stop=None, progress=None,
                 timeout=1800, poll_interval=2):
        stop = stop if stop is not None else threading.Event()
        progress = progress or (lambda message: None)
        payload = request.payload()
        if stop.is_set():
            raise StopWaiting('No task was submitted.')
        self.health()
        if stop.is_set():
            raise StopWaiting('No task was submitted.')
        root = Path(output_root)
        root.mkdir(parents=True, exist_ok=True)
        folder = Path(tempfile.mkdtemp(prefix='song-', dir=root))
        manifest = folder / 'job.json'
        job = {'schema': 1, 'request': asdict(request), 'payload': payload,
               'backend': 'ACE-Step', 'endpoint': self.base_url,
               'status': 'submitting', 'task_id': None, 'files': []}
        write_manifest(manifest, job)
        progress('Submitting song to the local engine…')
        try:
            # Never auto-retry submission: a lost response may still have queued a job.
            submitted = self._json('/release_task', payload)
            task_id = submitted.get('task_id') if isinstance(submitted, dict) else None
            if not isinstance(task_id, str) or not task_id or len(task_id) > 200:
                raise MusicError('The service did not return a valid task ID; do not blindly resubmit.')
            job.update(task_id=task_id, status='queued_or_running')
            write_manifest(manifest, job)
            progress('Queued or generating. The engine does not report a completion percentage.')
            deadline = time.monotonic() + timeout
            while True:
                if stop.is_set():
                    raise StopWaiting('Stopped waiting; the backend may continue. Task ID saved in job.json.')
                if time.monotonic() >= deadline:
                    raise MusicError('Waiting timed out; the backend may continue. Task ID saved in job.json.')
                rows = self._json('/query_result', {'task_id_list': [task_id]})
                if not isinstance(rows, list):
                    raise MusicError('Invalid task-status response.')
                row = next((r for r in rows if isinstance(r, dict) and r.get('task_id') == task_id), None)
                if row is None or type(row.get('status')) is not int or row['status'] not in (0, 1, 2):
                    raise MusicError('The service returned an unknown task state.')
                if row['status'] == 2:
                    raise MusicError('The music task failed. Check the local engine log.')
                if row['status'] == 1:
                    outputs = row.get('result')
                    if isinstance(outputs, str):
                        try:
                            outputs = json.loads(outputs)
                        except ValueError as error:
                            raise MusicError('Invalid audio result.') from error
                    if (not isinstance(outputs, list) or not outputs or len(outputs) > request.takes
                            or any(not isinstance(x, dict) or x.get('status') != 1
                                   or not isinstance(x.get('file'), str) for x in outputs)):
                        raise MusicError('The task completed without valid audio results.')
                    for number, result in enumerate(outputs, 1):
                        target = folder / f'take-{number}.wav'
                        progress(f'Saving take {number} of {len(outputs)}…')
                        self.download(result['file'], target, stop)
                        job['files'].append(target.name)
                        write_manifest(manifest, job)
                    job['status'] = 'completed'
                    job['result_metadata'] = [{key: item.get(key) for key in
                        ('seed_value', 'lm_model', 'dit_model', 'metas')} for item in outputs]
                    write_manifest(manifest, job)
                    progress('Audio saved. Play and evaluate the takes before judging quality.')
                    return folder
                stop.wait(poll_interval)
        except Exception as error:
            job['status'] = 'detached' if isinstance(error, StopWaiting) else 'error'
            job['error'] = str(error) if isinstance(error, MusicError) else type(error).__name__
            write_manifest(manifest, job)
            raise
