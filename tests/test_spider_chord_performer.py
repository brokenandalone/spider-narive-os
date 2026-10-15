"""Fully generated musical accompaniment from standard chord-only charts."""
from pathlib import Path
import tempfile
import unittest
from studio.chord_chart_performer import parse_chord_chart
from studio.score_performer import load_notation
from studio.score_midi import encode_performance_midi

class ChordPerformerTests(unittest.TestCase):
    def test_chord_chart_has_original_four_part_accompaniment(self):
        p = parse_chord_chart("[Verse]\nAm | F | C | G", bpm=92)
        self.assertEqual(p.bpm, 92)
        self.assertEqual(p.beats, 16)
        self.assertEqual(len(p.parts), 4)
        self.assertEqual({part.channel for part in p.parts}, {0, 1, 2, 9})
        self.assertGreater(len(p.notes), 70)
        self.assertTrue(any(n.pitch == 36 and n.part == 3 for n in p.notes))
        self.assertTrue(any(n.part == 0 for n in p.notes))
        self.assertTrue(any(n.part == 1 for n in p.notes))
        self.assertTrue(any(n.part == 2 for n in p.notes))
        midi = encode_performance_midi(p)
        self.assertEqual(midi[:4], b"MThd")
        self.assertIn(bytes([0x99, 38, 97]), midi)

    def test_slash_bass_and_chord_variants(self):
        p = parse_chord_chart("C/E | F#m7 | Bbmaj7 | Gsus4", 114)
        self.assertEqual(len(p.notes), len(parse_chord_chart("C G Am F", 114).notes) + 12)
        # The first bass note is E2/E3 depending on register, pitch class E.
        bass = next(n for n in p.notes if n.part == 1)
        self.assertEqual(bass.pitch % 12, 4)

    def test_bad_lyrics_not_silently_interpreted_as_chords(self):
        with self.assertRaisesRegex(ValueError, "Unrecognized chord"):
            parse_chord_chart("I love you baby\nAm F C G")
        with self.assertRaises(ValueError):
            parse_chord_chart("Am " * 129)
        with self.assertRaises(ValueError):
            parse_chord_chart("")

    def test_chord_file_import(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "accompaniment.chords"
            path.write_text("Am | F | C | G")
            song = load_notation(path, bpm=100)
            self.assertEqual(song.bpm, 100)
            self.assertEqual(song.origin, path.resolve())
            self.assertEqual(len(song.parts), 4)

if __name__ == "__main__":
    unittest.main()
