"""Fail-closed voice trust for the *source* Webbie resident.

Microphone transcription, familiar-face similarity, wake-word matches and
local socket messages are NOT speaker verification. Only a future PC-specific
trusted speaker adapter may supply a narrowly scoped authenticated identity.
No names or raw voice data are persisted by this policy.
"""
from __future__ import annotations
from dataclasses import dataclass
import time

TRUSTED_USERS = frozenset({"cory", "shayna"})
MAX_AUTH_AGE = 30
VOICE_CONTROLS = frozenset({"stop"})  # emergency STOP remains universally available


@dataclass(frozen=True)
class SpeakerEvidence:
    name: str
    verified: bool
    source: str
    issued_at: float
    audio_digest: str = ""  # optional backwards-compatible per-segment binding


def verify_speaker_evidence(evidence, *, now=None):
    """Strict type/provenance/expiry validation. False unless trusted adapter.

    Do not build SpeakerEvidence from LLM messages, webcam face labels or
    transcription/wake words. Caller must receive this from an authenticated
    on-PC local speaker verifier, a feature not yet supplied.
    """
    if not isinstance(evidence, SpeakerEvidence):
        return False
    stamp = float(time.time() if now is None else now)
    return (evidence.verified is True
            and isinstance(evidence.name, str)
            and evidence.name.casefold() in TRUSTED_USERS
            and evidence.source == "trusted.local_speaker_verifier"
            and type(evidence.issued_at) in (int, float)
            and 0 <= stamp - evidence.issued_at <= MAX_AUTH_AGE)


def voice_permission(*, voice, speaker_verified=False, evidence=None, now=None):
    """Typed owner's GUI path is separate; unverified voice is ignored."""
    if voice is not True:
        return True
    # A Boolean alone must never be enough to assert identity. This prevents
    # accidental true defaults and hallucinated user claims from bypassing.
    return speaker_verified is True and verify_speaker_evidence(
        evidence, now=now)


def trust_status():
    return ("Trusted voice commands require Cory or Shayna verified by a "
            "separate local speaker recognition adapter. The GitHub source "
            "does not yet provide that adapter. Speech text, wake words and "
            "camera face matches cannot unlock device control.")
