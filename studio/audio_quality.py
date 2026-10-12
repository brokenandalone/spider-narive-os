"""Read-only WAV sample-quality preflight for actual Spider Studio recordings.

Samples only the first and last 8 seconds of each input. Measures sample
peak/RMS, possible clipped samples and DC bias; NOT LUFS, true peak, beat sync,
mix quality, trained singer identity or forensic stem independence.
"""
import math
from pathlib import Path
import struct
import wave

if __package__:
    from .song_mix import MixError, valid_wav
    from .production_board import ROLES
else:
    from song_mix import MixError, valid_wav
    from production_board import ROLES


class QualityError(ValueError):
    pass


MAX_ASSETS = len(ROLES)
SECONDS_PER_EDGE = 8
CHUNK_FRAMES = 16384
CLIP_THRESHOLD = 0.9999


def _samples(block, width):
    if width == 1:
        for item in block:
            yield (item - 128) / 128.0
    elif width == 2:
        for (item,) in struct.iter_unpack('<h', block):
            yield item / 32768.0
    elif width == 3:
        for position in range(0, len(block), 3):
            yield int.from_bytes(block[position:position + 3], 'little', signed=True) / 8388608.0
    elif width == 4:
        for (item,) in struct.iter_unpack('<i', block):
            yield item / 2147483648.0
    else:
        raise QualityError('Only 8, 16, 24 and 32-bit PCM WAV is supported.')


def inspect_wav(source, *, stop=None):
    """Inspect the two edges of a file without changing or copying it.

    Sample peak warnings do not prove analog/digital clipping or quality.
    """
    try:
        path = valid_wav(source, 'quality preflight')
        if stop is not None and stop.is_set():
            raise QualityError('Audio preflight cancelled.')
        with wave.open(str(path), 'rb') as reader:
            if (reader.getcomptype() != 'NONE' or reader.getnchannels() not in (1, 2)
                    or reader.getsampwidth() not in (1, 2, 3, 4)
                    or reader.getframerate() <= 0 or reader.getnframes() <= 0):
                raise QualityError('Select a nonempty mono or stereo uncompressed PCM WAV.')
            rate = reader.getframerate()
            total_frames = reader.getnframes()
            channels = reader.getnchannels()
            width = reader.getsampwidth()
            edge = min(total_frames, rate * SECONDS_PER_EDGE)
            regions = [(0, edge)]
            if total_frames > edge:
                regions.append((max(edge, total_frames - edge), min(edge, total_frames - edge)))
            peak = 0.0
            squared = 0.0
            total = 0.0
            clipped = 0
            count = 0
            for start, frames in regions:
                reader.setpos(start)
                remaining = frames
                while remaining:
                    if stop is not None and stop.is_set():
                        raise QualityError('Audio preflight cancelled.')
                    to_read = min(CHUNK_FRAMES, remaining)
                    chunk = reader.readframes(to_read)
                    unit = width * channels
                    if not chunk or len(chunk) % unit:
                        raise QualityError('Damaged PCM WAV frames.')
                    got = len(chunk) // unit
                    for value in _samples(chunk, width):
                        abs_value = abs(value)
                        peak = max(peak, abs_value)
                        squared += value * value
                        total += value
                        count += 1
                        if abs_value >= CLIP_THRESHOLD:
                            clipped += 1
                    remaining -= got
            if not count:
                raise QualityError('Unable to read the PCM sample window.')
            rms = math.sqrt(squared / count)
            peak_dbfs = 20 * math.log10(peak) if peak else None
            rms_dbfs = 20 * math.log10(rms) if rms else None
            dc_mean = total / count
            warnings = []
            if peak == 0:
                warnings.append('Sampled audio regions contain digital silence.')
            elif rms_dbfs is not None and rms_dbfs < -45:
                warnings.append('Sampled average level is very low; review gain and noise.')
            if clipped:
                warnings.append('Near-full-scale PCM samples detected; listen for clipping.')
            if abs(dc_mean) >= .025:
                warnings.append('Possible DC bias in sampled PCM audio; check recording chain.')
            if channels == 1:
                warnings.append('Mono file; mixer/export may convert it to stereo.')
            return {
                'sample_rate': rate,
                'channels': channels,
                'sample_width_bits': width * 8,
                'duration_seconds': round(total_frames / rate, 3),
                'sampled_seconds': round(count / (rate * channels), 3),
                'sample_peak_dbfs': round(peak_dbfs, 2) if peak_dbfs is not None else None,
                'rms_dbfs': round(rms_dbfs, 2) if rms_dbfs is not None else None,
                'near_full_scale_samples': clipped,
                'dc_offset_ratio': round(dc_mean, 6),
                'warnings': warnings,
            }
    except (wave.Error, EOFError, OSError, MixError, ZeroDivisionError) as error:
        raise QualityError('Cannot inspect this file as a regular PCM WAV.') from error


def audit_assets(assets, *, stop=None):
    """Evaluate owner-selected recordings and warn about sync/rate mismatches."""
    if not isinstance(assets, dict) or not 1 <= len(assets) <= MAX_ASSETS:
        raise QualityError('Choose one to ten audio files for quality preflight.')
    if set(assets) - set(ROLES):
        raise QualityError('Unknown role in quality preflight.')
    checked = {}
    identities = set()
    for role in ROLES:
        if role not in assets:
            continue
        try:
            path = valid_wav(assets[role], role)
        except (OSError, MixError) as error:
            raise QualityError('The ' + role + ' WAV is missing or unsafe.') from error
        identity = (path.stat().st_dev, path.stat().st_ino)
        if identity in identities:
            raise QualityError('A single WAV cannot be treated as multiple independent tracks.')
        identities.add(identity)
        checked[role] = inspect_wav(path, stop=stop)
    lengths = [info['duration_seconds'] for info in checked.values()]
    rates = {info['sample_rate'] for info in checked.values()}
    warnings = []
    if len(lengths) > 1 and max(lengths) - min(lengths) > .5:
        warnings.append('Audio durations differ by more than half a second; review track timing.')
    if len(rates) > 1:
        warnings.append('Source WAV sample rates differ; check resampling in the DAW.')
    if 'reference_mix' in checked:
        warnings.append('The whole-song reference is not proof of separate isolated stems.')
    return {'analysis': 'first_and_last_8_seconds_only',
            'tracks': checked, 'session_warnings': warnings}
