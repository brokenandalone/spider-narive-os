"""Opt-in, HASH-PINNED offline voiceprint provider loader.

A verifier may decide who can issue privileged commands. The owner must
explicitly enable this feature and pin the SHA-256 of one audited local
Python provider file. No arbitrary import names, sys.path manipulation,
cloud fallback, shell commands or model downloads.
This checks code provenance, NOT biometric accuracy/liveness.
"""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import re
import stat
import sys
import types

from segment_speaker_gate import SegmentSpeakerGate

MAX_PROVIDER_BYTES=1_000_000
SHA256=re.compile(r"^[0-9a-f]{64}$")
MODULE_NAME="_webbie_pinned_voice_verifier"


def _pinned_source(folder, wanted):
    if not isinstance(wanted,str) or not SHA256.fullmatch(wanted):
        return None
    folder=Path(folder)
    candidate=folder/"speaker_voice_provider.py"
    try:
        if folder.is_symlink() or candidate.is_symlink():
            return None
        directory=folder.stat()
        source=candidate.stat()
        if (not stat.S_ISDIR(directory.st_mode) or
                directory.st_mode&0o022 or
                not stat.S_ISREG(source.st_mode) or
                source.st_uid not in (os.getuid(),0) or
                source.st_mode&0o022 or not 1<=source.st_size<=MAX_PROVIDER_BYTES):
            return None
        blob=candidate.read_bytes()
        after=candidate.stat()
        if (after.st_ino!=source.st_ino or after.st_size!=source.st_size
                or after.st_mtime_ns!=source.st_mtime_ns or
                hashlib.sha256(blob).hexdigest()!=wanted):
            return None
        return blob
    except (OSError,ValueError):
        return None


def speaker_gate_from_config(config=None, *, voice_root=None, clock=None,
                             importer=None):
    raw=(config or {}).get("speaker_verification")
    if not isinstance(raw,dict) or raw.get("enabled") is not True:
        return SegmentSpeakerGate(clock=clock)
    folder=Path(voice_root) if voice_root else Path(__file__).resolve().parents[1]/"voice"
    blob=_pinned_source(folder,raw.get("provider_sha256"))
    if blob is None:
        return SegmentSpeakerGate(clock=clock)
    try:
        if importer is not None:
            # Isolated offline test hook. Live invocation must not supply it.
            module=importer("speaker_voice_provider")
        else:
            module=types.ModuleType(MODULE_NAME)
            module.__file__=str(folder/"speaker_voice_provider.py")
            # Compile the exact approved bytes. Do not pick up stale Python
            # bytecode, a module cached in sys.modules, or a different path.
            compiled=compile(blob,str(folder/"speaker_voice_provider.py"),"exec")
            exec(compiled,module.__dict__)
        function=getattr(module,"verify_audio_segment",None)
        if callable(function):
            return SegmentSpeakerGate(function,clock=clock)
    except Exception:
        # A failed provider never silently falls back to an untrusted user.
        pass
    return SegmentSpeakerGate(clock=clock)
