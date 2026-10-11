"""Offline, non-destructive mix of actual, distinct recorded Spider Studio WAV stems."""
import json
import math
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

ROLES = ('backing', 'lead_vocal', 'guest_vocal', 'rhythm_guitar',
         'lead_guitar', 'bass', 'drums', 'keys')
DEFAULT_OUTPUT = Path.home() / 'Documents/Spider Studio/Music/Band Mixes'


def validate_tracks(tracks, gains=None):
    """Check separate source files, WAV headers, gains, roles before making output."""
    if not isinstance(tracks, dict) or not 2 <= len(tracks) <= len(ROLES):
        raise MixError('Choose two to eight independent WAV tracks.')
    if gains is None:
        gains = {}
    if not isinstance(gains, dict) or any(role not in tracks for role in gains):
        raise MixError('Levels must refer to selected audio tracks.')
    selected, levels, identities = {}, {}, set()
    for role in ROLES:
        if role not in tracks:
            continue
        audio = tracks[role]
        if not isinstance(audio, (str, Path)) or not str(audio).strip():
            raise MixError('Select a WAV for ' + role.replace('_', ' '))
        path = valid_wav(audio, role.replace('_', ' '))
        identity = (path.stat().st_dev, path.stat().st_ino)
        if identity in identities:
            raise MixError('Each band role needs a different source WAV.')
        identities.add(identity)
        try:
            with wave.open(str(path), 'rb') as stream:
                if (stream.getnframes() <= 0 or stream.getframerate() <= 0
                        or stream.getnchannels() not in (1, 2)):
                    raise MixError('Invalid WAV for ' + role.replace('_', ' '))
        except (wave.Error, EOFError, OSError) as exc:
            raise MixError('Invalid WAV for ' + role.replace('_', ' ')) from exc
        gain = gains.get(role, 1.0)
        if (isinstance(gain, bool) or not isinstance(gain, (float, int))
                or not math.isfinite(gain) or not 0 <= gain <= 2):
            raise MixError('Track gain must be a number from 0 to 2.')
        selected[role], levels[role] = path, float(gain)
    if set(tracks) != set(selected):
        raise MixError('Unknown band track role.')
    return selected, levels


def validate_mix_options(tracks, pans=None, mutes=None):
    """Validate per-track stereo balance and mute independently of file paths."""
    if not isinstance(tracks, dict) or not tracks:
        raise MixError('Choose band WAV tracks before setting mixer controls.')
    pans = {} if pans is None else pans
    mutes = {} if mutes is None else mutes
    if not isinstance(pans, dict) or not isinstance(mutes, dict):
        raise MixError('Pan and mute settings must be mapped to track roles.')
    if set(pans) - set(tracks) or set(mutes) - set(tracks):
        raise MixError('Mixer controls refer to an unknown track.')
    balances, silenced = {}, {}
    for role in tracks:
        pan = pans.get(role, 0.0)
        mute = mutes.get(role, False)
        if (isinstance(pan, bool) or not isinstance(pan, (int, float))
                or not math.isfinite(pan) or not -1.0 <= pan <= 1.0):
            raise MixError('Stereo pan must be a finite number from -1 to 1.')
        if not isinstance(mute, bool):
            raise MixError('Mute must be enabled or disabled for each track.')
        balances[role], silenced[role] = float(pan), mute
    if all(silenced.values()):
        raise MixError('Unmute at least one band track before mixing.')
    return balances, silenced


def band_mix_command(ffmpeg, tracks, gains, output, *, pans=None, mutes=None):
    """Non-shell FFmpeg command: unique stem pads, limiter, no overwrites."""
    selected, levels = validate_tracks(tracks, gains)
    balances, silenced = validate_mix_options(selected, pans, mutes)
    target = Path(output).expanduser()
    if target.is_symlink() or target.exists() or target.suffix.lower() != '.wav':
        raise MixError('Output must be a new WAV file.')
    command = [str(ffmpeg), '-hide_banner', '-loglevel', 'error', '-nostdin', '-n']
    filters, pads = [], []
    for i, (role, path) in enumerate(selected.items()):
        command.extend(('-i', str(path)))
        effective_gain = 0.0 if silenced[role] else levels[role]
        # Native FFmpeg stereo balance works with both mono and stereo WAVs.
        filters.append(f'[{i}:a:0]aformat=channel_layouts=stereo,'
                       f'stereotools=balance_out={balances[role]:.3f},'
                       f'volume={effective_gain:.3f}[stem{i}]')
        pads.append(f'[stem{i}]')
    filters.append(''.join(pads) + f'amix=inputs={len(pads)}:duration=longest:'
                   'dropout_transition=0:normalize=0,alimiter=limit=0.95[out]')
    command.extend(('-filter_complex', ';'.join(filters), '-map', '[out]',
                    '-ac', '2', '-ar', '48000', '-c:a', 'pcm_s24le', str(target)))
    return command


def mix_band_tracks(tracks, *, gains=None, pans=None, mutes=None, output_root=None, timeout=1200, stop=None):
    """Render stereo 48 kHz WAV; keep originals, log and receipt private."""
    selected, levels = validate_tracks(tracks, gains)
    balances, silenced = validate_mix_options(selected, pans, mutes)
    if isinstance(timeout, bool) or not isinstance(timeout, (float, int)) or not 1 <= timeout <= 7200:
        raise MixError('Invalid mix timeout.')
    stop = stop if stop is not None else threading.Event()
    if stop.is_set():
        raise MixError('Band mix cancelled before processing.')
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise MixError('FFmpeg is required for local band mixing.')
    parent = Path(output_root).expanduser() if output_root else DEFAULT_OUTPUT
    if parent.is_symlink():
        raise MixError('Output folder cannot be a symlink.')
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(parent, 0o700)
    folder = Path(tempfile.mkdtemp(prefix='band-', dir=parent))
    os.chmod(folder, 0o700)
    output = folder / 'band-mix.wav'
    command = band_mix_command(ffmpeg, selected, levels, output, pans=balances, mutes=silenced)
    log = folder / 'band-mix.log'
    try:
        with log.open('xb') as stream:
            os.chmod(log, 0o600)
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                       stdout=stream, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                if stop.is_set() or time.monotonic() >= deadline:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                    raise MixError('Band mix stopped or timed out. Originals preserved.')
                stop.wait(0.15)
        if process.returncode != 0 or output.is_symlink() or not output.is_file():
            raise MixError('Band mix failed. Check the private band-mix.log.')
        try:
            with wave.open(str(output), 'rb') as stream:
                if (stream.getnframes() <= 0 or stream.getframerate() != 48000
                        or stream.getnchannels() != 2):
                    raise MixError('Expected a 48 kHz stereo WAV output.')
        except (wave.Error, EOFError, OSError) as exc:
            raise MixError('Invalid final band WAV.') from exc
        os.chmod(output, 0o600)
        receipt = {'schema': 1, 'created_at_unix': int(time.time()),
                   'render': output.name, 'source_tracks_preserved': True,
                   'independent_tracks': [
                       {'role': role, 'source': str(path), 'gain': levels[role],
                        'pan': balances[role], 'muted': silenced[role]}
                       for role, path in selected.items()]}
        manifest = folder / 'band-mix.json'
        with manifest.open('x', encoding='utf-8') as stream:
            os.chmod(manifest, 0o600)
            json.dump(receipt, stream, indent=2)
        return output
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise MixError('Could not finish band mix. Original tracks preserved.') from exc
