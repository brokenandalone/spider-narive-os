"""Controller-independent note-on/off capture tests for Spider MIDI takes."""
from fractions import Fraction
import unittest

from studio.midi_take_recorder import MIDITake
from studio.score_midi import encode_performance_midi
from studio.midi_score_import import import_midi

class MIDITakeCaptureTests(unittest.TestCase):
    def test_note_lengths_velocities_chords_and_multi_instrument(self):
        recorder = MIDITake(120)
        recorder.start(100.0)
        recorder.event("note_on", 60, 91, 100.0, "keys")
        recorder.event("note_on", 64, 105, 100.0, "keys")
        recorder.event("note_off", 60, 0, 100.5, "keys")
        recorder.event("note_off", 64, 0, 101.0, "keys")
        recorder.event("note_on", 40, 110, 101.0, "bass")
        recorder.event("note_off", 40, 0, 101.25, "bass")
        recorder.stop(101.5)
        song=recorder.as_performance()
        self.assertEqual([p.name for p in song.parts], ["Keyboard","Bass"])
        self.assertEqual([(n.pitch,n.start,n.duration,n.velocity)
                          for n in song.notes],
                         [(60,Fraction(0),Fraction(1),91),
                          (64,Fraction(0),Fraction(2),105),
                          (40,Fraction(2),Fraction(1,2),110)])
        imported=import_midi(encode_performance_midi(song))
        self.assertEqual(len(imported.notes), 3)
        self.assertEqual(sorted(n.velocity for n in imported.notes),[91,105,110])

    def test_stop_closes_held_notes_and_minimum_one_tick(self):
        take=MIDITake(120)
        take.start(50)
        take.event("note_on",52,82,50.1,"guitar")
        take.stop(50.1)
        score=take.as_performance()
        self.assertEqual(score.notes[0].duration,Fraction(1,480))
        self.assertEqual(score.parts[0].program,24)

    def test_opt_in_limits_and_invalid_events(self):
        rec=MIDITake(100)
        with self.assertRaises(ValueError):
            rec.event("note_on",60,90,10.0)
        rec.start(10.0)
        with self.assertRaises(ValueError):
            rec.start(12.0)
        with self.assertRaises(ValueError):
            rec.event("note_on",60,90,9.5)
        with self.assertRaises(ValueError):
            rec.event("note_on",128,90,10.1)
        with self.assertRaises(ValueError):
            rec.event("note_on",60,90,10.1,"flute")
        rec.event("note_on",60,88,10.2)
        with self.assertRaises(ValueError):
            rec.event("note_on",62,80,10.15)
        with self.assertRaises(ValueError):
            rec.event("note_on",62,80,10.0 + 181)
        rec.stop(10.5)
        with self.assertRaises(ValueError):
            rec.event("note_on",61,80,10.6)
        with self.assertRaises(ValueError):
            rec.stop(10.7)
        with self.assertRaises(ValueError):
            MIDITake(20)

if __name__ == "__main__":
    unittest.main()
