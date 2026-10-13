"""Tests for opt-in, bounded Operations Hub folder inspections.

Keep as source-level tests; not a substitute for owner-PC GUI testing.
"""
import struct
import sys
from pathlib import Path
import tempfile
import unittest
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "system"))
from operations_batch import (
    studio_session_report, author_chapter_folder_report,
    study_assignment_folder_report,
)


class BatchReviews(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

    def _wav(self, name, rate):
        path = self.base / name
        with wave.open(str(path), "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(rate)
            out.writeframes(struct.pack("<" + "h" * 1000, *([1234] * 1000)))
        return path

    def test_studio_flags_different_sample_rates(self):
        self._wav("guitar.wav", 44100)
        self._wav("drums.wav", 48000)
        r = studio_session_report(self.base)
        self.assertEqual(r["wav_files_inspected"], 2)
        self.assertTrue(r["format_mismatch"])
        self.assertEqual(set(r["sample_rates_hz"].keys()), {44100, 48000})

    def test_author_aggregates_without_rewriting(self):
        a = self.base / "01.md"
        b = self.base / "02.txt"
        a.write_text("# Chapter 1\nWords one two.\n", encoding="utf-8")
        b.write_text("Chapter 2\n[TODO] Another scene.\n", encoding="utf-8")
        snapshot = (a.read_bytes(), b.read_bytes())
        r = author_chapter_folder_report(self.base)
        self.assertEqual(r["text_chapters_found"], 2)
        self.assertEqual(r["editorial_placeholders"], 1)
        self.assertEqual((a.read_bytes(), b.read_bytes()), snapshot)

    def test_study_source_placeholders(self):
        (self.base / "draft.md").write_text(
            "Essay text. [SOURCE NEEDED]\nReferences\n", encoding="utf-8"
        )
        r = study_assignment_folder_report(self.base)
        self.assertEqual(r["draft_files_found"], 1)
        self.assertEqual(r["unresolved_source_placeholders"], 1)
        self.assertEqual(r["drafts_with_references_heading"], 1)

    def test_refuses_symlinked_directory(self):
        alias = self.base.parent / (self.base.name + "_alias")
        alias.symlink_to(self.base, target_is_directory=True)
        self.addCleanup(lambda: alias.unlink(missing_ok=True))
        with self.assertRaises(ValueError):
            studio_session_report(alias)

    def test_refuses_too_many_texts(self):
        for index in range(51):
            (self.base / f"{index:02}.txt").write_text("draft", encoding="utf-8")
        with self.assertRaises(ValueError):
            study_assignment_folder_report(self.base)


if __name__ == "__main__":
    unittest.main()
