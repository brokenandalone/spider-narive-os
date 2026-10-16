"""Headless virtual-duplex tests for clock-aligned backing+input recording.

All PortAudio input/output is simulated. These tests do not claim actual
hardware ADC/DAC calibration or acoustic/monitor latency verification.
"""
import tempfile
import threading
import unittest
import wave
from pathlib import Path

from studio.audio_overdub_engine import available_outputs, capture_overdub
from studio.audio_capture_engine import CaptureError

def create_cue(filename,samples,rate=44100,channels=1):
    with wave.open(str(filename),"wb") as output:
        output.setnchannels(channels)
        output.setsampwidth(2)
        output.setframerate(rate)
        if channels==1:
            raw=b"".join(x.to_bytes(2,"little",signed=True) for x in samples)
        else:
            raw=b"".join(x.to_bytes(2,"little",signed=True)*2 for x in samples)
        output.writeframes(raw)

class FakeDuplex:
    def __init__(self,stop,*,status=False,partial=None,collide=None):
        self.stop=stop
        self.status=status
        self.partial=partial
        self.collide=collide
        self.opened=False
        self.written=[]
        self.kwargs=None

    def query_devices(self):
        return [
            {"name":"Mic","max_input_channels":2,"max_output_channels":0},
            {"name":"Monitor headphones","max_input_channels":0,"max_output_channels":2},
        ]

    def RawStream(self,**kwargs):
        self.opened=True
        self.kwargs=kwargs
        owner=self
        class Duplex:
            def __enter__(self):
                if owner.collide is not None:
                    owner.collide.write_bytes(b"another owner's work")
                callback=kwargs["callback"]
                # Each returned sample is known for exact alignment testing.
                frames_remaining=owner.partial if owner.partial is not None else 8
                index=0
                while frames_remaining>0:
                    count=min(4,frames_remaining)
                    unit=2*kwargs["channels"][0]
                    raw=b"".join(
                        ((1000+i).to_bytes(2,"little",signed=True)*
                         kwargs["channels"][0])
                        for i in range(index,index+count))
                    self_test = len(raw)==unit*count
                    assert self_test
                    outdata=bytearray(count*4)
                    callback(raw,outdata,count,None,
                             "output underrun" if owner.status else None)
                    owner.written.append(bytes(outdata))
                    index+=count
                    frames_remaining-=count
                    if owner.status:
                        break
                owner.stop.set()
                return self
            def __exit__(self,kind,value,tb):
                return False
        return Duplex()

def unpack16(raw):
    return [int.from_bytes(raw[i:i+2],"little",signed=True)
            for i in range(0,len(raw),2)]

class FullDuplexOverdubTests(unittest.TestCase):
    def test_refresh_outputs_does_not_open_audio(self):
        stop=threading.Event()
        fake=FakeDuplex(stop)
        self.assertEqual(available_outputs(fake),[(1,"Monitor headphones",2)])
        self.assertFalse(fake.opened)

    def test_backing_and_input_share_sample_frame_timeline(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            cue=root/"original-cue.wav"
            create_cue(cue,[12,23,34,45,56,67,78,89])
            target=root/"aligned-take.wav"
            stopped=threading.Event()
            fake=FakeDuplex(stopped)
            result=capture_overdub(
                target,cue=cue,input_device=0,output_device=1,
                role="lead_vocal",channels=1,rate=44100,
                max_seconds=1,stop=stopped,backend=fake)
            self.assertTrue(fake.opened)
            self.assertEqual(fake.kwargs["channels"],(1,2))
            self.assertEqual(fake.kwargs["dtype"],"int16")
            self.assertEqual(result["captured_frames"],8)
            self.assertEqual(result["frames"],8)
            self.assertEqual(result["timing"],"single_duplex_callback_stream_clock")
            played=b"".join(fake.written)
            # A mono backing cue is duplicated into L/R outputs.
            self.assertEqual(unpack16(played),[12,12,23,23,34,34,45,45,
                                              56,56,67,67,78,78,89,89])
            with wave.open(str(target),"rb") as wav:
                self.assertEqual(wav.getnframes(),8)
                self.assertEqual(wav.getsampwidth(),2)
                self.assertEqual(wav.getnchannels(),1)
                self.assertEqual(unpack16(wav.readframes(8)),
                                 [1000,1001,1002,1003,1004,1005,1006,1007])
            self.assertFalse(any(root.glob("*.part")))
            self.assertTrue(cue.exists())

    def test_sample_compensation_advances_or_delays_and_fills_silence(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            cue=root/"cue.wav"
            create_cue(cue,[1]*200,rate=44100,channels=2)
            for offset in (1,-1):
                with self.subTest(ms=offset):
                    target=root/f"shift-{offset}.wav"
                    stop=threading.Event()
                    fake=FakeDuplex(stop,partial=100)
                    result=capture_overdub(
                        target,cue=cue,input_device=0,output_device=1,
                        role="bass",channels=1,rate=44100,
                        max_seconds=1,stop=stop,backend=fake,latency_ms=offset)
                    self.assertEqual(result["frames"],200)
                    with wave.open(str(target),"rb") as wav:
                        data=unpack16(wav.readframes(200))
                        self.assertEqual(len(data),200)
                        if offset==1:
                            self.assertEqual(data[:4],[1044,1045,1046,1047])
                            self.assertEqual(data[56:],[0]*144)
                        else:
                            self.assertEqual(data[:44],[0]*44)
                            self.assertEqual(data[44:48],[1000,1001,1002,1003])
                            self.assertEqual(data[144:],[0]*56)
                    self.assertEqual(result["compensation_ms"],offset)

    def test_partial_stop_pads_remaining_duration_without_mixing_cue(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            cue=root/"cue.wav"
            create_cue(cue,[301]*8)
            stop=threading.Event()
            fake=FakeDuplex(stop,partial=4)
            result=capture_overdub(
                root/"partial.wav",cue=cue,input_device=0,output_device=1,
                role="lead_guitar",channels=1,rate=44100,
                max_seconds=1,stop=stop,backend=fake)
            self.assertEqual(result["captured_frames"],4)
            with wave.open(str(root/"partial.wav"),"rb") as wav:
                self.assertEqual(unpack16(wav.readframes(8)),
                                 [1000,1001,1002,1003,0,0,0,0])

    def test_failed_duplex_rejects_take_without_replacing_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            cue=root/"cue.wav"
            create_cue(cue,[11]*8)
            for status in (True,False):
                stop=threading.Event()
                target=root/("broken.wav" if status else "existing.wav")
                if not status:
                    target.write_bytes(b"original owner data")
                fake=FakeDuplex(stop,status=status)
                with self.subTest(status=status),self.assertRaises(CaptureError):
                    capture_overdub(
                        target,cue=cue,input_device=0,output_device=1,
                        role="backing_vocal",rate=44100,max_seconds=1,
                        stop=stop,backend=fake)
                self.assertEqual(target.exists(),not status)
                if not status:
                    self.assertEqual(target.read_bytes(),b"original owner data")
            self.assertFalse(any(root.glob("*.part")))

    def test_reject_incorrect_cue_format_rate_output_and_latency(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            cue=root/"guide.wav"
            create_cue(cue,[8]*100,rate=48000)
            bad=[
                {"rate":44100},
                {"latency_ms":251},
                {"latency_ms":1.25},
                {"output_device":-1},
                {"max_seconds":0},
            ]
            for changes in bad:
                args={"cue":cue,"input_device":0,"output_device":1,
                      "role":"drums","rate":48000,"max_seconds":1}
                args.update(changes)
                fake=FakeDuplex(threading.Event())
                with self.subTest(bad=changes),self.assertRaises(CaptureError):
                    capture_overdub(root/"reject.wav",backend=fake,**args)
                self.assertFalse(fake.opened)
                self.assertFalse((root/"reject.wav").exists())

if __name__=="__main__":
    unittest.main()
