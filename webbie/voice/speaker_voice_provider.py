"""Offline, per-utterance Cory/Shayna voiceprint adapter for Webbie.

Opt-in through the existing SHA-pinned speaker_provider_loader. Reuses the
owner's installed Sherpa-ONNX TitaNet model and .npy enrollment profiles.
Never records, enrolls, creates profiles or bypasses missing enrollment.
No external service, cloud request or device permissions.
"""
from __future__ import annotations

import math
import os
from pathlib import Path
import stat
import sys
import threading
import time
import wave

from voice_trust import SpeakerEvidence
from segment_speaker_gate import recording_fingerprint

AUTHORIZED = ("cory", "shayna")
MODEL = Path("/var/lib/spider-os/webbie-brain/voice/models/nemo_en_titanet_small.onnx")
PROFILES = Path("/var/lib/spider-os/webbie-brain/voice/profiles")
VENDOR = Path(__file__).resolve().parents[1] / "vendor"
MIN_SCORE = 0.88     # provisional. Calibrate for actual mic/voices before enable.
MIN_MARGIN = 0.05    # reject ambiguous matched profiles
_EMBED_LOCK = threading.Lock()
_EXTRACTOR = None


def _trusted_file(path, maximum):
    """Avoid following profile/model symlinks or mutable world-writable code."""
    try:
        if path.is_symlink():
            return False
        meta = path.stat()
        return (stat.S_ISREG(meta.st_mode)
                and meta.st_uid in (0, os.getuid())
                and not meta.st_mode & 0o022
                and 0 < meta.st_size <= maximum)
    except (OSError, ValueError):
        return False


def _normalize(values):
    items = [float(v) for v in values]
    if not 64 <= len(items) <= 1024 or any(not math.isfinite(v) for v in items):
        raise ValueError("Invalid speaker embedding dimensions")
    norm = math.sqrt(sum(v * v for v in items))
    if not math.isfinite(norm) or norm <= 1e-10:
        raise ValueError("Invalid speaker embedding magnitude")
    return tuple(v / norm for v in items)


def _dependencies():
    # Existing owner-installed vendor wheels; do not pull or install packages.
    if str(VENDOR) not in sys.path:
        sys.path.insert(0, str(VENDOR))
    import numpy
    import sherpa_onnx
    return numpy, sherpa_onnx


def _extractor():
    global _EXTRACTOR
    with _EMBED_LOCK:
        if _EXTRACTOR is None:
            if not _trusted_file(MODEL, 150_000_000):
                raise RuntimeError("Trusted offline speaker model unavailable")
            _, sherpa = _dependencies()
            config = sherpa.SpeakerEmbeddingExtractorConfig(
                model=str(MODEL), num_threads=2, debug=False, provider="cpu")
            if not config.validate():
                raise RuntimeError("Offline speaker model invalid")
            _EXTRACTOR = sherpa.SpeakerEmbeddingExtractor(config)
        return _EXTRACTOR


def _wav_features(filename):
    with wave.open(str(filename), "rb") as audio:
        rate = audio.getframerate()
        channels = audio.getnchannels()
        width = audio.getsampwidth()
        frames = audio.getnframes()
        if (width != 2 or not 1 <= channels <= 2
                or not 8000 <= rate <= 48000
                or frames < rate // 2 or frames > rate * 25):
            raise ValueError("Unsupported voice segment")
        raw = audio.readframes(frames)
    np, _ = _dependencies()
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    samples = samples.reshape(-1, channels).mean(axis=1)
    samples = np.ascontiguousarray(samples / 32768.0)
    return samples, rate


def _embedding(filename):
    samples, rate = _wav_features(filename)
    extractor = _extractor()
    with _EMBED_LOCK:
        stream = extractor.create_stream()
        stream.accept_waveform(sample_rate=rate, waveform=samples)
        stream.input_finished()
        if not extractor.is_ready(stream):
            raise ValueError("Voice sample too short")
        return _normalize(extractor.compute(stream))


def _profiles():
    if PROFILES.is_symlink() or not PROFILES.is_dir():
        return {}
    np, _ = _dependencies()
    found = {}
    for name in AUTHORIZED:
        source = PROFILES / (name + ".npy")
        if not _trusted_file(source, 1024 * 1024):
            continue
        try:
            data = np.load(str(source), allow_pickle=False)
            if getattr(data, "ndim", None) != 1:
                continue
            found[name] = _normalize(data)
        except (OSError, ValueError, TypeError):
            continue
    return found


def _select_identity(vector, profiles):
    if not profiles:
        return None  # NEVER 'bypass' if enrollment is absent or incomplete.
    scored = sorted(
        ((sum(a * b for a, b in zip(vector, ref)), name)
         for name, ref in profiles.items() if len(ref) == len(vector)),
        reverse=True,
    )
    if not scored or scored[0][0] < MIN_SCORE:
        return None
    if len(scored) > 1 and scored[0][0] - scored[1][0] < MIN_MARGIN:
        return None
    return scored[0]


def verify_audio_segment(filename):
    """Produce tightly scoped evidence for THIS exact local recorded segment."""
    first = recording_fingerprint(filename)
    if first is None:
        return None
    try:
        profiles = _profiles()
        if not profiles:
            return None
        vector = _embedding(filename)
        selected = _select_identity(vector, profiles)
        if selected is None:
            return None
        score, name = selected
        if recording_fingerprint(filename) != first:
            return None
        return SpeakerEvidence(
            name=name, verified=True,
            source="trusted.local_speaker_verifier",
            issued_at=time.time(),
            audio_digest=first, confidence=float(score),
        )
    except (OSError, ValueError, RuntimeError, TypeError, ImportError):
        return None
