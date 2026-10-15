"""Spider Auto Performer source-grade notation and SoundFont rendering tests."""
from pathlib import Path
import struct
from types import SimpleNamespace
import tempfile
import unittest
from zipfile import ZipFile
from unittest.mock import patch
import wave

from studio.score_performer import (
    parse_musicxml, parse_ascii_tab, load_notation, Performance, Part, Note
)
from studio.score_midi import encode_performance_midi, export_performance_midi
from studio.soundfont_render import render_soundfont, validate_soundfont

SCORE = """<?xml version="1.0" encoding="utf-8"?>
<score-partwise version="4.0">
<work><work-title>Spider Performance</work-title></work>
<movement-title>Spider Performance</movement-title>
<part-list>
 <score-part id="P1"><part-name>Guitar</part-name></score-part>
 <score-part id="P2"><part-name>Piano</part-name></score-part>
</part-list>
<part id="P1">
 <measure number="1">
 <attributes><divisions>8</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
 <direction><sound tempo="96"/></direction>
 <note><pitch><step>E</step><octave>4</octave></pitch><duration>8</duration><tie type="start"/></note>
 <note><pitch><step>E</step><octave>4</octave></pitch><duration>8</duration><tie type="stop"/></note>
 <note><rest/><duration>8</duration></note>
 <note><pitch><step>G</step><octave>4</octave></pitch><duration>8</duration></note>
 <note><chord/><pitch><step>B</step><octave>4</octave></pitch><duration>8</duration></note>
 </measure>
 <measure number="2">
 <note><pitch><step>F</step><alter>1</alter><octave>4</octave></pitch><duration>32</duration></note>
 </measure>
</part>
<part id="P2">
 <measure number="1">
 <attributes><divisions>8</divisions></attributes>
 <note><pitch><step>C</step><octave>4</octave></pitch><duration>32</duration></note>
 </measure>
 <measure number="2">
 <note><pitch><step>D</step><octave>4</octave></pitch><duration>32</duration></note>
 </measure>
</part>
</score-partwise>
"""
TAB = """e|--0---2---3---2-|
B|--1---3---0---3-|
G|--0---2---0---2-|
D|--2---0---0---0-|
A|--3-------2-----|
E|----------3-----|"""

class TestScorePerformer(unittest.TestCase):
    def test_musicxml_chords_ties_meter_tempo_parts(self):
        performance = parse_musicxml(SCORE)
        self.assertEqual(performance.title, "Spider Performance")
        self.assertEqual(performance.bpm, 96)
        self.assertEqual(performance.meter, (4, 4))
        self.assertEqual(len(performance.parts), 2)
        self.assertEqual(len(performance.notes), 6)
        self.assertEqual(len([n for n in performance.notes if n.pitch == 64 and n.part == 0]), 1)
        tied = [n for n in performance.notes if n.pitch == 64][0]
        self.assertEqual(float(tied.duration), 2.0)
        self.assertEqual(float(performance.beats), 8.0)
        chords = [n for n in performance.notes if n.start == 3 and n.part == 0]
        self.assertEqual({n.pitch for n in chords}, {67, 71})
        self.assertEqual(performance.parts[0].program, 24)

    def test_tab_polyphony_and_time_columns(self):
        p = parse_ascii_tab(TAB, bpm=122, slots_per_beat=2)
        self.assertEqual(p.bpm, 122)
        self.assertEqual(p.parts[0].name, "Guitar")
        self.assertEqual(len(p.notes), 19)
        first = [n.pitch for n in p.notes if n.start == 1]
        self.assertEqual(set(first), {64, 60, 55, 52, 48})
        self.assertTrue(p.warnings)
        bass = parse_ascii_tab("G|--0-2--|\nD|--0-2--|\nA|--0-2--|\nE|--0-2--|", bpm=110)
        self.assertEqual(len(bass.notes), 8)
        self.assertEqual(bass.parts[0].program, 33)
        self.assertEqual(bass.notes[0].pitch, 28)

    def test_reject_unsupported_and_insecure_scores(self):
        with self.assertRaisesRegex(ValueError, "entities|DTD"):
            parse_musicxml('<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]>' + SCORE)
        with self.assertRaises(ValueError):
            parse_musicxml("<score-timewise/>")
        with self.assertRaises(ValueError):
            parse_ascii_tab("E|--4-p-5-|\nB|--0-----|\nG|--------|\nD|--------|\nA|--------|\nE|--------|")
        with self.assertRaises(ValueError):
            parse_ascii_tab("e|--0-|\nB|--0-|\nG|--0-|\nD|--0-|")  # wrong bass string order

    def test_musicxml_drums_and_embedded_gm_programs(self):
        xml = """<score-partwise>
          <part-list>
            <score-part id="DR">
              <part-name>Drums</part-name>
              <score-instrument id="KICK"><instrument-name>Bass Drum</instrument-name></score-instrument>
              <midi-instrument id="KICK">
                <midi-channel>10</midi-channel><midi-unpitched>37</midi-unpitched>
              </midi-instrument>
            </score-part>
            <score-part id="EL">
              <part-name>Guitar</part-name>
              <score-instrument id="ELEC"><instrument-name>Electric</instrument-name></score-instrument>
              <midi-instrument id="ELEC"><midi-program>31</midi-program></midi-instrument>
            </score-part>
          </part-list>
          <part id="DR"><measure number="1">
            <attributes><divisions>1</divisions></attributes>
            <note><unpitched><display-step>A</display-step><display-octave>2</display-octave></unpitched>
              <duration>1</duration><instrument id="KICK"/></note>
          </measure></part>
          <part id="EL"><measure number="1">
            <attributes><divisions>1</divisions></attributes>
            <note><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration></note>
          </measure></part>
        </score-partwise>"""
        p = parse_musicxml(xml)
        self.assertEqual(p.parts[0].channel, 9)
        self.assertEqual(p.parts[1].program, 30)  # 1-based MusicXML -> MIDI patch 30
        self.assertEqual(p.notes[0].pitch, 36)
        raw = encode_performance_midi(p)
        self.assertIn(bytes((0x99, 36, 95)), raw)
        self.assertIn(bytes((0xC0, 30)), raw)

    def test_performance_midi_tracks_note_off_and_tempo(self):
        p = parse_musicxml(SCORE)
        raw = encode_performance_midi(p)
        self.assertEqual(raw[:4], b"MThd")
        self.assertEqual(struct.unpack(">HHH", raw[8:14]), (1, 3, 480))
        self.assertIn(b"\xff\x51\x03", raw)
        self.assertIn(bytes((0x90, 64, 95)), raw)
        self.assertIn(bytes((0x80, 64, 0)), raw)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "score.mid"
            export_performance_midi(p, output)
            self.assertEqual(output.read_bytes(), raw)
            notation = Path(directory) / "score.musicxml"
            notation.write_text(SCORE)
            self.assertEqual(load_notation(notation).bpm, 96)
            imported = load_notation(notation)
            self.assertEqual(imported.origin, notation.resolve())
            with self.assertRaisesRegex(ValueError, "original sheet music"):
                export_performance_midi(imported, notation)

    def test_safe_compressed_mxl_and_reject_path_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            src = Path(directory) / "score.mxl"
            container = ('<container><rootfiles><rootfile '
                         'full-path="Notation/music.xml"/></rootfiles></container>')
            with ZipFile(src, "w") as package:
                package.writestr("META-INF/container.xml", container)
                package.writestr("Notation/music.xml", SCORE)
            self.assertEqual(load_notation(src).bpm, 96)
            self.assertEqual(len(load_notation(src).notes), 6)
            with ZipFile(src, "w") as package:
                package.writestr(
                    "META-INF/container.xml",
                    '<container><rootfiles><rootfile full-path="../outside.musicxml"/>'
                    '</rootfiles></container>')
                package.writestr("../outside.musicxml", SCORE)
            with self.assertRaises(ValueError):
                load_notation(src)

    def test_optional_soundfont_renderer_and_no_unapproved_device(self):
        p = parse_musicxml(SCORE)
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            sf = home / "test.sf2"
            sf.write_bytes(b"RIFF" + bytes(4) + b"sfbk" + bytes(128))
            self.assertEqual(validate_soundfont(sf), sf)
            wavout = home / "sample.wav"
            observations = []
            def fake_renderer(command, stdout, stderr, timeout, check):
                observations.append(command)
                self.assertIn("-n", command)
                self.assertIn("-i", command)
                self.assertIn("-F", command)
                self.assertIn("-T", command)
                self.assertIn("-O", command)
                self.assertNotIn("sh", command)
                target = Path(command[command.index("-F") + 1])
                with wave.open(str(target), "wb") as f:
                    f.setnchannels(2)
                    f.setsampwidth(2)
                    f.setframerate(44100)
                    f.writeframes(b"\x00\x00\x07\x00" * 512)
                return SimpleNamespace(returncode=0)
            with patch("studio.soundfont_render.shutil.which", return_value="/usr/bin/fluidsynth"):
                result = render_soundfont(p, sf, wavout, runner=fake_renderer)
            self.assertEqual(result, wavout)
            self.assertEqual(len(observations), 1)
            with wave.open(str(wavout), "rb") as audio:
                self.assertEqual(audio.getnchannels(), 2)
                self.assertEqual(audio.getframerate(), 44100)
            self.assertTrue(sf.is_file())
            with self.assertRaises(ValueError):
                validate_soundfont(home / "none.sf2")
            with self.assertRaises(ValueError):
                parse_ascii_tab("", 110)

if __name__ == "__main__":
    unittest.main()
