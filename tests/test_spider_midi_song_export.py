"""Standard MIDI file format-1 export compatibility checks."""
from pathlib import Path
import struct
import tempfile
import unittest

from studio.instruments_engine import Pattern
from studio.song_arranger_engine import Song
from studio.midi_song_export import encode_song_midi, vlq, write_song_midi

def tracks(data):
    assert data[:4] == b"MThd"
    length, format_no, count, division = struct.unpack_from(">IHHH", data, 4)
    assert (length, format_no, division) == (6, 1, 480)
    position = 8 + length
    chunks = []
    for i in range(count):
        assert data[position:position+4] == b"MTrk"
        size = struct.unpack_from(">I", data, position + 4)[0]
        chunks.append(data[position+8:position+8+size])
        position += 8 + size
    assert position == len(data)
    return chunks

class MidiExportTests(unittest.TestCase):
    def test_variable_length_encoding(self):
        self.assertEqual(vlq(0), b"\x00")
        self.assertEqual(vlq(127), b"\x7f")
        self.assertEqual(vlq(128), b"\x81\x00")
        self.assertEqual(vlq(0x2000), b"\xc0\x00")
        with self.assertRaises(ValueError):
            vlq(-1)

    def test_full_format_tracks_and_tempo(self):
        song = Song(title="BCN Demo", bpm=123)
        intro = Pattern.preset("Rock")
        intro.set("bass", 0, 40)
        intro.set("guitar", 4, 64)
        intro.set("keys", 8, 60)
        song.capture("Intro", intro)
        song.capture("Verse", intro)
        data = encode_song_midi(song)
        chunks = tracks(data)
        self.assertEqual(len(chunks), 8)
        self.assertIn(b"\xff\x51\x03", chunks[0])
        self.assertIn(bytes([0x99, 36, 108]), chunks[1])  # kick, channel 10
        self.assertIn(bytes([0x90, 64, 96]), chunks[5])  # guitar
        self.assertIn(bytes([0x91, 40, 96]), chunks[6])  # bass
        self.assertIn(bytes([0x92, 60, 96]), chunks[7])  # piano
        for part in chunks:
            self.assertTrue(part.endswith(b"\xff\x2f\x00"))
        with tempfile.TemporaryDirectory() as folder:
            dest = Path(folder) / "song.mid"
            write_song_midi(song, dest)
            self.assertEqual(dest.read_bytes(), data)

    def test_empty_song_refused(self):
        with self.assertRaises(ValueError):
            encode_song_midi(Song())

if __name__ == "__main__":
    unittest.main()
