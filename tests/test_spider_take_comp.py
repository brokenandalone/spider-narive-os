"""Regression tests for non-destructive 16/24-bit recording take comping."""
import tempfile
import unittest
import wave
from pathlib import Path

from studio.take_comp_engine import CompSegment,comp_takes
from studio.audio_capture_engine import CaptureError

def wav(path,values,*,rate=44100,channels=1,width=2):
    with wave.open(str(path),"wb") as out:
        out.setnchannels(channels)
        out.setsampwidth(width)
        out.setframerate(rate)
        out.writeframes(b"".join(
            int(n).to_bytes(width,"little",signed=True)*channels
            for n in values))

def read(path):
    with wave.open(str(path),"rb") as source:
        frames=source.getnframes()
        width=source.getsampwidth()
        channels=source.getnchannels()
        raw=source.readframes(frames)
        values=[int.from_bytes(raw[i:i+width],"little",signed=True)
                for i in range(0,len(raw),width)]
        return values,frames,width,channels

class TakeCompTests(unittest.TestCase):
    def test_two_source_crossfade_changes_only_new_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            a=root/"first.wav";b=root/"second.wav"
            wav(a,[1000]*1000)
            wav(b,[-1000]*1000)
            original_a=a.read_bytes()
            original_b=b.read_bytes()
            target=root/"new-comp.wav"
            result=comp_takes(
                [a,b],[CompSegment(0,500,0),CompSegment(500,1000,1)],
                target,crossfade_ms=2)
            values,frames,width,channels=read(target)
            self.assertEqual((frames,width,channels),(1000,2,1))
            self.assertEqual(values[0],1000)
            self.assertEqual(values[-1],-1000)
            self.assertGreater(values[450],0)
            self.assertAlmostEqual(values[500],0,delta=2)
            self.assertLess(values[550],0)
            self.assertEqual(result["segments"],2)
            self.assertEqual(target.stat().st_mode&0o777,0o600)
            self.assertEqual(a.read_bytes(),original_a)
            self.assertEqual(b.read_bytes(),original_b)
            self.assertFalse(list(root.glob("*.part")))

    def test_multi_segment_stereo_native_24bit_and_no_crossfade(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            paths=[root/f"take-{n}.wav" for n in range(3)]
            for i,path in enumerate(paths):
                wav(path,[i*1_000_000]*30,rate=48000,channels=2,width=3)
            dest=root/"edited.wav"
            comp_takes(paths,[(0,10,0),(10,20,1),(20,30,2)],
                       dest,crossfade_ms=0)
            values,frames,width,channels=read(dest)
            self.assertEqual((frames,width,channels),(30,3,2))
            self.assertEqual(values[:20],[0]*20)
            self.assertEqual(values[20:40],[1_000_000]*20)
            self.assertEqual(values[40:],[2_000_000]*20)

    def test_bad_or_overlapping_segments_and_mismatched_takes_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            a=root/"a.wav";b=root/"b.wav"
            wav(a,[100]*1000)
            wav(b,[200]*1000)
            invalid=[
                [(0,501,0),(500,1000,1)],
                [(0,100,0),(110,1000,1)],
                [(0,500,0),(500,1001,1)],
                [(0,500,0),(500,1000,2)],
                [(0,500,True),(500,1000,1)],
            ]
            for idx,segments in enumerate(invalid):
                target=root/f"bad-{idx}.wav"
                with self.subTest(idx=idx),self.assertRaises(CaptureError):
                    comp_takes([a,b],segments,target)
                self.assertFalse(target.exists())
            wav(root/"unequal.wav",[1]*999)
            with self.assertRaises(CaptureError):
                comp_takes([a,root/"unequal.wav"],[(0,1000,0)],root/"bad.wav")
            with self.assertRaises(CaptureError):
                comp_takes([a,a],[(0,1000,0)],root/"bad2.wav")
            target=root/"existing.wav"
            target.write_bytes(b"owner's original recording")
            with self.assertRaises(CaptureError):
                comp_takes([a,b],[(0,1000,0)],target)
            self.assertEqual(target.read_bytes(),b"owner's original recording")

    def test_cancelled_comp_never_publishes_new_file(self):
        import threading
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            first=root/"one.wav";second=root/"two.wav"
            wav(first,[100]*1000)
            wav(second,[-100]*1000)
            cancelled=threading.Event();cancelled.set()
            with self.assertRaises(CaptureError):
                comp_takes([first,second],[(0,1000,0)],root/"cancel.wav",
                           stop=cancelled)
            self.assertFalse((root/"cancel.wav").exists())

if __name__=="__main__":
    unittest.main()
