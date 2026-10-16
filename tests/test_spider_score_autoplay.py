"""Notation-to-performance tests, no speakers or SoundFont required."""
import struct
import tempfile
from pathlib import Path
import unittest
from studio.score_performance import import_musicxml,import_ascii_tab,Note
from studio.score_audio_render import performance_midi,export_performance_midi,soundfont_ready

SCORE="""<?xml version="1.0"?>
<score-partwise version="4.0">
<work><work-title>Spider Score Test</work-title></work>
<part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list>
<part id="P1"><measure number="1">
<attributes><divisions>4</divisions></attributes>
<direction><sound tempo="100"/></direction>
<note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration></note>
<note><chord/><pitch><step>E</step><octave>4</octave></pitch><duration>4</duration></note>
<note><rest/><duration>4</duration></note>
<note><pitch><step>G</step><octave>4</octave></pitch><duration>8</duration></note>
</measure></part></score-partwise>"""
TAB="""e|--0---3---5---|
B|--1---3---5---|
G|--0---0---5---|
D|--2---0---7---|
A|--3---2---7---|
E|------3---5---|"""
class ScoreAutoplayTests(unittest.TestCase):
    def test_musicxml_chords_rests_and_tempo(self):
        performance=import_musicxml(SCORE)
        self.assertEqual(performance.bpm,100)
        self.assertEqual([(n.start,n.duration,n.pitch) for n in performance.notes],
                         [(0,480,60),(0,480,64),(960,960,67)])
        self.assertGreater(performance.seconds,0)
        self.assertEqual(performance.tracks,["Piano"])
        self.assertTrue(performance_midi(performance).startswith(b"MThd"))
    def test_ascii_guitar_tabs_are_polyphonic(self):
        song=import_ascii_tab(TAB,bpm=120)
        self.assertEqual(len(song.notes),17)
        self.assertEqual(song.notes[0].start,240)
        self.assertEqual(song.tracks,["Guitar"])
        self.assertTrue(all(40<=n.pitch<=88 for n in song.notes))
        with tempfile.TemporaryDirectory() as directory:
            filename=Path(directory)/"score.mid"
            export_performance_midi(song,filename)
            self.assertEqual(filename.read_bytes()[8:14],struct.pack(">HHH",1,2,480))
    def test_bass_and_invalid_tab(self):
        bass="G|--0---2--|\nD|--0---2--|\nA|--0---2--|\nE|--0---2--|"
        self.assertEqual(len(import_ascii_tab(bass,"bass").notes),8)
        with self.assertRaises(ValueError):
            import_ascii_tab(TAB,"bass")
        with self.assertRaises(ValueError):
            import_ascii_tab(TAB.replace("--0---3","--0--25"),"guitar")
    def test_no_unsafe_xml_entities_or_bad_score(self):
        with self.assertRaises(ValueError):
            import_musicxml("<!DOCTYPE foo [ <!ENTITY x SYSTEM 'file:///etc/passwd'> ]>"+SCORE)
        with self.assertRaises(ValueError):
            import_musicxml("<score-timewise/>")
        with self.assertRaises(ValueError):
            import_musicxml("x" * 2_000_001)
        with self.assertRaises(ValueError):
            Note(0,0,60)
    def test_soundfont_requires_an_actual_installed_bank(self):
        self.assertFalse(soundfont_ready("/definitely/missing/spider.sf2"))

if __name__=="__main__":
    unittest.main()
