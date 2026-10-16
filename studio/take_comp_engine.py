"""Non-destructive Spider Studio sample-aligned take comping.

An edit decision list chooses which *existing* recorded WAV supplies each
timeline interval. Every input remains unchanged. Equal-length/rate/depth/
channel PCM WAVs are required. Small crossfades smooth take switch points.
Export is create-new-only and streamed in 4096-frame blocks.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from array import array
import math
import os
import sys
import tempfile
import wave

try:
    from .audio_capture_engine import CaptureError
except ImportError:
    from audio_capture_engine import CaptureError

MAX_TAKES = 16
MAX_SEGMENTS = 128
MAX_FRAMES = 48000 * 300
CHUNK = 4096

@dataclass(frozen=True)
class CompSegment:
    start: int
    end: int
    take: int

def _read_pcm(raw, width):
    if width == 2:
        values = array("h")
        values.frombytes(raw)
        if sys.byteorder != "little":
            values.byteswap()
        return list(values)
    if width == 3:
        return [int.from_bytes(raw[i:i+3],"little",signed=True)
                for i in range(0,len(raw),3)]
    raise CaptureError("Take comping requires 16- or 24-bit signed PCM WAV")

def _write_pcm(values, width):
    maximum = (1 << (width*8-1)) - 1
    minimum = -maximum - 1
    clipped=(min(max(int(round(v)),minimum),maximum) for v in values)
    if width == 2:
        out=array("h",clipped)
        if sys.byteorder!="little":
            out.byteswap()
        return out.tobytes()
    return b"".join(int(v).to_bytes(3,"little",signed=True) for v in clipped)

def _describe(sources):
    if (not isinstance(sources,(list,tuple))
            or not 2 <= len(sources) <= MAX_TAKES):
        raise CaptureError("Select between two and sixteen different recorded WAV takes")
    opened=[]
    seen=set()
    try:
        for path in sources:
            p=Path(path)
            if p.is_symlink() or not p.is_file() or p.suffix.lower()!=".wav":
                raise CaptureError("Only regular local WAV take files can be comped")
            real=p.resolve()
            if real in seen:
                raise CaptureError("Every take must be a different WAV file")
            seen.add(real)
            reader=wave.open(str(real),"rb")
            opened.append(reader)
            rate,channels,width,frames=(
                reader.getframerate(),reader.getnchannels(),
                reader.getsampwidth(),reader.getnframes())
            if (reader.getcomptype()!="NONE" or rate not in (44100,48000)
                    or channels not in (1,2) or width not in (2,3)
                    or not 1 <= frames <= MAX_FRAMES):
                raise CaptureError("Take must be 16/24-bit mono/stereo PCM, 44.1/48 kHz, at most 5 minutes")
            if p.stat().st_size < 44 + frames*channels*width:
                raise CaptureError("Source take has incomplete PCM frames")
            if len(opened)>1 and (rate,channels,width,frames)!=format_info:
                raise CaptureError("All takes must have identical sample rate, channels, bit depth and duration")
            format_info=(rate,channels,width,frames)
        return opened,format_info
    except BaseException:
        for f in opened:
            f.close()
        raise

def _segments(parts,take_count,total_frames,fade):
    if (not isinstance(parts,(list,tuple))
            or not 1<=len(parts)<=MAX_SEGMENTS):
        raise CaptureError("Comp editing requires 1 to 128 arranged segments")
    result=[]
    previous=0
    for item in parts:
        if isinstance(item,CompSegment):
            seg=item
        elif (isinstance(item,(tuple,list)) and len(item)==3):
            seg=CompSegment(*item)
        else:
            raise CaptureError("Comp segment must be start, end, take index")
        if (type(seg.start) is not int or type(seg.end) is not int
            or type(seg.take) is not int or
            seg.start != previous or not seg.start < seg.end <= total_frames
            or not 0 <= seg.take < take_count):
            raise CaptureError("Comp segments must cover timeline in order without gaps/overlaps")
        result.append(seg)
        previous=seg.end
    if previous!=total_frames:
        raise CaptureError("Comp must cover the entire take timeline")
    if type(fade) is not int or not 0<=fade<=2400:
        raise CaptureError("Crossfade must be 0 to 2400 frames")
    for before,after in zip(result,result[1:]):
        if (before.take!=after.take and fade and
                (fade*2>before.end-before.start or fade*2>after.end-after.start)):
            raise CaptureError("Crossfade is longer than one of the chosen segments")
    return result

def comp_takes(sources, segments, destination, *, crossfade_ms=8, stop=None):
    """Create a newly named, time-aligned comp; do not touch original WAVs."""
    target=Path(destination)
    if target.suffix.lower()!=".wav" or target.is_symlink() or target.exists():
        raise CaptureError("Choose a new .wav export filename; original recordings are protected")
    if not target.parent.is_dir() or target.parent.is_symlink():
        raise CaptureError("Comp output parent must be an existing real directory")
    readers,info=_describe(sources)
    tmp=None
    try:
        rate,channels,width,total=info
        if (type(crossfade_ms) is not int or not 0<=crossfade_ms<=50):
            raise CaptureError("Crossfade duration must be 0 to 50 milliseconds")
        fade=round(crossfade_ms*rate/1000)
        plan=_segments(segments,len(readers),total,fade)
        if stop is not None and stop.is_set():
            raise CaptureError("Comp export was cancelled")
        boundaries=[(seg.end,seg.take,following.take)
                    for seg,following in zip(plan,plan[1:])
                    if seg.take!=following.take and fade>0]
        fd,tmp=tempfile.mkstemp(prefix=".spider-comp-",suffix=".wav.part",
                                 dir=str(target.parent))
        os.fchmod(fd,0o600)
        with os.fdopen(fd,"wb") as stream:
            with wave.open(stream,"wb") as out:
                out.setnchannels(channels)
                out.setsampwidth(width)
                out.setframerate(rate)
                idx=0
                for base in range(0,total,CHUNK):
                    if stop is not None and stop.is_set():
                        raise CaptureError("Comp export was cancelled")
                    end=min(base+CHUNK,total)
                    # One section can span multiple segments; render per subrange.
                    while idx<len(plan)-1 and base>=plan[idx].end:
                        idx+=1
                    cursor=base
                    while cursor<end:
                        while idx<len(plan)-1 and cursor>=plan[idx].end:
                            idx+=1
                        segment=plan[idx]
                        finish=min(end,segment.end)
                        reader=readers[segment.take]
                        reader.setpos(cursor)
                        data=reader.readframes(finish-cursor)
                        if len(data)!=(finish-cursor)*channels*width:
                            raise CaptureError("A take was truncated while comping")
                        values=_read_pcm(data,width)
                        # Crossfade is centered at each edit point; blend the
                        # two takes at identical timeline coordinates.
                        for boundary,earlier,later in boundaries:
                            left=boundary-fade
                            right=boundary+fade
                            overlap_lo=max(cursor,left)
                            overlap_hi=min(finish,right)
                            if overlap_lo>=overlap_hi:
                                continue
                            alternate=later if segment.take==earlier else earlier
                            other=readers[alternate]
                            other.setpos(overlap_lo)
                            raw_other=other.readframes(overlap_hi-overlap_lo)
                            if len(raw_other)!=(overlap_hi-overlap_lo)*channels*width:
                                raise CaptureError("Crossfade source was truncated")
                            other_values=_read_pcm(raw_other,width)
                            for frame in range(overlap_lo,overlap_hi):
                                alpha=(frame-left)/(2*fade)
                                # At early side the chosen segment is A;
                                # at late side the chosen segment is B.
                                mine=1-alpha if segment.take==earlier else alpha
                                other_weight=1-mine
                                for ch in range(channels):
                                    a=(frame-cursor)*channels+ch
                                    b=(frame-overlap_lo)*channels+ch
                                    values[a]=values[a]*mine+other_values[b]*other_weight
                        out.writeframesraw(_write_pcm(values,width))
                        cursor=finish
                out.writeframes(b"")
            stream.flush()
            os.fsync(stream.fileno())
        if target.exists() or target.is_symlink():
            raise FileExistsError("Another recording with that name was created")
        os.link(tmp,target,follow_symlinks=False)
        return {"path":str(target),"frames":total,"rate":rate,
                "channels":channels,"width":width,
                "segments":len(plan),"crossfade_ms":crossfade_ms}
    finally:
        for reader in readers:
            reader.close()
        if tmp is not None:
            Path(tmp).unlink(missing_ok=True)
