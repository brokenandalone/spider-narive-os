"""Bounded read-only waveform peaks from actual verified Studio session PCM WAVs.

Only small sample windows are read. No audio hardware or DSP service is used.
These are *sampled* amplitude thumbnails, not complete loudness analysis.
"""
from __future__ import annotations
import sys
from array import array
from pathlib import Path
import wave
try:
    from .multitrack import SessionError
except ImportError:
    from multitrack import SessionError

def waveform_peaks(path, *, columns=260, window=96):
    if (type(columns) is not int or not 16 <= columns <= 800 or
            type(window) is not int or not 4<=window<=256):
        raise SessionError("Waveform preview window is out of bounds.")
    source=Path(path)
    if source.is_symlink() or not source.is_file() or source.suffix.lower()!=".wav":
        raise SessionError("Select a regular verified recording WAV for thumbnail.")
    peaks=[]
    try:
        with wave.open(str(source),"rb") as wav:
            total=wav.getnframes()
            channels=wav.getnchannels()
            width=wav.getsampwidth()
            if (wav.getcomptype()!="NONE" or width not in (2,3)
                or channels not in (1,2) or total<=0):
                raise SessionError("Waveform supports 16/24-bit mono/stereo PCM only.")
            fullscale=float(1<<(8*width-1))
            for column in range(columns):
                pos=min(total-1,(column*total)//columns)
                count=min(window,total-pos)
                wav.setpos(pos)
                raw=wav.readframes(count)
                if len(raw)!=count*channels*width:
                    raise SessionError("Cannot finish reading waveform preview.")
                if width==2:
                    samples=array("h")
                    samples.frombytes(raw)
                    if sys.byteorder!="little":
                        samples.byteswap()
                    highest=max(abs(x) for x in samples) if samples else 0
                else:
                    highest=max(
                        abs(int.from_bytes(raw[i:i+3],"little",signed=True))
                        for i in range(0,len(raw),3))
                peaks.append(round(min(1.,highest/fullscale),4))
        return peaks
    except (OSError,ValueError,EOFError,wave.Error,ZeroDivisionError) as exc:
        raise SessionError("Cannot inspect the selected WAV waveform.") from exc
