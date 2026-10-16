"""Real PCM audio capture smoke tests with a fake consented input stream.

No microphones, speakers, ALSA/PipeWire services or external packages used.
"""
from pathlib import Path
import tempfile
import threading
import unittest
import wave

from studio.audio_capture_engine import (
    available_inputs,capture_take,new_take_filename,CaptureError,QUEUE_LIMIT)

class FakeBackend:
    def __init__(self,stop,*,chunks=3,bad_status=False,overflow=False,
                 create_collision=None):
        self.stop=stop
        self.chunks=chunks
        self.bad_status=bad_status
        self.overflow=overflow
        self.create_collision=create_collision
        self.opened=False
        self.kwargs={}
    def query_devices(self):
        return [{"name":"Output only","max_input_channels":0},
                {"name":"Fake private stereo input","max_input_channels":2}]
    def RawInputStream(self,**kwargs):
        self.opened=True
        self.kwargs=kwargs
        owner=self
        class Stream:
            def __enter__(self):
                if owner.create_collision is not None:
                    owner.create_collision.write_bytes(b"preexisting")
                cb=kwargs["callback"]
                if owner.bad_status:
                    cb(bytes(64),16,None,"input overflow")
                else:
                    count=(QUEUE_LIMIT+5) if owner.overflow else owner.chunks
                    for index in range(count):
                        # 32 frames of two channels at 16 bits = 128 bytes.
                        cb(b"\xe8\x03\x18\xfc"*32,32,None,None)
                        if owner.stop.is_set():
                            break
                owner.stop.set()
                return self
            def __exit__(self,typ,val,tb):
                return False
        return Stream()

class AudioCaptureEngineTests(unittest.TestCase):
    def test_manual_input_discovery_does_not_open_device(self):
        stop=threading.Event()
        fake=FakeBackend(stop)
        self.assertEqual(available_inputs(fake),[(1,"Fake private stereo input",2)])
        self.assertFalse(fake.opened)

    def test_private_stereo_recording_writes_pcm_and_preserves_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            stop=threading.Event()
            fake=FakeBackend(stop,chunks=3)
            dest=root/"Spider-Recording.wav"
            result=capture_take(dest,device=1,role="lead_vocal",channels=2,
                                rate=48000,max_seconds=3,backend=fake,stop=stop)
            self.assertEqual(Path(result["path"]),dest)
            self.assertEqual(result["frames"],96)
            self.assertEqual(result["sample_width_bits"],16)
            self.assertEqual(result["channels"],2)
            self.assertTrue(fake.opened)
            self.assertEqual(fake.kwargs["dtype"],"int16")
            with wave.open(str(dest),"rb") as wav:
                self.assertEqual(wav.getnchannels(),2)
                self.assertEqual(wav.getsampwidth(),2)
                self.assertEqual(wav.getframerate(),48000)
                self.assertEqual(wav.getnframes(),96)
                self.assertEqual(wav.readframes(1),b"\xe8\x03\x18\xfc")
            self.assertEqual(dest.stat().st_mode & 0o777,0o600)
            self.assertFalse(list(root.glob("*.part")))

    def test_mono_format_and_no_existing_takes_replaced(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            initial=root/"already.wav"
            initial.write_bytes(b"private original take")
            fake=FakeBackend(threading.Event())
            with self.assertRaises(CaptureError):
                capture_take(initial,device=1,role="bass",backend=fake)
            self.assertEqual(initial.read_bytes(),b"private original take")
            self.assertFalse(fake.opened)
            mono_backend=FakeBackend(threading.Event())
            # 32 frames of mono 16-bit PCM
            class Mono(FakeBackend):
                def RawInputStream(self,**kwargs):
                    self.opened=True
                    owner=self
                    class Stream:
                        def __enter__(self):
                            kwargs["callback"](b"\xe8\x03"*32,32,None,None)
                            owner.stop.set()
                            return self
                        def __exit__(self,*a): return False
                    return Stream()
            one=Mono(threading.Event())
            song=root/"mono.wav"
            capture_take(song,device=1,role="bass",channels=1,rate=44100,
                         stop=one.stop,backend=one,max_seconds=5)
            with wave.open(str(song),"rb") as reader:
                self.assertEqual(reader.getnframes(),32)
                self.assertEqual(reader.getframerate(),44100)
                self.assertEqual(reader.getnchannels(),1)

    def test_audio_device_errors_drop_incomplete_recording(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for label,kwargs in (
                ("port-xrun",{"bad_status":True}),
                ("buffer-overflow",{"overflow":True}),
            ):
                with self.subTest(label=label):
                    stop=threading.Event()
                    fake=FakeBackend(stop,**kwargs)
                    target=root/(label+".wav")
                    with self.assertRaises(CaptureError):
                        capture_take(target,device=1,role="drums",stop=stop,
                                     backend=fake,max_seconds=3,channels=2)
                    self.assertFalse(target.exists())
            self.assertFalse(list(root.glob("*.part")))

    def test_atomic_race_and_strict_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            dest=root/"record.wav"
            stop=threading.Event()
            backend=FakeBackend(stop,create_collision=dest)
            with self.assertRaises(FileExistsError):
                capture_take(dest,device=1,role="piano_keys",stop=stop,backend=backend)
            self.assertEqual(dest.read_bytes(),b"preexisting")
            for values in ({"device":-1},{"channels":4},{"rate":96000},
                           {"max_seconds":301},{"role":"unknown"}):
                params=dict(device=1,role="bass",channels=1,rate=48000,max_seconds=3)
                params.update(values)
                with self.subTest(values=values),self.assertRaises(CaptureError):
                    capture_take(root/"reject.wav",backend=backend,**params)
            one=new_take_filename(root,"lead_guitar",clock=313)
            self.assertEqual(one.name,"Spider-lead_guitar-313.wav")
            one.write_bytes(b"existing")
            with self.assertRaises(FileExistsError):
                new_take_filename(root,"lead_guitar",clock=313)

if __name__=="__main__":
    unittest.main()
