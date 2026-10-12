"""Opt-in bridge to an owner-installed OFFLINE voiceprint provider.

A provider is never shipped or downloaded by this PR. It is loaded only
when the owner explicitly enables the feature in local Webbie configuration
AND a separate audited local module is installed under Webbie voice.
The module must expose verify_audio_segment(wav_path) returning
SpeakerEvidence with a matching SHA-256 digest and fresh origin metadata.
No cloud service, web speech synthesis, LLM or face match is a fallback.
"""
from __future__ import annotations
import importlib
from pathlib import Path
import sys
from segment_speaker_gate import SegmentSpeakerGate


def speaker_gate_from_config(config=None, *, voice_root=None, clock=None,
                             importer=None):
    raw = (config or {}).get("speaker_verification")
    if not isinstance(raw,dict) or raw.get("enabled") is not True:
        return SegmentSpeakerGate(clock=clock)
    folder=Path(voice_root) if voice_root else Path(__file__).resolve().parents[1]/"voice"
    candidate=folder/"speaker_voice_provider.py"
    if not candidate.is_file() or candidate.is_symlink():
        return SegmentSpeakerGate(clock=clock)
    try:
        # No user-provided import path or shell command is ever accepted.
        # Only a separately installed, audited file at this fixed location.
        if str(folder) not in sys.path:
            sys.path.insert(0,str(folder))
        module=(importer or importlib.import_module)("speaker_voice_provider")
        verified_fn=getattr(module,"verify_audio_segment",None)
        if callable(verified_fn):
            return SegmentSpeakerGate(verified_fn,clock=clock)
    except (ImportError,AttributeError,OSError):
        pass
    return SegmentSpeakerGate(clock=clock)
