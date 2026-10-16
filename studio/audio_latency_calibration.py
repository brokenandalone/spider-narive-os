"""Owner-triggered audio-interface loopback calibration.

A short low-level coded signal plays over one explicitly selected stereo
output and is measured on one explicitly selected input. This measures
round-trip stream+device delay ONLY if the user physically loops the output
back into that input. It does not infer speaker-to-microphone latency safely.

Never starts from construction or device discovery. Only called after user
clicks Measure Loopback. Playback is limited to a short, -18 dBFS code.
"""
from __future__ import annotations
from array import array
import math
import sys
import threading
import time

try:
    from .audio_capture_engine import CaptureError, _backend
except ImportError:
    from audio_capture_engine import CaptureError, _backend

PROBE_SECONDS=1.25
MAX_DELAY_MS=250
CODE_SAMPLES=101

def _code():
    state=0xACE1
    taps=[]
    for i in range(CODE_SAMPLES):
        bit=((state>>0)^(state>>2)^(state>>3)^(state>>5))&1
        state=(state>>1)|(bit<<15)
        taps.append(3600 if state&1 else -3600)
    return taps

def probe_samples(rate):
    if type(rate) is not int or rate not in (44100,48000):
        raise CaptureError("Calibration requires 44.1/48 kHz")
    total=round(PROBE_SECONDS*rate)
    result=[0]*total
    code=_code()
    for seconds in (.10,.38,.66):
        pos=round(seconds*rate)
        result[pos:pos+len(code)]=code
    return result

def estimate_latency(captured, rate, *, minimum_level=50):
    """Normalized coded-pulse correlation over 0..250 ms, no FFT dependency.

    Three independently positioned bursts must agree within 3 frames or a
    false positive, noisy signal, missing cable, or variable-latency route is
    rejected. The desired result is a measured sample offset, not a promise
    of acoustically perfect alignment in the user's environment.
    """
    if type(rate) is not int or rate not in (44100,48000):
        raise CaptureError("Invalid calibration sample rate")
    if not isinstance(captured,(tuple,list)):
        raise CaptureError("Calibrator requires signed PCM input samples")
    if len(captured)<round(PROBE_SECONDS*rate):
        raise CaptureError("Calibration input is shorter than the probe")
    code=_code()
    energy=sum(x*x for x in code)
    max_delay=round(rate*MAX_DELAY_MS/1000)
    best=[]
    for second in (.10,.38,.66):
        start=round(second*rate)
        winner=(float("-inf"),-1)
        # A sparse, polarity-aware score across the coded burst tolerates
        # ordinary analog gain and DC offset while rejecting isolated spikes.
        for lag in range(max_delay+1):
            pos=start+lag
            if pos+len(code)>len(captured):
                break
            dot=0
            norm=0
            for offset,reference in enumerate(code):
                sample=captured[pos+offset]
                dot+=reference*sample
                norm+=sample*sample
            if norm<=0:
                continue
            correlation=dot/math.sqrt(energy*norm)
            if correlation>winner[0]:
                winner=(correlation,lag)
        if winner[1]<0 or winner[0]<.70:
            raise CaptureError("Loopback signal not detected reliably. Check direct cable, level and routing")
        best.append(winner)
    delays=[x[1] for x in best]
    if max(delays)-min(delays)>3:
        raise CaptureError("Loopback arrivals disagree; unstable device delay or missing signal")
    samples=round(sum(delays)/3)
    # A successful reference correlation should have measurable input energy.
    if max(abs(captured[round(.10*rate)+samples+i]) for i in range(CODE_SAMPLES))<minimum_level:
        raise CaptureError("Loopback recording level is too low")
    return {"round_trip_samples":samples,
            "round_trip_ms":round(1000*samples/rate,3),
            "sample_rate":rate,"confidence":round(min(x[0] for x in best),3),
            "type":"physical_loopback_round_trip",
            "warning":"Round-trip measurement is not a separately measured ADC input offset"}

def measure_loopback(*,input_device,output_device,rate=48000,
                     stop=None,backend=None):
    """Open one selected full-duplex stream only after explicit user approval."""
    if (type(input_device) is not int or not 0<=input_device<=1024 or
            type(output_device) is not int or not 0<=output_device<=1024):
        raise CaptureError("Select an existing input and stereo output before calibration")
    stopped=stop if stop is not None else threading.Event()
    if stopped.is_set():
        raise CaptureError("Calibration was cancelled before opening hardware")
    samples=probe_samples(rate)
    api=_backend(backend)
    recorded=[]
    state={"sent":0,"error":None,"last":time.monotonic()}
    def callback(indata,outdata,frames,timing,status):
        outdata[:]=bytes(len(outdata))
        if status:
            state["error"]="Audio dropouts interrupted calibration"
            stopped.set()
            return
        if frames<=0 or frames>8192 or len(indata)!=frames*2 or len(outdata)!=frames*4:
            state["error"]="Unexpected duplex calibration sample layout"
            stopped.set()
            return
        wanted=min(frames,len(samples)-state["sent"])
        if wanted:
            out=array("h")
            for i in range(wanted):
                value=samples[state["sent"]+i]
                out.extend((value,value))
            if sys.byteorder!="little":
                out.byteswap()
            outdata[:wanted*4]=out.tobytes()
            inp=array("h")
            inp.frombytes(bytes(indata[:wanted*2]))
            if sys.byteorder!="little":
                inp.byteswap()
            recorded.extend(inp)
            state["sent"]+=wanted
        state["last"]=time.monotonic()
        if state["sent"]>=len(samples):
            stopped.set()
    try:
        with api.RawStream(samplerate=rate,device=(input_device,output_device),
                           channels=(1,2),dtype="int16",blocksize=1024,callback=callback):
            while not stopped.is_set():
                if time.monotonic()-state["last"]>3:
                    raise CaptureError("Loopback hardware did not deliver audio frames")
                time.sleep(.01)
    except (OSError,RuntimeError,ValueError) as exc:
        raise CaptureError("Cannot use the selected loopback inputs and outputs: "+str(exc)[:180]) from exc
    if state["error"]:
        raise CaptureError(state["error"])
    if state["sent"]!=len(samples):
        raise CaptureError("Loopback was stopped before capture finished")
    return estimate_latency(recorded,rate)
