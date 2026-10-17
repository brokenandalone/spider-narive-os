"""Owner-private, non-destructive release exports from actual finished mix WAVs.

Three fixed FFmpeg profiles. No shell, no automatic cloud uploads and no
untrusted user-defined FFmpeg arguments. Originals and old exports are intact.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import wave

if __package__:
    from .song_mix import MixError, valid_wav
else:
    from song_mix import MixError, valid_wav

DEFAULT_ROOT = Path.home() / 'Documents/Spider Studio/Music/Release Exports'
PROFILES = {
    'studio_wav': {
        'label': 'Studio master | 48 kHz, stereo, 24-bit PCM WAV',
        'file': 'studio-48k-24bit.wav', 'suffix': '.wav',
        'args': ('-ar', '48000', '-ac', '2', '-c:a', 'pcm_s24le'),
    },
    'cd_wav': {
        'label': 'CD-compatible | 44.1 kHz, stereo, 16-bit PCM WAV',
        'file': 'cd-44k-16bit.wav', 'suffix': '.wav',
        'args': ('-af', 'aresample=dither_method=triangular',
                 '-ar', '44100', '-ac', '2', '-c:a', 'pcm_s16le'),
    },
    'mp3_320': {
        'label': 'High-quality MP3 | stereo, 320 kbps CBR',
        'file': 'preview-320k.mp3', 'suffix': '.mp3',
        'args': ('-ar', '44100', '-ac', '2', '-c:a', 'libmp3lame', '-b:a', '320k'),
    },
}
ALL_PROFILES = tuple(PROFILES)


def validate_source(path):
    source = valid_wav(path, 'finished stereo mix')
    try:
        with wave.open(str(source), 'rb') as audio:
            if (audio.getnframes() <= 0 or audio.getframerate() <= 0
                    or audio.getnchannels() not in (1, 2)
                    or audio.getcomptype() != 'NONE'
                    or audio.getsampwidth() not in (1, 2, 3, 4)):
                raise MixError('Select an uncompressed mono or stereo PCM WAV.')
    except (OSError, EOFError, wave.Error, ZeroDivisionError) as error:
        raise MixError('The selected WAV is invalid or unsupported.') from error
    return source


def choose_profiles(names):
    if (not isinstance(names, (tuple, list)) or not 1 <= len(names) <= len(PROFILES)
            or len(set(names)) != len(names) or any(name not in PROFILES for name in names)):
        raise MixError('Choose one or more distinct supported release formats.')
    return tuple(names)


def encode_command(ffmpeg, source, profile, destination):
    """Deterministic non-shell FFmpeg command, no existing output overwritten."""
    if profile not in PROFILES:
        raise MixError('Unknown release format.')
    source = validate_source(source)
    target = Path(destination).expanduser()
    settings = PROFILES[profile]
    if (target.is_symlink() or target.exists() or target.suffix.lower() != settings['suffix']
            or target.resolve() == source):
        raise MixError('Release output must be a new file with the correct extension.')
    return [
        str(ffmpeg), '-hide_banner', '-loglevel', 'error', '-nostdin', '-n',
        '-i', str(source), '-map', '0:a:0', '-vn', '-sn', '-dn', '-map_metadata', '-1',
        *settings['args'], str(target),
    ]


def _hash_file(path, stop):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while True:
            if stop.is_set():
                raise MixError('Export cancelled. Original mix is unchanged.')
            block = stream.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _validate_output(path, profile):
    if path.is_symlink() or not path.is_file() or path.stat().st_size < 64:
        raise MixError('The release encoder did not produce a valid output file.')
    if profile not in ('studio_wav', 'cd_wav'):
        return
    try:
        with wave.open(str(path), 'rb') as reader:
            expected = 48000 if profile == 'studio_wav' else 44100
            bits = 3 if profile == 'studio_wav' else 2
            if (reader.getnframes() <= 0 or reader.getnchannels() != 2
                    or reader.getframerate() != expected or reader.getsampwidth() != bits):
                raise MixError('Export WAV does not match the selected format.')
    except (wave.Error, EOFError, OSError) as error:
        raise MixError('Export WAV is damaged or unsupported.') from error


def export_release(source, profiles=('studio_wav',), *, output_root=None,
                   stop=None, timeout=1200):
    """Write a fresh, private release bundle with log and receipt.

    The stop flag interrupts hashing and running encoders. Partial outputs are
    removed after failure; previous release folders are not altered.
    """
    source = validate_source(source)
    selected = choose_profiles(profiles)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 1 <= timeout <= 7200:
        raise MixError('Invalid release export timeout.')
    stop = stop if stop is not None else threading.Event()
    if stop.is_set():
        raise MixError('Export cancelled before processing.')
    executable = shutil.which('ffmpeg')
    if not executable:
        raise MixError('FFmpeg must be installed to create release exports.')
    original_stat = source.stat()
    source_hash = _hash_file(source, stop)
    parent = Path(output_root).expanduser() if output_root else DEFAULT_ROOT
    if parent.is_symlink():
        raise MixError('Release export library cannot be a symlink.')
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(parent, 0o700)
    folder = Path(tempfile.mkdtemp(prefix='release-', dir=parent))
    os.chmod(folder, 0o700)
    receipts = []
    try:
        for profile in selected:
            if stop.is_set():
                raise MixError('Release export was stopped. Source mix is preserved.')
            name = PROFILES[profile]['file']
            target = folder / name
            command = encode_command(executable, source, profile, target)
            log = folder / (profile + '.log')
            with log.open('xb') as output:
                os.chmod(log, 0o600)
                proc = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                        stdout=output, stderr=subprocess.STDOUT)
                deadline = time.monotonic() + timeout
                while proc.poll() is None:
                    if stop.is_set() or time.monotonic() >= deadline:
                        proc.terminate()
                        try:
                            proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                            proc.wait(timeout=5)
                        raise MixError('Release export stopped or timed out. Original preserved.')
                    stop.wait(.15)
            if proc.returncode:
                raise MixError('FFmpeg export failed. Inspect the private ' + log.name + '.')
            _validate_output(target, profile)
            os.chmod(target, 0o600)
            receipts.append({
                'profile': profile, 'label': PROFILES[profile]['label'],
                'filename': name, 'file_bytes': target.stat().st_size,
            })
        newest = source.stat()
        if ((newest.st_dev, newest.st_ino, newest.st_size, newest.st_mtime_ns)
                != (original_stat.st_dev, original_stat.st_ino,
                    original_stat.st_size, original_stat.st_mtime_ns)):
            raise MixError('Source audio changed during export. Recheck the mix.')
        receipt = {
            'schema': 1, 'created_at_unix': int(time.time()),
            'original_mix': str(source), 'original_sha256': source_hash,
            'source_preserved': True, 'exports': receipts,
        }
        manifest = folder / 'release.json'
        with manifest.open('x', encoding='utf-8') as output:
            os.chmod(manifest, 0o600)
            json.dump(receipt, output, indent=2)
        return folder
    except (OSError, subprocess.TimeoutExpired) as error:
        raise MixError('Could not complete release export. Original remains unchanged.') from error
    except MixError:
        raise
    finally:
        # No half-valid output is left masquerading as a completed release.
        if not (folder / 'release.json').is_file():
            for file in folder.glob('*'):
                if file.is_file() and not file.is_symlink():
                    file.unlink(missing_ok=True)
            try:
                folder.rmdir()
            except OSError:
                pass


def list_releases(*, output_root=None, limit=50):
    parent = Path(output_root).expanduser() if output_root else DEFAULT_ROOT
    if parent.is_symlink():
        raise MixError('Release library cannot be a symlink.')
    if not parent.is_dir():
        return []
    result = []
    for folder in parent.glob('release-*'):
        if folder.is_symlink() or not folder.is_dir():
            continue
        receipt = folder / 'release.json'
        try:
            if (receipt.is_symlink() or not receipt.is_file()
                    or not 0 < receipt.stat().st_size < 64 * 1024):
                continue
            data = json.loads(receipt.read_text(encoding='utf-8'))
            if data.get('schema') != 1 or not isinstance(data.get('exports'), list):
                continue
            exports = []
            for item in data['exports']:
                if not isinstance(item, dict) or item.get('profile') not in PROFILES:
                    raise ValueError('Unknown export profile')
                filename = item.get('filename')
                if filename != PROFILES[item['profile']]['file']:
                    raise ValueError('Unexpected release filename')
                audio = folder / filename
                if audio.is_symlink() or not audio.is_file() or audio.stat().st_size < 64:
                    raise ValueError('Missing release audio')
                exports.append({'profile': item['profile'], 'file': str(audio)})
            if not exports:
                continue
            result.append({
                'folder': str(folder), 'created_at_unix': data.get('created_at_unix', 0),
                'source': data.get('original_mix', ''), 'exports': exports,
                'sort_time': folder.stat().st_mtime_ns,
            })
        except (OSError, ValueError, UnicodeError):
            continue
    return sorted(result, key=lambda item: item['sort_time'], reverse=True)[:max(1, min(int(limit), 100))]
