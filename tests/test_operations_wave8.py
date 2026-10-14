"""Wave 8 source regressions (tests deferred for installed PC acceptance)."""
from __future__ import annotations
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import wave
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "system"))

from operations_wave8_core import selected_file, selected_folder, term_occurrences
from operations_wave8_studio import production_brief
from operations_wave8_author import continuity_coverage
from operations_wave8_study import rubric_signals
from operations_wave8_research import research_provenance
from operations_wave8_kali import purple_training_plan
from operations_wave8_system import (
    source_snapshot, compare_source_snapshot, backup_folder_inventory,
)
from operations_wave8_webbie import assistant_readiness
from operations_services import SOURCES


class Wave8Quality(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)

    def text(self, filename, content):
        file = self.base / filename
        file.write_text(content, encoding="utf-8")
        return file

    def wav(self, filename, rate=44100):
        file = self.base / filename
        with wave.open(str(file), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(rate)
            stream.writeframes(struct.pack("<" + "h" * 128, *([2000] * 128)))
        return file

    def test_limited_wav_production_brief(self):
        self.wav("bass.wav", 44100)
        self.wav("drums.wav", 48000)
        r = production_brief(self.base)
        self.assertEqual(r["stem_inventory"]["wav_files_inspected"], 2)
        self.assertTrue(r["stem_inventory"]["format_mismatch"])
        self.assertEqual(r["suggested_filename_role_counts"]["bass"], 1)
        self.assertEqual(r["suggested_filename_role_counts"]["drums"], 1)
        self.assertGreater(len(r["review_flags"]), 0)

    def test_canon_coverage_does_not_invent_conflicts(self):
        chapters = self.base / "chapters"
        chapters.mkdir()
        (chapters / "01.md").write_text("Shayna finds the letter.\n", encoding="utf-8")
        (chapters / "02.md").write_text("Daniel meets Shayna.\n", encoding="utf-8")
        canon = self.text("canon.json", json.dumps({"characters": {
            "Shayna Kinser": ["Shayna"],
            "Daniel": ["Daniel"],
            "Kayla": ["Kayla"],
        }}))
        before = (chapters / "01.md").read_bytes()
        report = continuity_coverage(chapters, canon)
        self.assertEqual(report["chapters_inspected"], 2)
        self.assertEqual(report["chapters_containing_each_character"]["Shayna Kinser"], 2)
        self.assertEqual(report["chapters_containing_each_character"]["Kayla"], 0)
        self.assertEqual(before, (chapters / "01.md").read_bytes())

    def test_reject_invalid_alias_list(self):
        chapters = self.base / "chapters"
        chapters.mkdir()
        (chapters / "01.txt").write_text("Text", encoding="utf-8")
        canon = self.text("bad.json", '{"characters":{"Shayna":"not-a-list"}}')
        with self.assertRaises(ValueError):
            continuity_coverage(chapters, canon)

    def test_study_rubric_flags_absent_topic_without_grading(self):
        draft = self.text("draft.md", "Education and society.\nReferences\n")
        rubric = self.text("rubric.md", "# Introduction\n- Cultural stratification\n- Historical context\n")
        report = rubric_signals(draft, rubric)
        self.assertEqual(report["rubric_items_detected"], 3)
        self.assertTrue(report["references_heading_present"])
        self.assertEqual(report["workspace"], "Study")

    def test_sources_out_of_range_and_duplicate(self):
        body = self.text("report.md", "Evidence [1] and [3].")
        sources = self.text("refs.json", json.dumps({"sources": [
            {"title": "A", "url": "https://example.com/a", "published": "2024"},
            {"title": "B", "url": "https://example.com/a", "published": ""},
        ]}))
        r = research_provenance(body, sources)
        self.assertEqual(r["out_of_range_citation_ids"], [3])
        self.assertEqual(r["duplicated_normalized_urls"], 1)
        self.assertEqual(r["uncited_source_entries"], 1)

    def test_kali_training_does_not_execute_tools(self):
        snap = {
            "readiness": {"container_state": "running"},
            "purple_tools": {"state": "running",
                             "tools": {"yara": True, "suricata": True, "zeek": False}},
        }
        r = purple_training_plan(snap)
        self.assertEqual(r["container_state"], "running")
        self.assertEqual(len(r["lessons"]), 5)
        self.assertIn("suricata", r["lessons"][3]["tools_detected"])

    def test_source_baseline_and_changed_file(self):
        root = self.base / "install"
        for rel in SOURCES.values():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("old", encoding="utf-8")
        with patch("operations_wave8_system.system_status", return_value={
            "installed_source_presence": {x: True for x in SOURCES},
            "user_services": {}, "disk_free_gib": 20.0,
        }):
            previous = source_snapshot(root)
            saved = self.text("saved.json", json.dumps(previous))
            rel = root / SOURCES["Webbie"]
            rel.write_text("new", encoding="utf-8")
            comparison = compare_source_snapshot(saved, root)
        self.assertEqual(comparison["changed_source_components"], {"Webbie": "changed"})
        self.assertFalse(comparison["no_changes_detected"])

    def test_refuse_unrecognized_baseline(self):
        saved = self.text("fake.json", '{"schema":"untrusted"}')
        with self.assertRaises(ValueError):
            compare_source_snapshot(saved)

    def test_backup_inventory_is_name_only(self):
        (self.base / "Spider_OS_Consolidated_SAFE_BACKUP_20261013").mkdir()
        (self.base / "My Personal Documents").mkdir()
        r = backup_folder_inventory(self.base)
        self.assertEqual(r["matching_backup_directories"], 1)

    def test_reject_symlinked_source_and_folder(self):
        original = self.text("real.md", "private")
        alias = self.base / "link.md"
        alias.symlink_to(original)
        with self.assertRaises(ValueError):
            selected_file(alias, {".md"})
        target = self.base / "docs"
        target.mkdir()
        linked = self.base / "alias"
        linked.symlink_to(target, target_is_directory=True)
        with self.assertRaises(ValueError):
            selected_folder(linked, {".md"}, 10)

    def test_alias_requires_literal_name_not_regex(self):
        self.assertEqual(term_occurrences("Shayna and Shayna", "Shayna"), 2)
        with self.assertRaises(ValueError):
            term_occurrences("anything", ".*")

    def test_webbie_readiness_does_not_change_or_download_models(self):
        with patch("operations_wave8_webbie.shutil.which", return_value=None):
            report = assistant_readiness(self.base)
        self.assertEqual(report["local_models_advertised"], [])
        self.assertFalse(report["ollama_available"])


if __name__ == "__main__":
    unittest.main()
