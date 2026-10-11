"""Bounded identity adapter for Webbie's *existing* local Whisper stream.

This module does not identify speakers by itself. A separate, locally
installed voiceprint engine, explicitly enrolled and validated by the owner,
must supply SpeakerEvidence for the SAME short audio segment. Never infer
speaker identity from the transcript, wake phrase, face or speaker's name.
Until such a provider exists, all normal spoken requests remain blocked.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import os
import stat

from voice_trust import SpeakerEvidence, verify_speaker_evidence

MAX_AUDIO_BYTES=2_000_000


def recording_fingerprint(path):
    """Bounded streaming digest. Never retain audio, text or embeddings."""
    file=Path(path)
    if file.is_symlink():
        return None
    try:
        before=file.stat()
        if (not stat.S_ISREG(before.st_mode)
                or before.st_uid!=os.getuid()
                or before.st_size<44 or before.st_size>MAX_AUDIO_BYTES):
            return None
        digest=hashlib.sha256()
        with file.open("rb") as stream:
            while True:
                packet=stream.read(65536)
                if not packet:
                    break
                digest.update(packet)
        after=file.stat()
        if (after.st_ino!=before.st_ino or
                after.st_size!=before.st_size or
                after.st_mtime_ns!=before.st_mtime_ns):
            return None
        return digest.hexdigest()
    except (OSError,ValueError):
        return None


class SegmentSpeakerGate:
    """Fail-closed bridge for one recorded speech chunk.

    The optional provider must accept the *audio path* and return a trusted
    SpeakerEvidence with matching audio_digest. Providers that only return
    a name, bool, face label or transcript are rejected.
    """

    def __init__(self, provider=None, *, clock=None):
        self.provider=provider
        self.clock=clock

    @property
    def configured(self):
        return callable(self.provider)

    def verify_file(self, path):
        if not self.configured:
            return None
        fingerprint=recording_fingerprint(path)
        if not fingerprint:
            return None
        try:
            raw=self.provider(str(path))
            if (not isinstance(raw,SpeakerEvidence)
                    or raw.audio_digest!=fingerprint
                    or not verify_speaker_evidence(raw,now=self.clock() if self.clock else None)):
                return None
            return raw
        except Exception:
            # Never include path, transcript or voice embedding in errors.
            return None

    def status(self):
        return ("Trusted voiceprint provider configured; actual microphone "
                "and owner identity still require a live test."
                if self.configured else
                "Trusted voiceprint provider not connected. Commands are "
                "blocked except emergency STOP. Type in The Web meanwhile.")
