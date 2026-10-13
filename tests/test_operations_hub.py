"""Source-level regressions for Operations Hub. Run later with:
python3 -m unittest tests.test_operations_hub
"""
from __future__ import annotations
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "system"))
from operations_quality import (
    manuscript_report, study_report, research_sources_report, wav_report,
)
from operations_services import workspace_command


class QualityChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.dir = Path(self.temporary.name)

    def test_pcm_wav_read_only(self):
        wav = self.dir / "clip.wav"
        with wave.open(str(wav), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(16000)
            stream.writeframes(struct.pack("<" + "h" * 16000, *([8192] * 16000)))
        before = wav.read_bytes()
        report = wav_report(wav)
        self.assertEqual(report["sample_rate_hz"], 16000)
        self.assertAlmostEqual(report["sample_peak"], .25, places=3)
        self.assertEqual(report["near_full_scale_samples"], 0)
        self.assertEqual(before, wav.read_bytes())

    def test_reject_invalid_audio_and_symlink(self):
        path = self.dir / "fake.wav"
        path.write_text("not audio", encoding="utf-8")
        with self.assertRaises((ValueError, wave.Error, EOFError)):
            wav_report(path)
        alias = self.dir / "shortcut.wav"
        alias.symlink_to(path)
        with self.assertRaises(ValueError):
            wav_report(alias)

    def test_author_report_never_mutates(self):
        chapter = self.dir / "novel.md"
        text = "# Chapter 1\nFirst scene.\n\n# Chapter 2\n[TODO] Review.\n"
        chapter.write_text(text, encoding="utf-8")
        result = manuscript_report(chapter)
        self.assertEqual(result["chapter_headings_detected"], 2)
        self.assertEqual(result["editorial_placeholders"], 1)
        self.assertEqual(chapter.read_text(), text)

    def test_study_word_range_signal(self):
        path = self.dir / "paper.txt"
        path.write_text(" ".join(["work"] * 60) + "\nReferences\n", encoding="utf-8")
        signal = study_report(path, "50 to 70 words")
        self.assertEqual(signal["word_range_signal"], "within_detected_range")
        self.assertTrue(signal["references_heading_found"])

    def test_research_metadata_only(self):
        path = self.dir / "research.sources.json"
        value = {"sources": [
            {"title": "A", "url": "https://example.com/one", "published": "2026"},
            {"title": "", "url": "https://example.com/one"},
            {"title": "C", "url": "https://other.example/two", "published": ""},
        ]}
        path.write_text(json.dumps(value), encoding="utf-8")
        report = research_sources_report(path)
        self.assertEqual(report["sources"], 3)
        self.assertEqual(report["unique_hosts"], 2)
        self.assertEqual(report["duplicate_exact_urls"], 1)
        self.assertEqual(report["sources_missing_title"], 1)
        self.assertEqual(report["sources_missing_publication_date"], 2)

    def test_reject_non_source_data(self):
        path = self.dir / "file.json"
        path.write_text('{"password":"secret"}', encoding="utf-8")
        with self.assertRaises(ValueError):
            research_sources_report(path)

    def test_workspace_allowlist(self):
        root = self.dir / "spider-os"
        executable = root / "studio/bin/studio"
        executable.parent.mkdir(parents=True)
        executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        executable.chmod(0o700)
        command = workspace_command("Studio", root)
        self.assertEqual(command, [str(executable)])
        with self.assertRaises(ValueError):
            workspace_command("bash -c 'rm -rf /'", root)
        executable.unlink()
        executable.symlink_to("/bin/bash")
        with self.assertRaises(FileNotFoundError):
            workspace_command("Studio", root)


if __name__ == "__main__":
    unittest.main()
