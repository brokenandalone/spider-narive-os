"""Spider Studio opt-in PCM capture backend for separate owner-recorded takes.

No audio devices are opened on import or app startup. A user-selected device
is opened only inside capture_take(), requested explicitly by the Record
control. Data travels through a bounded queue; PortAudio callback never
writes files or touches UI. The existing sound server, Nova and Webbie are not
reconfigured. Uses optional, separately installed python-sounddevice.
"""
from __future__ import annotations

from array import array
import math
import os
from pathlib import Path
import queue
import re
import sys
import tempfile
import threading
import time
import wave

RATES=(44100,48000)
BLOCK_FRAMES=1024
QUEUE_LIMIT=96
MAX_SECONDS=300
MAX_CAPTURE_BYTES=MAX_SECONDS*48000*2*3
ROLES=("lead_vocal","backing_vocal","rhythm_guitar","lead_guitar",
       "bass","drums","piano_keys","other_instrument")
_SAFE_LABEL=re.compile(r"[^A-Za-z0-9_-]+")
class CaptureError(ValueError):
    pass

def _backend(provided=None):
    if provided is not None:
        return provided
    try:
        import sounddevice
    except ImportError as exc:
        raise CaptureError("Optional python-sounddevice/PortAudio backend is not installed") from exc
    return sounddevice

def available_inputs(backend=None):
    """Owner-triggered device discovery: list only devices with capture inputs."""
    api=_backend(backend)
    try:
        devices=api.query_devices()
        return [(i,str(d.get("name","Input"))[:110],int(d["max_input_channels"]))
                for i,d in enumerate(devices)
                if int(d.get("max_input_channels",0))>0]
    except (OSError,RuntimeError,KeyError,TypeError,ValueError) as exc:
        raise CaptureError("Unable to list available audio recording devices") from exc

def _validate(target,device,channels,rate,max_seconds,role,bit_depth):
    dest=Path(target)
    if dest.suffix.lower()!=".wav" or dest.exists() or dest.is_symlink():
        raise CaptureError("Choose a NEW .wav recording path; existing takes are protected")
    if not dest.parent.is_dir() or dest.parent.is_symlink():
        raise CaptureError("Recording directory is unavailable or a symlink")
    if type(device) is not int or not 0<=device<=1024:
        raise CaptureError("Select a valid input device from the recording console")
    if type(channels) is not int or channels not in (1,2):
        raise CaptureError("Audio recording must be mono or stereo")
    if type(rate) is not int or rate not in RATES:
        raise CaptureError("Only 44.1/48 kHz recording is supported")
    if type(bit_depth) is not int or bit_depth not in (16,24):
        raise CaptureError("Only native 16-bit or 24-bit PCM input capture is supported")
    if type(max_seconds) not in (int,float) or isinstance(max_seconds,bool) or not 0<max_seconds<=MAX_SECONDS:
        raise CaptureError("Recording time limit must be between 0 and 300 seconds")
    if role not in ROLES:
        raise CaptureError("Choose a supported instrument/vocal recording role")
    return dest

def _levels(pcm,bit_depth):
    if bit_depth==16:
        samples=array("h")
        samples.frombytes(pcm)
        if sys.byteorder!="little":
            samples.byteswap()
        scale=32768.0
    elif bit_depth==24:
        samples=(int.from_bytes(pcm[i:i+3],"little",signed=True)
                 for i in range(0,len(pcm),3))
        samples=list(samples)
        scale=8388608.0
    else:
        raise CaptureError("Unsupported capture meter format")
    if not samples:
        return -120.0, -120.0
    peak=max(abs(v) for v in samples)/scale
    power=sum(v*v for v in samples)/(len(samples)*scale**2)
    peak_db=max(-120.0,20*math.log10(peak)) if peak else -120.0
    rms_db=max(-120.0,10*math.log10(power)) if power else -120.0
    return round(peak_db,1),round(rms_db,1)

def capture_take(destination,*,device,role,channels=1,rate=48000,max_seconds=180,
                 bit_depth=16,stop=None,on_level=None,backend=None):
    """Record one raw input stream into an atomic private 16-bit PCM WAV.

    The loop drains callback events after a requested Stop. If PortAudio ever
    drops an input block, or the queue overflows, the recording is rejected,
    not silently represented as an uninterrupted professional take.
    """
    dest=_validate(destination,device,channels,rate,max_seconds,role,bit_depth)
    stop=stop if stop is not None else threading.Event()
    if stop.is_set():
        raise CaptureError("Recording cancelled before opening the microphone")
    api=_backend(backend)
    raw_queue=queue.Queue(maxsize=QUEUE_LIMIT)
    fault=[]
    frames_written=0
    tmp=None
    sample_width=bit_depth//8
    limit_frames=min(int(rate*max_seconds),MAX_CAPTURE_BYTES//(channels*sample_width))
    if limit_frames<1:
        raise CaptureError("Recording time limit too short")
    def callback(indata,frames,timing,status):
        if stop.is_set() or fault:
            return
        if status:
            fault.append("Audio input overrun/underrun: capture must be retaken")
            stop.set()
            return
        if type(frames) is not int or frames<=0 or frames>8192:
            fault.append("Invalid PortAudio frame count")
            stop.set()
            return
        try:
            block=bytes(indata)
            if len(block)!=frames*channels*sample_width:
                raise ValueError("Capture data size does not match input frames")
            raw_queue.put_nowait((block,frames))
        except (queue.Full,ValueError,BufferError):
            fault.append("Recording buffer overflow; retake rather than save damaged audio")
            stop.set()
    try:
        fd,tmp=tempfile.mkstemp(prefix=".spider-take-",suffix=".wav.part",
                                dir=str(dest.parent))
        os.fchmod(fd,0o600)
        with os.fdopen(fd,"wb") as output:
            with wave.open(output,"wb") as wav:
                wav.setnchannels(channels)
                wav.setsampwidth(sample_width)
                wav.setframerate(rate)
                try:
                    with api.RawInputStream(
                        samplerate=rate,blocksize=BLOCK_FRAMES,device=device,
                        channels=channels,dtype="int24" if bit_depth==24 else "int16",
                        callback=callback):
                        start=time.monotonic()
                        updated=start
                        while True:
                            if time.monotonic()-start>=max_seconds:
                                stop.set()
                            if stop.is_set() and raw_queue.empty():
                                break
                            try:
                                raw,count=raw_queue.get(timeout=.08)
                            except queue.Empty:
                                continue
                            remaining=limit_frames-frames_written
                            if remaining<=0:
                                stop.set()
                                continue
                            wanted=min(count,remaining)
                            wav.writeframesraw(raw[:wanted*channels*sample_width])
                            frames_written+=wanted
                            now=time.monotonic()
                            if on_level is not None and now-updated>=.12:
                                peak,rms=_levels(raw[:wanted*channels*sample_width],
                                                 bit_depth)
                                on_level(peak,rms,frames_written/rate)
                                updated=now
                            if frames_written>=limit_frames:
                                stop.set()
                except (OSError,RuntimeError,ValueError) as exc:
                    raise CaptureError("Audio input could not be opened or captured: "+str(exc)[:160]) from exc
                wav.writeframes(b"")
            output.flush()
            os.fsync(output.fileno())
        if fault:
            raise CaptureError(fault[0])
        if frames_written<=0:
            raise CaptureError("No microphone/instrument samples were recorded")
        if dest.exists() or dest.is_symlink():
            raise FileExistsError("A recording with this name was created during capture")
        # Link is an atomic create-new-only operation on the same filesystem.
        os.link(tmp,dest,follow_symlinks=False)
        os.chmod(dest,0o600)
        return {
            "path":str(dest),"role":role,"channels":channels,"sample_rate":rate,
            "frames":frames_written,"duration_seconds":round(frames_written/rate,3),
            "sample_width_bits":bit_depth,
        }
    finally:
        if tmp is not None:
            Path(tmp).unlink(missing_ok=True)

def new_take_filename(folder,role,*,clock=None):
    if role not in ROLES:
        raise CaptureError("Unsupported take role")
    base=Path(folder)
    if not base.is_dir() or base.is_symlink():
        raise CaptureError("Take directory does not exist or is a symlink")
    moment=int(time.time_ns() if clock is None else clock)
    if moment<0:
        raise CaptureError("Invalid take timestamp")
    filename=f"Spider-{role}-{moment}.wav"
    target=base/filename
    if target.exists() or target.is_symlink():
        raise FileExistsError("Take identifier collision; choose a new filename")
    return target
