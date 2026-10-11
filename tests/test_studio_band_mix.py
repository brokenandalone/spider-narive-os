"""Offline tests for independent guitar/vocal stems and private mix receipts."""
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import wave
from studio import band_mix
from studio.song_mix import MixError


def wav(path, stereo=False, rate=8000):
    with wave.open(str(path), 'wb') as out:
        out.setnchannels(2 if stereo else 1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(b'\0\0' * (1600 if stereo else 800))


class FakeProcess:
    def __init__(self, argv, **kwargs):
        self.returncode = 0
        wav(Path(argv[-1]), stereo=True, rate=48000)
    def poll(self):
        return self.returncode


class BandMixTests(unittest.TestCase):
    def test_two_guitars_and_guest_singer_are_independent_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            stems = {role: root / (role + '.wav') for role in
                     ('backing', 'lead_vocal', 'guest_vocal', 'rhythm_guitar', 'lead_guitar')}
            for audio in stems.values(): wav(audio)
            cmd = band_mix.band_mix_command('ffmpeg', stems, {'lead_guitar': .7}, root / 'fresh.wav')
            graph = cmd[cmd.index('-filter_complex') + 1]
            self.assertIn('amix=inputs=5', graph)
            self.assertIn('volume=0.700[stem4]', graph)
            self.assertEqual(cmd.count('-i'), 5)
            self.assertIn('-n', cmd)
            self.assertNotIn('-y', cmd)

    def test_private_render_receipt_and_unchanged_tracks(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            stems = {'backing': root / 'bed.wav', 'rhythm_guitar': root / 'rhythm.wav',
                     'lead_guitar': root / 'lead.wav', 'guest_vocal': root / 'female.wav'}
            for audio in stems.values(): wav(audio)
            before = {role: path.read_bytes() for role, path in stems.items()}
            with patch.object(band_mix.shutil, 'which', return_value='/usr/bin/ffmpeg'), \
                 patch.object(band_mix.subprocess, 'Popen', side_effect=FakeProcess) as launch:
                output = band_mix.mix_band_tracks(stems, output_root=root / 'exports',
                                                  gains={'guest_vocal': .9})
            self.assertEqual(output.name, 'band-mix.wav')
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(output.parent.stat().st_mode & 0o777, 0o700)
            manifest = output.parent / 'band-mix.json'
            self.assertEqual(manifest.stat().st_mode & 0o777, 0o600)
            data = json.loads(manifest.read_text())
            self.assertEqual([e['role'] for e in data['independent_tracks']],
                             ['backing', 'guest_vocal', 'rhythm_guitar', 'lead_guitar'])
            self.assertTrue(data['source_tracks_preserved'])
            self.assertEqual(before, {role: path.read_bytes() for role, path in stems.items()})
            self.assertEqual(launch.call_count, 1)
            self.assertNotIn('shell', launch.call_args.kwargs)

    def test_reject_duplicates_symlink_fake_wav_and_bad_gains(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            one, two = root / 'one.wav', root / 'two.wav'
            wav(one); wav(two)
            with self.assertRaises(MixError):
                band_mix.validate_tracks({'backing': one, 'lead_guitar': one})
            (root / 'linked.wav').symlink_to(one)
            with self.assertRaises(MixError):
                band_mix.validate_tracks({'backing': one, 'lead_guitar': root / 'linked.wav'})
            (root / 'fake.wav').write_text('not WAV')
            with self.assertRaises(MixError):
                band_mix.validate_tracks({'backing': one, 'lead_guitar': root / 'fake.wav'})
            for gain in (-.1, 2.1, float('nan'), True):
                with self.assertRaises(MixError):
                    band_mix.validate_tracks({'backing': one, 'lead_guitar': two}, {'backing': gain})
            with self.assertRaises(MixError):
                band_mix.validate_tracks({'backing': one, 'unknown': two})
            hardlink = root / 'hardlink.wav'; hardlink.hardlink_to(one)
            with self.assertRaises(MixError):
                band_mix.validate_tracks({'backing': one, 'lead_guitar': hardlink})

    def test_pan_and_mute_are_independent_and_encoded_in_filter(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            stems = {'rhythm_guitar': root / 'rhythm.wav',
                     'lead_guitar': root / 'lead.wav',
                     'guest_vocal': root / 'guest.wav'}
            for source in stems.values():
                wav(source)
            cmd = band_mix.band_mix_command(
                'ffmpeg', stems, {'lead_guitar': .7}, root / 'out.wav',
                pans={'rhythm_guitar': -.35, 'lead_guitar': .45},
                mutes={'guest_vocal': True},
            )
            graph = cmd[cmd.index('-filter_complex') + 1]
            self.assertIn('balance_out=-0.350', graph)
            self.assertIn('balance_out=0.450', graph)
            self.assertIn('volume=0.700', graph)
            self.assertIn('volume=0.000[stem0]', graph)
            self.assertEqual(cmd.count('-i'), 3)

    def test_bad_pan_mute_and_all_silent_rejected_before_export(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            tracks = {'rhythm_guitar': root / 'one.wav',
                      'lead_guitar': root / 'two.wav'}
            for path in tracks.values():
                wav(path)
            for pan in (True, float('nan'), float('inf'), -1.1, 1.1, 'left'):
                with self.assertRaises(MixError):
                    band_mix.validate_mix_options(tracks, {'rhythm_guitar': pan})
            for mute in (0, 'yes', None):
                with self.assertRaises(MixError):
                    band_mix.validate_mix_options(tracks, mutes={'lead_guitar': mute})
            with self.assertRaisesRegex(MixError, 'Unmute'):
                band_mix.mix_band_tracks(
                    tracks, output_root=root / 'out',
                    mutes={'rhythm_guitar': True, 'lead_guitar': True},
                )
            self.assertFalse((root / 'out').exists())
            with self.assertRaises(MixError):
                band_mix.validate_mix_options(tracks, {'bass': 0.3})

    def test_mix_manifest_records_pan_and_muted_flags(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            tracks = {'rhythm_guitar': root / 'one.wav',
                      'lead_guitar': root / 'two.wav'}
            for path in tracks.values():
                wav(path)
            with patch.object(band_mix.shutil, 'which', return_value='/usr/bin/ffmpeg'), \
                 patch.object(band_mix.subprocess, 'Popen', side_effect=FakeProcess):
                target = band_mix.mix_band_tracks(
                    tracks, output_root=root / 'out',
                    pans={'rhythm_guitar': -.4, 'lead_guitar': .4},
                    mutes={'rhythm_guitar': True},
                )
            record = json.loads((target.parent / 'band-mix.json').read_text())
            by_role = {row['role']: row for row in record['independent_tracks']}
            self.assertEqual(by_role['rhythm_guitar']['pan'], -.4)
            self.assertTrue(by_role['rhythm_guitar']['muted'])
            self.assertEqual(by_role['lead_guitar']['pan'], .4)
            self.assertFalse(by_role['lead_guitar']['muted'])

    def test_audio_offsets_encoded_in_ffmpeg_with_exact_millisecond_values(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            tracks = {'rhythm_guitar': root / 'rhythm.wav',
                      'lead_guitar': root / 'lead.wav'}
            for path in tracks.values(): wav(path)
            command = band_mix.band_mix_command(
                'ffmpeg', tracks, {}, root / 'fresh.wav',
                offsets_ms={'rhythm_guitar': 450, 'lead_guitar': 5})
            graph = command[command.index('-filter_complex') + 1]
            self.assertIn('adelay=450:all=1', graph)
            self.assertIn('adelay=5:all=1', graph)
            self.assertEqual(command.count('-i'), 2)
            self.assertIn('-n', command)
            for invalid in (-1, 60001, False, 2.5, '100'):
                with self.assertRaises(MixError):
                    band_mix.validate_offsets(tracks, {'lead_guitar': invalid})
            with self.assertRaises(MixError):
                band_mix.validate_offsets(tracks, {'unknown': 250})

    def test_inspect_tracks_reports_duration_and_sample_rate_mismatch(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            a, b = root / 'one.wav', root / 'two.wav'
            wav(a, rate=8000)
            wav(b, rate=44100)
            # Produce a genuine >0.5s duration difference, not just rate drift.
            with wave.open(str(a), 'wb') as long_audio:
                long_audio.setnchannels(1)
                long_audio.setsampwidth(2)
                long_audio.setframerate(8000)
                long_audio.writeframes(bytes(16000))
            inspection = band_mix.inspect_tracks({'drums': a, 'bass': b})
            self.assertEqual(inspection['tracks']['drums']['sample_rate'], 8000)
            self.assertEqual(inspection['tracks']['bass']['sample_rate'], 44100)
            self.assertTrue(any('Sample rates differ' in note for note in inspection['warnings']))
            self.assertTrue(any('durations differ' in note for note in inspection['warnings']))

    def test_receipt_records_offset_without_changing_input_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            tracks = {'rhythm_guitar': root / 'rhythm.wav',
                      'lead_guitar': root / 'lead.wav'}
            for source in tracks.values(): wav(source)
            before = {k: v.read_bytes() for k, v in tracks.items()}
            with (patch.object(band_mix.shutil, 'which', return_value='/usr/bin/ffmpeg'),
                  patch.object(band_mix.subprocess, 'Popen', side_effect=FakeProcess)):
                out = band_mix.mix_band_tracks(
                    tracks, output_root=root / 'mixes',
                    offsets_ms={'lead_guitar': 120})
            data = json.loads((out.parent / 'band-mix.json').read_text())
            roles = {row['role']: row for row in data['independent_tracks']}
            self.assertEqual(roles['lead_guitar']['offset_ms'], 120)
            self.assertEqual(roles['rhythm_guitar']['offset_ms'], 0)
            self.assertEqual(before, {k: v.read_bytes() for k, v in tracks.items()})

    def test_cancel_before_output_and_refuse_existing_target(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            one, two = root / 'one.wav', root / 'two.wav'
            wav(one); wav(two)
            selected = {'backing': one, 'lead_guitar': two}
            stop = threading.Event(); stop.set()
            with self.assertRaisesRegex(MixError, 'cancelled'):
                band_mix.mix_band_tracks(selected, output_root=root / 'new-folder', stop=stop)
            self.assertFalse((root / 'new-folder').exists())
            (root / 'existing.wav').touch()
            with self.assertRaises(MixError):
                band_mix.band_mix_command('ffmpeg', selected, {}, root / 'existing.wav')
