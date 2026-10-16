"""Validated offline per-channel effects for Spider Studio session mixing.

These are real FFmpeg DSP effects on original independent WAVs during mixing.
Per-channel filters deliberately omit the final limiter; only the stereo bus
is limited after all tracks are summed. No arbitrary filter text accepted.
"""
from __future__ import annotations

try:
    from .take_effects import TakeEffects,effects_graph
    from .multitrack import SessionError
except ImportError:
    from take_effects import TakeEffects,effects_graph
    from multitrack import SessionError

FIELDS=("bass_db","mids_db","treble_db","compression","room")
DEFAULTS={"bass_db":0,"mids_db":0,"treble_db":0,"compression":False,"room":0}

def normalize_track_effects(settings=None):
    """Return copy of a safe track FX state, for mixing and private presets."""
    if settings is None:
        return dict(DEFAULTS)
    if not isinstance(settings,dict) or not set(settings).issubset(FIELDS):
        raise SessionError("Unknown per-track EQ / compressor / room effect")
    values={**DEFAULTS,**settings}
    try:
        TakeEffects(**values).validate()
    except (ValueError,TypeError) as exc:
        raise SessionError("Track effects must be bounded EQ, compression and room settings") from exc
    return values

def track_effects_filter(settings):
    """Return only verified filter fragments, with no per-track final limiter."""
    params=normalize_track_effects(settings)
    return effects_graph(TakeEffects(**params),final_limiter=False)
