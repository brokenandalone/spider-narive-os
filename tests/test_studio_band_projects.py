"""Tests for durable, owner-private Studio Band Mixer project revisions."""
import json
from pathlib import Path
import tempfile
import unittest
import wave

from studio.band_projects import (
    PROJECTS_ROOT, list_projects, load_project, recent_mixes,
    save_project, validate_project,
)
from studio.song_mix import MixError


def wav(path):
    with wave.open(str(path), 'wb') as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(22050)
        file.writeframes(b'\x00\x00' * 300)


class BandProjectTests(unittest.TestCase):
    def test_private_versioned_save_and_controls_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            guitar = root / 'guitar.wav'
            wav(guitar)
            state = {'rhythm_guitar': {
                'path': str(guitar), 'gain': .75, 'pan': -.45,
                'muted': False, 'solo': True, 'offset_ms': 125,
            }}
            first = save_project('Broken Sorrow Demo', state, root=root / 'projects')
            second = save_project('Broken Sorrow Demo', state, root=root / 'projects')
            self.assertNotEqual(first, second)
            self.assertEqual(first.stat().st_mode & 0o777, 0o600)
            self.assertEqual(first.parent.stat().st_mode & 0o777, 0o700)
            data = load_project(first, root=root / 'projects')
            self.assertEqual(data['title'], 'Broken Sorrow Demo')
            self.assertEqual(data['tracks']['rhythm_guitar']['pan'], -.45)
            self.assertEqual(data['tracks']['rhythm_guitar']['offset_ms'], 125)
            self.assertTrue(data['tracks']['rhythm_guitar']['solo'])
            self.assertEqual(data['missing_sources'], [])
            self.assertEqual(len(list_projects(root=root / 'projects')), 2)
            self.assertTrue(guitar.is_file())

    def test_draft_and_moved_source_are_marked_but_never_deleted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'vocal.wav'
            wav(source)
            project = save_project(
                'Draft voice', {'lead_vocal': {'path': str(source)}},
                root=root / 'projects',
            )
            source.rename(root / 'voice-renamed.wav')
            loaded = load_project(project, root=root / 'projects')
            self.assertEqual(loaded['missing_sources'], ['lead_vocal'])
            self.assertTrue((root / 'voice-renamed.wav').exists())
            empty = save_project('Empty first draft', {}, root=root / 'projects')
            self.assertEqual(load_project(empty, root=root / 'projects')['tracks'], {})

    def test_reject_bad_schema_symlink_cross_library_and_malformed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            projects = root / 'projects'
            saved = save_project('test', {}, root=projects)
            altered = json.loads(saved.read_text())
            altered['schema'] = 999
            saved.write_text(json.dumps(altered))
            with self.assertRaises(MixError):
                load_project(saved, root=projects)
            saved.write_text('not JSON')
            with self.assertRaises(MixError):
                load_project(saved, root=projects)
            with self.assertRaises(MixError):
                load_project(root / 'elsewhere' / 'project.json', root=projects)
            fake = projects / 'project-link'
            fake.symlink_to(saved.parent, target_is_directory=True)
            with self.assertRaises(MixError):
                load_project(fake / 'project.json', root=projects)

    def test_invalid_duplicate_and_nan_settings_fail_without_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vocal = root / 'lead.wav'
            wav(vocal)
            track = {'path': str(vocal), 'gain': 1}
            for value in (float('nan'), float('inf'), True, -1):
                with self.assertRaises(MixError):
                    validate_project('Test', {'lead_vocal': dict(track, gain=value)})
            with self.assertRaises(MixError):
                validate_project('Test', {'lead_vocal': dict(track, solo=1)})
            with self.assertRaises(MixError):
                validate_project('Test', {'lead_vocal': dict(track, offset_ms=60001)})
            with self.assertRaises(MixError):
                validate_project('Test', {'lead_vocal': track, 'guest_vocal': track})
            with self.assertRaises(MixError):
                save_project('Bad', {'random_unknown': track}, root=root / 'projects')
            self.assertFalse((root / 'projects').exists())

    def test_recent_mixes_ignore_fake_and_symlink_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mix = root / 'band-legit'
            mix.mkdir()
            audio = mix / 'band-mix.wav'
            wav(audio)
            (mix / 'band-mix.json').write_text(json.dumps({
                'schema': 1, 'created_at_unix': 123456,
                'render': 'band-mix.wav', 'independent_tracks': [{'role': 'drums'}],
            }))
            other = root / 'band-evil'
            other.mkdir()
            (other / 'band-mix.wav').symlink_to(audio)
            (other / 'band-mix.json').write_text((mix / 'band-mix.json').read_text())
            recent = recent_mixes(root=root)
            self.assertEqual(len(recent), 1)
            self.assertEqual(recent[0]['track_count'], 1)
            self.assertEqual(recent[0]['file'], str(audio))


if __name__ == '__main__':
    unittest.main()
