"""Synchronised, atomic instrument-stem export for the Spider virtual band.

Each score part renders independently to its selected, locally licensed
SoundFont. Dry stems include muted/soloed parts and preserve note timing.
All stems start at score time zero and are padded to the longest rendered tail.
Nothing is written inside the final destination until all parts succeed.
"""
from __future__ import annotations
from array import array
from contextlib import ExitStack
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import wave

try:
    from .studio_score_mix import _isolated_part, _audio_layout
    from .soundfont_render import render_soundfont,validate_soundfont
except ImportError:
    from studio_score_mix import _isolated_part, _audio_layout
    from soundfont_render import render_soundfont,validate_soundfont

MAX_STEMS = 15
MAX_EXPORT_BYTES = 1_200_000_000
BLOCK = 8192

def _safe_name(value):
    safe=re.sub(r"[^a-zA-Z0-9_-]+","-",str(value))[:45].strip("-")
    return safe or "Instrument"

def _pcm24(raw):
    """Scale signed 16-bit samples into exact signed 24-bit containers."""
    values=array("h")
    values.frombytes(raw)
    if sys.byteorder!="little":
        values.byteswap()
    out=bytearray(3*len(values))
    for i,value in enumerate(values):
        out[i*3:(i+1)*3]=(value*256).to_bytes(3,"little",signed=True)
    return bytes(out)

def render_score_stems(performance,default_bank,destination,part_banks=None,
                       rate=48000,bit_depth=24,part_renderer=None):
    """Create one new directory containing n fully aligned stereo WAV files.

    The target folder must not exist, so an export cannot replace older stems
    or a user's unrelated session. Staging is a sibling directory and is
    atomically renamed only when all WAVs and the manifest have succeeded.
    """
    p=performance.validated()
    if type(rate) is not int or rate not in (44100,48000):
        raise ValueError("Stem output supports 44.1/48 kHz")
    if type(bit_depth) is not int or bit_depth not in (16,24):
        raise ValueError("Stem output supports 16/24-bit PCM")
    if not 1<=len(p.parts)<=MAX_STEMS or p.duration_seconds>300:
        raise ValueError("Stem export part/duration limit exceeded")
    target=Path(destination)
    if target.exists() or target.is_symlink():
        raise FileExistsError("Stem folder already exists; choose a new destination")
    if not target.parent.is_dir():
        raise FileNotFoundError("Stem parent folder does not exist")
    banks=dict(part_banks or {})
    if any(type(i) is not int or not 0<=i<len(p.parts) for i in banks):
        raise ValueError("Unknown instrument bank assignment")
    samples=[validate_soundfont(banks.get(i,default_bank)).resolve()
             for i in range(len(p.parts))]
    if any(target.resolve()==sample for sample in samples):
        raise ValueError("Cannot export stems over an instrument bank")
    if p.origin is not None and target.resolve()==p.origin.resolve():
        raise ValueError("Cannot export stems over imported source")
    execute=part_renderer or render_soundfont
    with tempfile.TemporaryDirectory(prefix=".spider-stems-",dir=target.parent) as temp:
        stage=Path(temp)
        rendered=[]
        for i,part in enumerate(p.parts):
            single=_isolated_part(p,i)
            name=f"{i+1:02d}-{_safe_name(part.name)}.wav"
            source=stage / f"_raw_{i:02d}.wav"
            if single is not None:
                execute(single,samples[i],source,rate=rate)
                _audio_layout(source,rate)
            rendered.append((name,source if single is not None else None,part))
        durations=[_audio_layout(src,rate) for _,src,_ in rendered if src is not None]
        if not durations:
            raise ValueError("No playable score notes for stem export")
        frames=max(durations)
        expected=frames*2*(bit_depth//8)*len(rendered)
        if expected>MAX_EXPORT_BYTES:
            raise ValueError("Stem exports exceed the 1.2 GB safety limit")
        manifest={
            "format":"spider-audio-stems","version":1,"title":p.title,
            "rate":rate,"channels":2,"bit_depth":bit_depth,"frames":frames,
            "parts":[]
        }
        for i,(name,src,part) in enumerate(rendered):
            final=stage/name
            with ExitStack() as stack:
                reader=stack.enter_context(wave.open(str(src),"rb")) if src else None
                writer=stack.enter_context(wave.open(str(final),"wb"))
                writer.setnchannels(2)
                writer.setsampwidth(bit_depth//8)
                writer.setframerate(rate)
                remaining=frames
                while remaining:
                    amount=min(BLOCK,remaining)
                    raw=reader.readframes(amount) if reader is not None else b""
                    real_frames=len(raw)//4
                    raw+=bytes((amount-real_frames)*4)
                    writer.writeframesraw(_pcm24(raw) if bit_depth==24 else raw)
                    remaining-=amount
                writer.writeframes(b"")
            manifest["parts"].append({
                "index":i,"instrument":part.name,"program":part.program,
                "channel":part.channel,"filename":name,
                "sample_bank":samples[i].name,
                "note_count":sum(1 for n in p.notes if n.part==i)})
        (stage/"stems.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n","utf-8")
        for _,src,_ in rendered:
            if src is not None:
                src.unlink()
        if target.exists():
            raise FileExistsError("Destination was created during stem rendering")
        os.rename(stage,target)
    return target
