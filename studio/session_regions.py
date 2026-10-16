"""Non-destructive, sample-aligned multi-region WAV timeline edit decisions.

A region selects an interval from ONE verified source track and positions
it on the song timeline. It may overlap another region (layered playback).
Nothing edits, saves, or renames source WAVs. No free-form FFmpeg syntax.
"""
from __future__ import annotations
try:
    from .session_clip_edit import normalize_clip_edit,clip_ffmpeg_filters
    from .multitrack import SessionError
except ImportError:
    from session_clip_edit import normalize_clip_edit,clip_ffmpeg_filters
    from multitrack import SessionError

MAX_REGIONS=12
MAX_SESSION_MS=7_200_000
REGION_FIELDS=("start_ms","end_ms","at_ms","fade_in_ms","fade_out_ms")

def normalize_regions(track,regions=None):
    """Return canonical list and latest audible endpoint in seconds.

    An absent/empty region list means use the original single-clip editor.
    A nonempty list is an independent alternative to that editor, and all
    start/end times are checked against the verified WAV's sample count.
    """
    if regions is None or regions==[]:
        return [],0.0
    if not isinstance(regions,list) or not 1<=len(regions)<=MAX_REGIONS:
        raise SessionError("Choose 1 to 12 independent timeline regions.")
    normalized=[]
    latest=0.
    for region in regions:
        if not isinstance(region,dict) or set(region)!=set(REGION_FIELDS):
            raise SessionError("Every region needs exactly source start/end, timeline position and fades.")
        if any(type(region[key]) is not int for key in REGION_FIELDS):
            raise SessionError("Timeline regions must use whole milliseconds.")
        if not 0<=region["at_ms"]<=MAX_SESSION_MS:
            raise SessionError("Timeline position must be between zero and two hours.")
        if not 0<=region["start_ms"]<region["end_ms"]<=MAX_SESSION_MS:
            raise SessionError("A source region needs increasing bounded start and end times.")
        # Reuse the actual one-region source-frame validator.
        _,source=normalize_clip_edit(track,{
            "trim_start_ms":region["start_ms"],
            "trim_end_ms":region["end_ms"],
            "fade_in_ms":region["fade_in_ms"],
            "fade_out_ms":region["fade_out_ms"]},delay_ms=0)
        endpoint=region["at_ms"]/1000+source.duration_seconds
        if endpoint>MAX_SESSION_MS/1000:
            raise SessionError("A timeline region cannot finish after two hours.")
        latest=max(latest,endpoint)
        normalized.append(dict(region))
    return normalized,latest

def timeline_filter_segments(index,track,regions):
    """Create fixed, FFmpeg-escaped-by-construction graph for one source WAV.

    Output is (filter declarations, final composite pad). A single FFmpeg
    input is split into bounded branches rather than reopening source WAVs.
    All source samples are trimmed BEFORE resampling. Timestamps restart
    at each region's 0 and its own fade applies before mixing.
    """
    edits,_=normalize_regions(track,regions)
    if not edits:
        raise SessionError("Multi-region renderer requires a nonempty edit list.")
    prefixes=[]
    count=len(edits)
    if count==1:
        branches=[f"[{index}:a:0]"]
    else:
        branches=[f"[r{index}_{part}]" for part in range(count)]
        prefixes.append(
            f"[{index}:a:0]asplit={count}"+ "".join(branches))
    output_pads=[]
    for part,item in enumerate(edits):
        _,source=normalize_clip_edit(track,{
            "trim_start_ms":item["start_ms"],
            "trim_end_ms":item["end_ms"],
            "fade_in_ms":item["fade_in_ms"],
            "fade_out_ms":item["fade_out_ms"]})
        chain=clip_ffmpeg_filters(source)
        # Zero delay never needs adelay; nonzero delay is explicit, and is
        # applied at 48kHz AFTER sample-exact source trims and fade offsets.
        delay=f",adelay={item['at_ms']}:all=1" if item["at_ms"] else ""
        pad=f"[piece{index}_{part}]"
        prefixes.append(
            f"{branches[part]}{chain},aresample=48000,"
            "aformat=sample_fmts=fltp:channel_layouts=stereo"
            f"{delay}{pad}")
        output_pads.append(pad)
    if count==1:
        return prefixes,output_pads[0]
    mixed=f"[regions{index}]"
    prefixes.append(
        "".join(output_pads)+
        f"amix=inputs={count}:duration=longest:dropout_transition=0:"
        f"normalize=0{mixed}")
    return prefixes,mixed
