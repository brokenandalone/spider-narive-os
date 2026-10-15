"""Score expression tests: written notes stay safe; performance feels musical."""
from fractions import Fraction
import unittest

from studio.score_performer import Performance, Note, Part
from studio.performance_expression import Expression, GROOVES, express

class MusicalExpressionTests(unittest.TestCase):
    def score(self):
        return Performance(
            "Spider Band", 120,
            [Part("Electric Guitar", 27, 0), Part("Finger Bass", 33, 1),
             Part("Drum Set", 0, 9)],
            [Note(0, 60, Fraction(0), Fraction(1), 90),
             Note(0, 64, Fraction(0), Fraction(1), 90),
             Note(0, 67, Fraction(0), Fraction(1), 90),
             Note(1, 40, Fraction(1, 2), Fraction(1, 2), 88),
             Note(2, 38, Fraction(1), Fraction(1, 8), 100)],
            Fraction(4)).validated()

    def test_reproducible_and_non_destructive(self):
        original = self.score()
        before = list(original.notes)
        kwargs = Expression("Natural player", 70, 12, 313)
        a = express(original, kwargs)
        b = express(original, kwargs)
        self.assertEqual(a.notes, b.notes)
        self.assertEqual(original.notes, before)
        self.assertEqual([n.pitch for n in a.notes], sorted(n.pitch for n in before))
        self.assertEqual(len(a.notes), len(before))
        self.assertTrue(all(n.start >= 0 and n.start+n.duration <= a.beats for n in a.notes))

    def test_as_written_with_no_strum_is_exact(self):
        src = self.score()
        out = express(src, Expression("As written", 75, 0))
        self.assertEqual(out.notes, src.notes)

    def test_swing_moves_only_offbeat_and_strum_rolls_chord(self):
        src = self.score()
        out = express(src, Expression("Swing 60%", 75, 12))
        bass = [n for n in out.notes if n.part == 1][0]
        self.assertGreater(bass.start, Fraction(1, 2))
        guitar_starts = sorted(n.start for n in out.notes if n.part == 0)
        self.assertEqual(len(set(guitar_starts)), 3)

    def test_velocity_bounds_and_invalid_config(self):
        src = self.score()
        strong = express(src, Expression("Driving rock", 100, 0))
        soft = express(src, Expression("Natural player", 0, 0))
        self.assertTrue(all(1 <= n.velocity <= 127 for n in strong.notes))
        self.assertLess(sum(n.velocity for n in soft.notes),
                        sum(n.velocity for n in strong.notes))
        for setting in (Expression("nonsense"), Expression("As written", -1),
                        Expression("As written", 75, 99)):
            with self.assertRaises(ValueError):
                express(src, setting)

if __name__ == "__main__":
    unittest.main()
