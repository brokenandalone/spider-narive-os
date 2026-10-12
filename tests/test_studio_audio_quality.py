"""Real read-only PCM audio QC tests, without microphone or AI models."""
import math
from pathlib import Path
import struct
import tempfile
import threading
import unittest
import wave

from studio.audio_quality import QualityError, _samples, audit_assets, inspect_wav


def make_wav(path, frames, *, rate=8000, channels=1, width=2, sample=0):
    if width == 1:
        value = bytes([sample])
    elif width == 2:
        value = struct.pack('<h', sample)
    elif width == 3:
        value = int(sample).to_bytes(3, 'little', signed=True)
    else:
        value = struct.pack('<i', sample)
    with wave.open(str(path), 'wb') as wav:
        wav.setframerate(rate)
        wav.setnchannels(channels)
        wav.setsampwidth(width)
        wav.writeframes(value * channels * frames)


class AudioQualityTests(unittest.TestCase):
    def test_pcm_levels_silence_and_near_full_scale_are_measured(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            silent = root / 'silent.wav'
            peak = root / 'peak.wav'
            make_wav(silent, 3200)
            make_wav(peak, 4000, sample=32767)
            before = (silent.read_bytes(), peak.read_bytes())
            a = inspect_wav(silent)
            b = inspect_wav(peak)
            self.assertIsNone(a['sample_peak_dbfs'])
            self.assertIsNone(a['rms_dbfs'])
            self.assertIn('digital silence', ' '.join(a['warnings']))
            self.assertAlmostEqual(b['sample_peak_dbfs'], 0, places=2)
            self.assertGreater(b['near_full_scale_samples'], 0)
            self.assertIn('Near-full-scale', ' '.join(b['warnings']))
            self.assertEqual(before, (silent.read_bytes(), peak.read_bytes()))

    def test_8_16_24_32_bit_signed_pcm_normalization(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for width, value in ((1, 0), (2, -32768), (3, -8388608),
                                 (4, -2147483648)):
                file = root / f'{width}.wav'
                make_wav(file, 160, width=width, sample=value)
                result = inspect_wav(file)
                self.assertEqual(result['sample_width_bits'], width * 8)
                self.assertEqual(result['sample_peak_dbfs'], 0.0)
                self.assertEqual(result['sampled_seconds'], .02)
                self.assertTrue(result['near_full_scale_samples'] > 0)
                self.assertAlmostEqual(result['dc_offset_ratio'], -1.0)
            # 8-bit PCM is unsigned, so value=128 is exact silence.
            eight = root / 'unsigned-silence.wav'
            make_wav(eight, 200, width=1, sample=128)
            self.assertIsNone(inspect_wav(eight)['sample_peak_dbfs'])

    def test_only_samples_8_seconds_each_edge_and_reports_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / 'long.wav'
            make_wav(file, 30 * 8000)
            report = inspect_wav(file)
            self.assertEqual(report['duration_seconds'], 30)
            self.assertEqual(report['sampled_seconds'], 16)
            self.assertLess(report['sampled_seconds'], report['duration_seconds'])

    def test_bad_sources_symlinks_duplicate_and_cancel_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            good = root / 'good.wav'
            make_wav(good, 800)
            shortcut = root / 'shortcut.wav'
            shortcut.symlink_to(good)
            bad = root / 'bad.wav'
            bad.write_text('not audio')
            for file in (shortcut, bad):
                with self.subTest(file=file), self.assertRaises(QualityError):
                    inspect_wav(file)
            with self.assertRaises(QualityError):
                audit_assets({'lead_guitar': str(good), 'drums': str(good)})
            with self.assertRaises(QualityError):
                audit_assets({'some_unknown_role': str(good)})
            event = threading.Event()
            event.set()
            with self.assertRaisesRegex(QualityError, 'cancelled'):
                inspect_wav(good, stop=event)

    def test_cross_track_duration_rate_and_full_song_reference_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            one, two = root / 'one.wav', root / 'two.wav'
            make_wav(one, 8000, rate=8000, channels=1)
            make_wav(two, 88200, rate=44100, channels=2)
            report = audit_assets({
                'reference_mix': str(one), 'rhythm_guitar': str(two),
            })
            warnings = ' '.join(report['session_warnings'])
            self.assertIn('durations differ', warnings)
            self.assertIn('sample rates differ', warnings)
            self.assertIn('whole-song reference', warnings)
            self.assertIn('Mono', ' '.join(report['tracks']['reference_mix']['warnings']))
            self.assertEqual(report['analysis'], 'first_and_last_8_seconds_only')


if __name__ == '__main__':
    unittest.main()
