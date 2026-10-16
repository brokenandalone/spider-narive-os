#!/usr/bin/env python3
"""Dependency-free activity gate for Webbie's 16k mono WAV chunks.

Not speaker verification: speaker_guard must authorize commands separately.
"""
from array import array
import math
import re
import sys
import time
import wave

def wav_has_activity(path, minimum_db=-43.0, noise_margin_db=8.0,
                     minimum_speech_seconds=0.22):
    """Reject silence, hard clipping and many steady-noise recordings."""
    try:
        with wave.open(str(path), "rb") as recording:
            if recording.getnchannels()!=1 or recording.getsampwidth()!=2:
                return False
            rate=recording.getframerate()
            if not 8000<=rate<=48000:
                return False
            frames=recording.readframes(recording.getnframes())
        samples=array("h")
        samples.frombytes(frames)
        if sys.byteorder!="little":
            samples.byteswap()
        if not samples or sum(abs(s)>=32500 for s in samples)/len(samples)>.10:
            return False
        width=max(1,round(rate*.03))
        blocks=[]
        for start in range(0,len(samples)-width+1,width):
            segment=samples[start:start+width]
            rms=math.sqrt(sum(float(x)*x for x in segment)/width)
            blocks.append(20*math.log10(max(rms,1.0)/32768.0))
        if not blocks:
            return False
        ordered=sorted(blocks)
        low=ordered[max(0,int(len(ordered)*.15)-1)]
        high=ordered[int((len(ordered)-1)*.85)]
        if high<minimum_db:
            return False
        threshold=max(minimum_db,low+noise_margin_db)
        if high-low<noise_margin_db and high>-25:
            threshold=minimum_db
        active=sum(db>threshold for db in blocks)
        return active*.03>=minimum_speech_seconds
    except (OSError,ValueError,EOFError,wave.Error):
        return False

JUNK_TRANSCRIPTS={"","blank audio","silence","music","applause","thank you for watching",
                  "thanks for watching","subtitles by","subscribe to my channel",
                  "you","the end","hmm","uh","um"}

def normalize_transcript(text):
    raw=str(text or "").strip()
    raw=re.sub(r"\[(?:blank_audio|silence|music|applause)\]","",raw,flags=re.I)
    compact=re.sub(r"[^a-z0-9]+"," ",raw.lower()).strip()
    if compact in JUNK_TRANSCRIPTS or len(compact)<2:
        return ""
    if re.search(r"^(?:subtitles|captions)\s+(?:by|provided)",compact):
        return ""
    return raw[:1100]

class TranscriptDeduper:
    def __init__(self,seconds=2.5,clock=time.monotonic):
        self.seconds=seconds
        self.clock=clock
        self.last_key=None
        self.last_time=float("-inf")
    def accept(self,text):
        key=re.sub(r"[^a-z0-9]+"," ",text.lower()).strip()
        if not key:
            return False
        now=self.clock()
        if key==self.last_key and now-self.last_time<self.seconds:
            return False
        self.last_key=key
        self.last_time=now
        return True
