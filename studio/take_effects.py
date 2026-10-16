"""Non-destructive Spider Studio offline take effects, using installed FFmpeg.

Whitelisted, parametrically bounded EQ/compression/short-delay reverb/
limiting. No shell, VST loading, network, user-defined filter strings,
device input, or writes to source WAVs. Runs only after an explicit action.
"""
from __future__ import annotations
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import wave
import math

try:
    from .audio_capture_engine import CaptureError
except ImportError:
    from audio_capture_engine import CaptureError

@dataclass(frozen=True)
class TakeEffects:
    bass_db: int=0
    mids_db: int=0
    treble_db: int=0
    compression: bool=False
    room: int=0

    def validate(self):
        if any(type(x) is not int or not -12<=x<=12
               for x in (self.bass_db,self.mids_db,self.treble_db)):
            raise CaptureError("EQ adjustment must be a whole dB in -12..12")
        if type(self.compression) is not bool:
            raise CaptureError("Compression selection must be a boolean")
        if type(self.room) is not int or not 0<=self.room<=40:
            raise CaptureError("Room intensity must be 0 to 40 percent")
        return self

def effects_graph(settings, *, final_limiter=True):
    s=settings.validate()
    pipeline=[]
    if s.bass_db:
        pipeline.append(f"equalizer=f=105:width_type=o:width=1.0:g={s.bass_db}")
    if s.mids_db:
        pipeline.append(f"equalizer=f=1050:width_type=o:width=1.0:g={s.mids_db}")
    if s.treble_db:
        pipeline.append(f"equalizer=f=6300:width_type=o:width=1.0:g={s.treble_db}")
    if s.compression:
        pipeline.append("acompressor=threshold=0.25:ratio=3:attack=15:release=150:makeup=1")
    if s.room:
        # Echo is a subtle short reflection, not a convolution room impulse.
        delay=68
        decay=round(s.room/250,3)
        pipeline.append(f"aecho=in_gain=0.8:out_gain=0.8:delays={delay}:decays={decay:.3f}")
    if type(final_limiter) is not bool:
        raise CaptureError("Final limiter toggle must be true or false")
    if final_limiter:
        pipeline.append("alimiter=limit=0.95:level=0")
    return ",".join(pipeline)

def apply_take_effects(source,destination,settings=TakeEffects(),*,
                       binary=None,stop=None,timeout=300):
    if type(timeout) not in (int,float) or not 1<=timeout<=1800:
        raise CaptureError("Invalid effect processing timeout")
    graph=effects_graph(settings)
    src=Path(source)
    dest=Path(destination)
    if src.is_symlink() or src.suffix.lower()!=".wav" or not src.is_file():
        raise CaptureError("Choose one recorded regular WAV track")
    if dest.exists() or dest.is_symlink() or dest.suffix.lower()!=".wav":
        raise CaptureError("Effect output must be a NEW separate WAV file")
    if not dest.parent.is_dir() or dest.parent.is_symlink():
        raise CaptureError("Effect destination directory does not exist")
    if src.resolve()==dest.resolve():
        raise CaptureError("Cannot overwrite the source recording")
    try:
        with wave.open(str(src),"rb") as wav:
            if (wav.getcomptype()!="NONE" or wav.getnchannels() not in (1,2)
                    or wav.getsampwidth() not in (2,3)
                    or wav.getframerate() not in (44100,48000)
                    or not 1<=wav.getnframes()<=wav.getframerate()*300):
                raise CaptureError("Effects require 16/24-bit mono or stereo PCM 44.1/48 kHz, max 5 min")
            rate=wav.getframerate()
            channels=wav.getnchannels()
            frames=wav.getnframes()
    except (OSError,wave.Error,EOFError,ZeroDivisionError) as exc:
        raise CaptureError("Cannot inspect recorded track for effects") from exc
    exe=binary or shutil.which("ffmpeg")
    if not exe:
        raise CaptureError("FFmpeg is required for native offline studio effects")
    if stop is not None and stop.is_set():
        raise CaptureError("Effects cancelled before processing")
    tmp=None
    try:
        fd,tmp=tempfile.mkstemp(prefix=".spider-fx-",suffix=".wav.part",
                                dir=str(dest.parent))
        os.close(fd)
        os.chmod(tmp,0o600)
        # FFmpeg output probe requires the explicit WAV muxer because temp
        # extension is intentionally .part.
        args=[str(exe),"-hide_banner","-loglevel","error",
              "-nostdin","-y","-i",str(src),"-vn","-af",graph,
              "-ac",str(channels),"-ar",str(rate),
              "-c:a","pcm_s24le","-f","wav",str(tmp)]
        proc=subprocess.Popen(args,stdin=subprocess.DEVNULL,
                              stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        try:
            deadline=time.monotonic()+timeout
            while proc.poll() is None:
                if stop is not None and stop.is_set() or time.monotonic()>deadline:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=5)
                    raise CaptureError("Effects processing cancelled or timed out")
                time.sleep(.08)
            _,err=proc.communicate(timeout=2)
            if proc.returncode:
                raise CaptureError("FFmpeg effect renderer failed: "+err.decode("utf-8","replace")[-180:])
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
        with wave.open(str(tmp),"rb") as wav:
            if (wav.getnchannels()!=channels or wav.getsampwidth()!=3
                    or wav.getframerate()!=rate
                    or wav.getnframes()<frames
                    or wav.getnframes()>frames+round(rate*.3)):
                raise CaptureError("Effects renderer returned invalid or truncated audio")
        if dest.exists() or dest.is_symlink():
            raise FileExistsError("An effects output already exists")
        os.link(tmp,dest,follow_symlinks=False)
        return {"path":str(dest),"role":"processed_recording",
                "channels":channels,"sample_rate":rate,
                "sample_width_bits":24,"duration_seconds":frames/rate,
                "effects":settings}
    finally:
        if tmp:
            Path(tmp).unlink(missing_ok=True)
