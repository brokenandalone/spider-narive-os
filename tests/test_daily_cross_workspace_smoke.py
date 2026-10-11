"""Source-only cross-workspace continuity contract for the daily integrated candidate.

Does not import GUI apps, use microphones/cameras, start services or read HOME.
"""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_WIRING = {
    "webbie/agent/webbie.py": (
        "handle_verified_research", "verified_workspace_voice_action",
        "speaker_verified", "is_direct_stop", "quiet_asleep",
        "request_navigation_preview", "voice_permission", "inspect_readiness",
    ),
    "webbie/brain/brain.py": ("private_session_active", "ask_ollama", "remember_turn"),
    "the-web/shell/webbie_computer_panel.py": (
        "open_website", "offer_navigation", "cancel_navigation",
    ),
    "the-web/shell/webbie_panel.py": ("open_cognitive_center", "show_proactive_checks"),
    "study/study.py": (
        "open_assignment_workspace", "open_flashcards", "open_study_progress",
        "open_deep_forage", "open_weekly_planner",
        "open_study_coach", "open_course_readings",
    ),
    "study/store.py": (
        "assignment_record", "add_flashcards", "set_assignment_score",
    ),
    "author/main.py": ("project_map_status", "import_docx", "AuthorWindow", "StoryAtlas"),
    "author/store.py": ("chapter_plan", "import_docx", "AuthorStore"),
    "studio/ai_panel.py": (
        "open_multitrack_session", "open_saved_session_mix", "open_mastering_desk",
    ),
    "studio/main.py": ("BandMixerPanel", "StudioAIPanel", "ReleasePanel"),
    "study/reading_library.py": ("search", "MAX_",),
    "webbie/agent/voice_trust.py": ("voice_permission",),
    "studio/release_export.py": ("export",),
    "author/story_atlas.py": ("timeline",),
    "kali-bay/ui/kali_bay.py": (
        "build_lab_page", "build_guides_page", "start_catalog_load",
        "build_ledger_page", "refresh_evidence_ledger",
        "open_webbie_security",
    ),
    "kali-bay/runtime/evidence_ledger.py": (
        "append_event", "verify_ledger", "MAX_ENTRIES",
    ),
    "kali-bay/package/audit-upgrade.py": (
        "blocked_customized", "safe_for_automatic_replacement",
    ),
    "the-web/shell/main.py": (
        "toggle_command_palette", "open_pinned_slot", "choose_menu_text_size",
    ),
    "forage/engine.py": ("citation_validation_failed", "deep_research"),
    "forage/local_index.py": ("document_text", "configured_roots"),
    "media/ai-dj/nova_host.py": ("Nova",),
}

class DailyCrossWorkspaceSmoke(unittest.TestCase):
    def test_python_syntax_and_critical_entrypoints(self):
        for filename, symbols in REQUIRED_WIRING.items():
            with self.subTest(file=filename):
                path = ROOT / filename
                text = path.read_text(encoding="utf-8")
                ast.parse(text, filename=str(path))
                for symbol in symbols:
                    self.assertIn(symbol, text, f"{filename} lost {symbol}")

    def test_combined_batch_tracks_every_critical_entrypoint(self):
        source = (ROOT / "system/release_batch.py").read_text()
        tree = ast.parse(source)
        entry = next(n for n in tree.body if isinstance(n, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == "APP_FILES"
                             for t in n.targets))
        installed = set(ast.literal_eval(entry.value))
        self.assertTrue(set(REQUIRED_WIRING).issubset(installed))
        self.assertNotIn("study/notes.sqlite", installed)
        self.assertNotIn("webbie/private_memory.db", installed)
        self.assertIn("require_daily_continuity(backup_root)", source)
        self.assertIn("daily_install_guard(backup_root)", source)

    def test_separate_system_installers_are_check_only_in_candidate(self):
        scripts = (
            ("the-web/package/install-desktop.sh", "Per-workspace desktop installation"),
            ("the-web/package/install-author-webbie.sh", "Targeted Author/Webbie installs"),
            ("kali-bay/package/install-kali-bay.sh", "separate Kali Bay"),
        )
        for filename, warning in scripts:
            with self.subTest(file=filename):
                content = (ROOT / filename).read_text()
                self.assertIn(warning, content)
                self.assertIn("exit 3", content)
                self.assertIn("--check", content)

if __name__ == "__main__":
    unittest.main()
