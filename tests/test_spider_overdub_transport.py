"""Sample-level regression tests for count-in and punch recording transport.

Never opens actual speakers, microphones, sound servers, or live station audio.
"""
from pathlib import Path
import tempfile
import threading
import unittest
import wave

from studio.overdub_transport import transport_plan,write_aligned_punch
from studio.audio_overdub_engine import capture_overdub
from studio.audio_capture_engine import CaptureError

def as_pcm(samples,channels=1):
    return b"".join(
        int(value).to_bytes(2,"little",signed=True)*channels for value in samples)

class BoundedDuplex:
    """PortAudio-like fake with blocks crossing count-in/cue boundaries."""
    def __init__(self,stop):
        self.stop=stop
        self.kwargs=None
        self.written=[]
        self.opened=False

    def RawStream(self,**kwargs):
        self.kwargs=kwargs
        self.opened=True
        owner=self
        class Stream:
            def __enter__(self):
                callback=kwargs["callback"]
                rate=kwargs["samplerate"]
                # Only the first complete simulated intro + cue is emitted.
                # 4 beats at tempo 280 + eight cue samples.
                plan=transport_plan(rate=rate,cue_frames=8,
                                    tempo=280,count_in_bars=1)
                cursor=0
                while cursor<plan.total_frames:
                    count=min(1024,plan.total_frames-cursor)
                    sample=as_pcm([1500]*count,kwargs["channels"][0])
                    output=bytearray(count*4)
                    callback(sample,output,count,None,None)
                    owner.written.append((cursor,bytes(output)))
                    cursor+=count
                return self
            def __exit__(self,*unused):
                return False
        return Stream()

class TransportPlanTests(unittest.TestCase):
    def test_countin_tempo_meter_and_headphone_click_pcm(self):
        plan=transport_plan(rate=48000,cue_frames=100,
                            tempo=120,beats_per_bar=3,count_in_bars=2)
        self.assertEqual(plan.intro_frames,144000)
        self.assertEqual(len(plan.intro_pcm),plan.intro_frames*4)
        self.assertEqual(plan.total_frames,144100)
        # Nonzero stereo metronome at the first tick, and a silent gap.
        self.assertTrue(any(plan.intro_pcm[4:2000]))
        self.assertEqual(plan.intro_pcm[8000:12000],bytes(4000))
        self.assertEqual(plan.intro_pcm[:2],plan.intro_pcm[2:4])
        self.assertEqual(plan.punch_start,0)
        self.assertEqual(plan.punch_end,100)
        plain=transport_plan(rate=44100,cue_frames=123)
        self.assertEqual(plain.intro_pcm,b"")
        self.assertEqual(plain.intro_frames,0)

    def test_punch_boundaries_are_sample_accurate(self):
        plan=transport_plan(rate=48000,cue_frames=48000,
                            punch_start_ms=25,punch_end_ms=175)
        self.assertEqual((plan.punch_start,plan.punch_end),(1200,8400))
        for bad in (
            {"count_in_bars":5},
            {"count_in_bars":True},
            {"beats_per_bar":6},
            {"tempo":10},
            {"tempo":120.0},
            {"punch_start_ms":10},
            {"punch_start_ms":10,"punch_end_ms":10},
            {"punch_start_ms":-1,"punch_end_ms":100},
            {"punch_start_ms":0,"punch_end_ms":1001},
            {"punch_start_ms":True,"punch_end_ms":100},
        ):
            with self.subTest(bad=bad),self.assertRaises(CaptureError):
                transport_plan(rate=48000,cue_frames=48000,**bad)

    def test_punch_gate_applied_after_latency_shift_in_bounded_chunks(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)
            raw=base/"raw.pcm"
            raw.write_bytes(as_pcm(list(range(100,116))))
            for shift, expected in (
                (2,[0,0,102,103,104,105,106,0,0,0,0,0,0,0,0,0]),
                (-2,[0,0,0,0,102,103,104,0,0,0,0,0,0,0,0,0]),
            ):
                target=base/f"shift-{shift}.wav"
                with wave.open(str(target),"wb") as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(2)
                    wav.setframerate(44100)
                    write_aligned_punch(raw,wav,16,16,shift,
                                        punch_start=2,punch_end=7,
                                        chunk_frames=3)
                with wave.open(str(target),"rb") as wav:
                    content=wav.readframes(16)
                    numbers=[int.from_bytes(content[i:i+2],"little",signed=True)
                             for i in range(0,len(content),2)]
                if shift==2:
                    self.assertEqual(numbers,[0,0,104,105,106,107,108,0,0,0,0,0,0,0,0,0])
                else:
                    self.assertEqual(numbers,[0,0,100,101,102,103,104,0,0,0,0,0,0,0,0,0])
                self.assertEqual(len(numbers),16)
            self.assertEqual(raw.read_bytes(),as_pcm(list(range(100,116))))

    def test_full_duplex_preroll_does_not_record_click_into_new_take(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            cue=root/"backing.wav"
            with wave.open(str(cue),"wb") as out:
                out.setnchannels(2)
                out.setsampwidth(2)
                out.setframerate(44100)
                out.writeframes(as_pcm([100,200,300,400,500,600,700,800],2))
            stop=threading.Event()
            device=BoundedDuplex(stop)
            output=root/"take.wav"
            result=capture_overdub(
                output,cue=cue,input_device=0,output_device=1,
                role="lead_vocal",channels=1,rate=44100,max_seconds=2,
                tempo=280,beats_per_bar=4,count_in_bars=1,
                punch_start_ms=None,punch_end_ms=None,
                backend=device,stop=stop)
            self.assertEqual(result["count_in_bars"],1)
            self.assertEqual(result["captured_frames"],8)
            self.assertEqual(result["frames"],8)
            self.assertGreater(result["preroll_seconds"],0)
            click_blocks=[b for frame,b in device.written
                          if frame<result["preroll_seconds"]*44100]
            self.assertTrue(any(any(x) for x in click_blocks))
            sound=b"".join(b for _,b in device.written)
            self.assertIn(as_pcm([100,200,300,400,500,600,700,800],2),sound)
            with wave.open(str(output),"rb") as wav:
                self.assertEqual(wav.getnframes(),8)
                self.assertEqual(wav.readframes(8),as_pcm([1500]*8))
            self.assertEqual(cue.stat().st_size,44+8*4)
            self.assertFalse(list(root.glob("*.part")))

    def test_punch_preflight_precedes_input_or_headphone_stream(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            cue=root/"reference.wav"
            with wave.open(str(cue),"wb") as out:
                out.setnchannels(2);out.setsampwidth(2)
                out.setframerate(48000);out.writeframes(as_pcm([1]*100,2))
            fake=BoundedDuplex(threading.Event())
            with self.assertRaises(CaptureError):
                capture_overdub(
                    root/"fail.wav",cue=cue,input_device=0,output_device=1,
                    role="bass",rate=48000,backend=fake,
                    punch_start_ms=10,punch_end_ms=20)
            self.assertFalse(fake.opened)
            self.assertFalse((root/"fail.wav").exists())

if __name__=="__main__":
    unittest.main()
