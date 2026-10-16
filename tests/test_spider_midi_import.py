"""Roundtrip notation and imported type-0/1 MIDI without MIDI devices."""
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest

from studio.score_performer import Performance, Note, Part, parse_musicxml
from studio.score_midi import encode_performance_midi
from studio.midi_score_import import import_midi, import_midi_file
from studio.midi_song_export import chunk, track_bytes

class MIDIScoreImportTests(unittest.TestCase):
    def example(self):
        return Performance(
            "Studio Session", 120,
            [Part("Lead Guitar", 30, 0), Part("Bass", 33, 1), Part("Drum Kit", 0, 9)],
            [
                Note(0, 64, Fraction(0), Fraction(1), 92),
                Note(0, 67, Fraction(0), Fraction(1), 96),
                Note(1, 40, Fraction(2), Fraction(3,2), 101),
                Note(2, 36, Fraction(4), Fraction(1,8), 112),
            ],
            Fraction(8), [], (4, 4),
            tempo_changes=[(Fraction(4), 60)],
        ).validated()

    def test_type_one_roundtrip_pitches_timing_velocities_and_tempo(self):
        original = self.example()
        encoded = encode_performance_midi(original)
        restored = import_midi(encoded)
        self.assertEqual(restored.bpm, 120)
        self.assertEqual(restored.tempo_changes, [(Fraction(4), 60)])
        self.assertAlmostEqual(original.duration_seconds, 6.0)
        self.assertAlmostEqual(restored.duration_seconds, 6.0)
        self.assertEqual(restored.beats, original.beats)
        self.assertEqual(sorted((n.pitch,n.start,n.duration,n.velocity)
                                for n in restored.notes),
                         sorted((n.pitch,n.start,n.duration,n.velocity)
                                for n in original.notes))
        self.assertEqual([part.program for part in restored.parts], [30, 33, 0])
        self.assertEqual([part.channel for part in restored.parts], [0, 1, 9])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"Spider Session.mid"
            path.write_bytes(encoded)
            imported=import_midi_file(path)
            self.assertEqual(imported.origin,path.resolve())
            self.assertEqual(imported.title,"Spider Session")

    def test_single_track_format_zero_running_status(self):
        # Running status second note uses previous 0x90.
        events = bytes([
            0, 0xC0, 24,
            0, 0x90, 60, 100,
            0, 64, 77,
            0x81, 0x70, 0x80, 60, 0,
            0, 64, 0,  # Running status of note-off
            0, 0xFF, 0x2F, 0
        ])
        track=chunk(b"MTrk",events)
        header=chunk(b"MThd",b"\x00\x00\x00\x01\x01\xe0")
        result=import_midi(header+track)
        self.assertEqual([n.pitch for n in result.notes],[60,64])
        self.assertEqual([n.velocity for n in result.notes],[100,77])
        self.assertEqual(result.notes[0].duration,Fraction(1,2))
        self.assertEqual(result.parts[0].program,24)

    def test_broken_and_unsafe_inputs_fail(self):
        valid=encode_performance_midi(self.example())
        for bad in (b"bad",valid[:10],valid[:-2],valid.replace(b"MTrk",b"XXXX",1),
                    valid[:12]+b"\xe7\x28"+valid[14:]):
            with self.subTest(bad=bad[:12]),self.assertRaises(ValueError):
                import_midi(bad)
        with self.assertRaises(ValueError):
            import_midi(b"x"*2_000_001)

    def test_musicxml_midscore_tempo_stays_when_exported(self):
        xml="""<score-partwise>
        <part-list><score-part id="P1"><part-name>Keys</part-name></score-part></part-list>
        <part id="P1">
        <measure number="1"><attributes><divisions>1</divisions></attributes>
          <direction><sound tempo="120"/></direction>
          <note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration></note>
        </measure>
        <measure number="2">
          <direction><sound tempo="60"/></direction>
          <note><pitch><step>E</step><octave>4</octave></pitch><duration>4</duration></note>
        </measure></part></score-partwise>"""
        original=parse_musicxml(xml)
        self.assertEqual(original.tempo_changes,[(Fraction(4),60)])
        self.assertAlmostEqual(original.duration_seconds,6.0)
        again=import_midi(encode_performance_midi(original))
        self.assertEqual(again.tempo_changes,[(Fraction(4),60)])
        self.assertAlmostEqual(again.duration_seconds,6.0)

if __name__=="__main__":
    unittest.main()
