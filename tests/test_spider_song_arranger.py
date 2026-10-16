"""No-device regression tests for Spider Audio Studio's multibar arrangements."""
import json
from pathlib import Path
import tempfile
import unittest
import wave

from studio.instruments_engine import Pattern, TRACKS
from studio.song_arranger_engine import (
    MAX_BARS, Song, Channel, Bar, render_song_chunks, song_duration,
    write_song_wav, export_stems, save_song, load_song,
)

class SongArrangementTests(unittest.TestCase):
    def make_song(self):
        song = Song(title="Spider Test", bpm=120)
        song.capture("Intro", Pattern.preset("Rock"))
        song.capture("Verse", Pattern.preset("Four on the floor"))
        second = song.bars[1].pattern
        second.set("guitar", 0, 52)
        second.set("bass", 0, 40)
        second.set("keys", 8, 60)
        return song

    def test_capture_is_independent_and_roundtrips(self):
        source = Pattern.preset("Rock")
        song = Song(bpm=110)
        song.capture("Verse", source)
        source.set("bass", 0, 40)
        self.assertIsNone(song.bars[0].pattern.events["bass"][0])
        song.mixer["guitar"].pan = 100
        song.mixer["keys"].mute = True
        rebuilt = Song.from_dict(json.loads(json.dumps(song.as_dict())))
        self.assertEqual(rebuilt.as_dict(), song.as_dict())
        self.assertEqual(rebuilt.mixer["guitar"].pan, 100)

    def test_reject_invalid_documents_before_rendering(self):
        data = self.make_song().as_dict()
        mutations = [
            lambda d: d.update(bpm=True),
            lambda d: d.update(title=""),
            lambda d: d["mixer"]["kick"].update(gain=101),
            lambda d: d["mixer"]["kick"].update(solo="false"),
            lambda d: d["mixer"]["bass"].update(pan=-101),
            lambda d: d["bars"][0].update(name=""),
            lambda d: d["bars"][0]["pattern"]["events"]["kick"].__setitem__(0, "x"),
            lambda d: d["bars"].extend([d["bars"][0]] * MAX_BARS),
        ]
        for mutation in mutations:
            corrupted = json.loads(json.dumps(data))
            mutation(corrupted)
            with self.subTest(mutation=str(mutation)):
                with self.assertRaises(ValueError):
                    Song.from_dict(corrupted)

    def test_two_bar_stereo_export_accurate_length(self):
        song = self.make_song()
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "song.wav"
            write_song_wav(song, file, rate=8000)
            with wave.open(str(file), "rb") as wav:
                self.assertEqual(wav.getnchannels(), 2)
                self.assertEqual(wav.getsampwidth(), 2)
                self.assertEqual(wav.getframerate(), 8000)
                self.assertEqual(wav.getnframes(), 8000 * 4)
                self.assertTrue(any(wav.readframes(8000)))
            self.assertAlmostEqual(song_duration(song), 4.0)

    def test_silence_mute_solo_and_panning(self):
        song = Song(bpm=120)
        source = Pattern()
        source.set("keys", 0, 60)
        song.capture("Piano", source)
        song.mixer["keys"].pan = -100
        audio = b"".join(render_song_chunks(song, rate=8000))
        # Hard left is silent on right, non-silent on left.
        from array import array
        import sys
        pcm = array("h"); pcm.frombytes(audio)
        if sys.byteorder != "little": pcm.byteswap()
        self.assertTrue(any(pcm[::2]))
        self.assertFalse(any(pcm[1::2]))
        song.mixer["keys"].mute = True
        muted = b"".join(render_song_chunks(song, rate=8000))
        self.assertFalse(any(muted))
        song.mixer["keys"].mute = False
        song.mixer["kick"].solo = True
        soloed = b"".join(render_song_chunks(song, rate=8000))
        self.assertFalse(any(soloed))

    def test_stems_and_saved_project(self):
        song = Song(bpm=240)
        pattern = Pattern()
        pattern.set("hat", 0)
        pattern.set("guitar", 0, 52)
        song.capture("Demo", pattern)
        with tempfile.TemporaryDirectory() as folder:
            place = Path(folder)
            name = place / "project.spider-song.json"
            save_song(song, name)
            self.assertEqual(load_song(name).as_dict(), song.as_dict())
            stems = export_stems(song, place, rate=8000)
            self.assertEqual(len(stems), len(TRACKS))
            for filename in stems:
                with wave.open(str(filename), "rb") as f:
                    self.assertEqual(f.getnframes(), 8000)
            with self.assertRaises(FileExistsError):
                export_stems(song, place, rate=8000)

if __name__ == "__main__":
    unittest.main()
