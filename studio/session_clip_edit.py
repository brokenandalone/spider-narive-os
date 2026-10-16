"""Sample-bound, non-destructive clip edit decisions for verified Studio WAVs.

A clip chooses an input source region and duration using whole millisecond
controls, but the returned start/end boundaries are integer sample frames.
All edits are held in the mix preset/receipt, never written into source WAVs.
"""
from __future__ import annotations
from dataclasses import dataclass
try:
    from .multitrack import SessionError
except ImportError:
    from multitrack import SessionError

FIELDS=("trim_start_ms","trim_end_ms","fade_in_ms","fade_out_ms")
DEFAULTS={"trim_start_ms":0,"trim_end_ms":0,
          "fade_in_ms":0,"fade_out_ms":0}
MAX_FADE_MS=30000
MAX_RENDER_MS=2*3600*1000

@dataclass(frozen=True)
class ClipRegion:
    start_frame: int
    end_frame: int
    source_frames: int
    sample_rate: int
    fade_in_ms: int
    fade_out_ms: int
    duration_ms: float

    @property
    def duration_seconds(self):
        return (self.end_frame-self.start_frame)/self.sample_rate


def _frame(rate,ms):
    return (rate*ms+500)//1000


def normalize_clip_edit(track,settings=None,*,delay_ms=0):
    """Validate a track's clip edit against its original verified WAV frames.

    trim_end_ms=0 means full source end, supporting old presets. End may be
    rounded to the last frame; values beyond the actual file are rejected.
    """
    if not isinstance(track,dict):
        raise SessionError("Verify the source WAV before editing it.")
    rate,frames=track.get("sample_rate"),track.get("frames")
    if (type(rate) is not int or not 8000<=rate<=192000
            or type(frames) is not int or not 1<=frames<=rate*7200):
        raise SessionError("A valid verified WAV sample count is required.")
    if settings is None:
        options=dict(DEFAULTS)
    elif isinstance(settings,dict) and set(settings).issubset(FIELDS):
        options={**DEFAULTS,**settings}
    else:
        raise SessionError("Unrecognized audio clip editing control.")
    if (type(delay_ms) is not int or not 0<=delay_ms<=20000):
        raise SessionError("Clip placement offset must be 0..20 seconds.")
    for key,value in options.items():
        limit=MAX_FADE_MS if key.startswith("fade_") else MAX_RENDER_MS
        if type(value) is not int or not 0<=value<=limit:
            raise SessionError("Clip trim and fades must be bounded whole milliseconds.")
    start=_frame(rate,options["trim_start_ms"])
    requested_end=options["trim_end_ms"]
    end=frames if requested_end==0 else _frame(rate,requested_end)
    if start>=frames or end>frames or end<=start:
        raise SessionError("Clip trim boundaries must contain actual source audio.")
    duration=(end-start)/rate
    # Fade lengths never extend beyond the portion of source actually included.
    if (options["fade_in_ms"]+options["fade_out_ms"]) > duration*1000+0.0001:
        raise SessionError("Fade-in and fade-out overlap beyond the retained clip.")
    if delay_ms/1000+duration>7200:
        raise SessionError("Placed clip exceeds the two-hour session limit.")
    return options,ClipRegion(
        start,end,frames,rate,
        options["fade_in_ms"],options["fade_out_ms"],duration*1000)


def clip_ffmpeg_filters(region):
    """Return fixed FFmpeg fragments, using exact source frames for trim."""
    if not isinstance(region,ClipRegion):
        raise SessionError("Cannot render an unverified clip.")
    filters=[
        f"atrim=start_sample={region.start_frame}:end_sample={region.end_frame}",
        "asetpts=PTS-STARTPTS",
    ]
    # Fade lengths are tied to the *trimmed* clip's time zero. The final
    # stereo bus is limited by the existing master pipeline.
    if region.fade_in_ms:
        filters.append(
            f"afade=t=in:st=0:d={region.fade_in_ms/1000:.3f}")
    if region.fade_out_ms:
        start=region.duration_seconds-region.fade_out_ms/1000
        filters.append(
            f"afade=t=out:st={start:.6f}:d={region.fade_out_ms/1000:.3f}")
    return ",".join(filters)
