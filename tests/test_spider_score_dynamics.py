"""Verify written dynamics and articulation from real MusicXML score grammar."""
from fractions import Fraction
import unittest
from studio.score_performer import parse_musicxml

SHEET = """<?xml version="1.0"?>
<score-partwise version="4.0">
  <part-list><score-part id="P1"><part-name>Electric Guitar</part-name></score-part></part-list>
  <part id="P1"><measure number="1">
    <attributes><divisions>1</divisions></attributes>
    <direction><direction-type><dynamics><pp/></dynamics></direction-type></direction>
    <note>
      <pitch><step>C</step><octave>4</octave></pitch><duration>1</duration>
      <notations><articulations><staccato/></articulations></notations>
    </note>
    <direction><direction-type><dynamics><ff/></dynamics></direction-type></direction>
    <note>
      <pitch><step>D</step><octave>4</octave></pitch><duration>1</duration>
      <notations><articulations><accent/></articulations></notations>
    </note>
    <direction><sound dynamics="78"/></direction>
    <note><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration></note>
    <note><rest/><duration>1</duration></note>
  </measure></part>
</score-partwise>"""

class MusicXMLExpressionTests(unittest.TestCase):
    def test_dynamic_levels_staccato_and_accent(self):
        score=parse_musicxml(SHEET)
        self.assertEqual([n.pitch for n in score.notes], [60,62,64])
        self.assertEqual([n.velocity for n in score.notes], [44,127,78])
        self.assertEqual(score.notes[0].duration,Fraction(1,2))
        self.assertEqual(score.notes[1].duration,Fraction(1))
        self.assertEqual(score.notes[2].start,Fraction(2))
        self.assertEqual(score.parts[0].program,27)
        self.assertEqual(score.beats,4)

    def test_invalid_dynamic_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_musicxml(SHEET.replace('dynamics="78"', 'dynamics="not-a-number"'))

if __name__=="__main__":
    unittest.main()
