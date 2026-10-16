"""No-hardware physical-loopback latency calibration regression suite."""
import tempfile
import threading
import unittest

from studio.audio_latency_calibration import (
    estimate_latency, probe_samples, measure_loopback)
from studio.audio_capture_engine import CaptureError

class MockLoopback:
    def __init__(self,lag,rate=44100,missing=False):
        self.rate=rate
        self.lag=lag
        self.missing=missing
        self.opened=False
    def RawStream(self,**kwargs):
        self.opened=True
        unit=kwargs["channels"][0]
        assert kwargs["dtype"]=="int16"
        assert kwargs["samplerate"]==self.rate
        song=probe_samples(self.rate)
        owner=self
        class Stream:
            def __enter__(self):
                callback=kwargs["callback"]
                pos=0
                while pos<len(song):
                    count=min(1024,len(song)-pos)
                    raw=b"".join(
                        (0 if owner.missing or i<owner.lag
                         else song[i-owner.lag]).to_bytes(2,"little",signed=True)
                        for i in range(pos,pos+count))
                    out=bytearray(count*4)
                    callback(raw,out,count,None,None)
                    pos+=count
                return self
            def __exit__(self,*args):
                return False
        return Stream()

class LoopbackLatencyTests(unittest.TestCase):
    def test_three_known_pulses_find_exact_delay_with_scaled_input(self):
        rate=44100
        original=probe_samples(rate)
        for lag in (0,137,1024):
            captured=[0]*lag+[round(s*.45) for s in original]
            result=estimate_latency(captured,rate)
            self.assertEqual(result["round_trip_samples"],lag)
            self.assertAlmostEqual(result["round_trip_ms"],lag*1000/rate,places=3)
            self.assertGreater(result["confidence"],.99)
            self.assertEqual(result["type"],"physical_loopback_round_trip")

    def test_owner_triggered_duplex_collects_output_and_input(self):
        fake=MockLoopback(137,rate=44100)
        self.assertFalse(fake.opened)
        observed=measure_loopback(input_device=0,output_device=1,
                                  rate=44100,backend=fake)
        self.assertTrue(fake.opened)
        self.assertEqual(observed["round_trip_samples"],137)

    def test_missing_loopback_rejected_not_guessed(self):
        fake=MockLoopback(0,missing=True)
        with self.assertRaises(CaptureError):
            measure_loopback(input_device=0,output_device=1,
                             rate=44100,backend=fake)
        self.assertTrue(fake.opened)

    def test_bad_devices_and_cancel_rejected_before_opening(self):
        fake=MockLoopback(0)
        for params in ({"input_device":-1},{"output_device":-1},
                       {"rate":96000}):
            args=dict(input_device=0,output_device=1,rate=44100,backend=fake)
            args.update(params)
            with self.assertRaises(CaptureError):
                measure_loopback(**args)
            self.assertFalse(fake.opened)
        stop=threading.Event();stop.set()
        with self.assertRaises(CaptureError):
            measure_loopback(input_device=0,output_device=1,
                             backend=fake,stop=stop)
        self.assertFalse(fake.opened)

if __name__=="__main__":
    unittest.main()
