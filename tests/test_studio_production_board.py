"""Studio v10 private production checkpoint safety and workflow tests."""
import json
import os
from pathlib import Path
import tempfile
import unittest
import wave

from studio.production_board import (
    ProductionError, create_session, latest_status, list_sessions,
    load_session, next_action, save_revision,
)


def wav(path):
    with wave.open(str(path), 'wb') as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(22050)
        output.writeframes(bytes(4096))


class ProductionBoardTests(unittest.TestCase):
    def test_revisioned_song_does_not_change_recordings(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            library = root / 'songs'
            song = create_session('Mercer and Ninth', root=library)
            self.assertTrue(song.startswith('session-'))
            original = root / 'guitar.wav'
            wav(original)
            before = original.read_bytes()
            first = save_revision(song, 'Mercer and Ninth',
                {'rhythm_guitar': str(original)}, {'rhythm_guitar': True},
                notes='Keep lead separate', root=library)
            second = save_revision(song, 'Mercer and Ninth',
                {'rhythm_guitar': str(original)}, {'rhythm_guitar': True},
                notes='Different guitar tone', root=library)
            os.utime(second, ns=(first.stat().st_atime_ns, first.stat().st_mtime_ns + 2000))
            self.assertNotEqual(first, second)
            self.assertTrue(first.exists())
            self.assertTrue(second.exists())
            self.assertEqual(original.read_bytes(), before)
            self.assertEqual(first.stat().st_mode & 0o777, 0o600)
            self.assertEqual(first.parent.stat().st_mode & 0o777, 0o700)
            current = load_session(song, root=library)
            self.assertEqual(current['notes'], 'Different guitar tone')
            self.assertTrue(current['reviewed_stems']['rhythm_guitar'])
            self.assertEqual(len(list_sessions(root=library)), 1)

    def test_source_moved_is_flagged_and_never_deleted(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            src = root / 'voice.wav'
            wav(src)
            library = root / 'sessions'
            sid = create_session('Voices', root=library)
            save_revision(sid, 'Voices',
                {'lead_vocal': str(src)}, {'lead_vocal': True}, root=library)
            src.rename(root / 'voice-moved.wav')
            report = load_session(sid, root=library)
            self.assertEqual(report['missing'], ['lead_vocal'])
            self.assertTrue((root / 'voice-moved.wav').is_file())

    def test_no_fake_stems_inferred_from_full_song_and_no_sensitive_voice_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            src = root / 'full-mix.wav'
            wav(src)
            library = root / 'sessions'
            sid = create_session('Secret Song Title', notes='private lyrics and voice', root=library)
            save_revision(sid, 'Secret Song Title',
                {'reference_mix': str(src)}, {}, notes='secret intimate lyric', root=library)
            data = load_session(sid, root=library)
            self.assertIn('Review separated', next_action(data))
            report = latest_status(root=library)
            self.assertIn('song reference available', report)
            self.assertIn('0 reviewed', report)
            for secret in ('Secret Song Title', 'private lyrics', 'secret intimate lyric', str(src)):
                self.assertNotIn(secret, report)

    def test_reject_duplicate_wavs_symlinks_and_unreviewed_roles(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            src = root / 'source.wav'
            wav(src)
            library = root / 'sessions'
            sid = create_session('Safe', root=library)
            with self.assertRaises(ProductionError):
                save_revision(sid, 'Safe',
                    {'backing': str(src), 'lead_vocal': str(src)},
                    {'backing': True, 'lead_vocal': True}, root=library)
            with self.assertRaises(ProductionError):
                save_revision(sid, 'Safe', {}, {'lead_vocal': True}, root=library)
            with self.assertRaises(ProductionError):
                save_revision(sid, 'Safe', {'lead_vocal': str(src)},
                              {'lead_vocal': 'yes'}, root=library)
            linked = root / 'linked.wav'
            linked.symlink_to(src)
            with self.assertRaises(ProductionError):
                save_revision(sid, 'Safe', {'backing': str(linked)}, {}, root=library)
            with self.assertRaises(ProductionError):
                load_session('../escape', root=library)
            with self.assertRaises(ProductionError):
                create_session('invalid\x00title', root=library)

    def test_damaged_and_symlink_revisions_are_not_loaded(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            library = root / 'sessions'
            sid = create_session('Cautious', root=library)
            old = load_session(sid, root=library)
            corrupt = library / sid / ('revision-' + 'f' * 32 + '.json')
            corrupt.write_text('not a JSON object')
            os.utime(corrupt, ns=(10**17, 10**17))
            # Broken newest revision is skipped instead of replacing old data.
            result = load_session(sid, root=library)
            self.assertEqual(result['title'], old['title'])
            poison = library / sid / ('revision-' + 'e' * 32 + '.json')
            poison.symlink_to(corrupt)
            self.assertEqual(load_session(sid, root=library)['title'], 'Cautious')
            library_link = root / 'linked-library'
            library_link.symlink_to(library, target_is_directory=True)
            with self.assertRaises(ProductionError):
                list_sessions(root=library_link)

    def test_stage_progress_requires_real_reviewed_stems_and_final_wav(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            files = {name: root / (name + '.wav') for name in
                     ('ref', 'guitar', 'drums', 'final')}
            for file in files.values():
                wav(file)
            library = root / 'sessions'
            sid = create_session('Song', root=library)
            save_revision(sid, 'Song', {
                'reference_mix': str(files['ref']),
                'rhythm_guitar': str(files['guitar']),
                'drums': str(files['drums']),
            }, {'rhythm_guitar': True, 'drums': True}, root=library)
            info = load_session(sid, root=library)
            self.assertIn('Send two or more', next_action(info))
            self.assertIn('2 reviewed', latest_status(root=library))
            save_revision(sid, 'Song', {
                'reference_mix': str(files['ref']),
                'rhythm_guitar': str(files['guitar']),
                'drums': str(files['drums']),
                'final_mix': str(files['final']),
            }, {'rhythm_guitar': True, 'drums': True}, root=library)
            self.assertIn('Release Desk', next_action(load_session(sid, root=library)))


if __name__ == '__main__':
    unittest.main()
