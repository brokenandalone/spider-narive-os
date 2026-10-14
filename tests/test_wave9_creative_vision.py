"""Wave 9 regression cases. Commit test source, run when owner resumes tests."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "system"))

from wave9_music import SongDraft, render_song
from wave9_visual import analyze_one_frame, camera_inventory, capture_camera_once
from wave9_canon import canon_proposal_review
from wave9_desktop import desktop_continuity


class FakeClient:
    events = []

    def __init__(self, endpoint):
        if endpoint != "http://127.0.0.1:8001":
            raise ValueError("Loopback endpoint required.")
        self.endpoint = endpoint

    def generate(self, request, folder, stop=None, progress=None, **kwargs):
        self.events.append(("generate", str(folder), request.title))
        return Path(folder) / "song-mock-result"


class FakeSong:
    def __init__(self, **kwargs):
        self.title = kwargs["title"]


class FakeCamera:
    def camera_devices(self):
        return ["/dev/video0"]

    def capture_jpeg(self, camera, timeout=12):
        return b"\xff\xd8FRAME\xff\xd9"

    def describe_frame(self, jpeg, prompt="", model="", timeout=90):
        return "A desk and a window; objects may be hard to see."


class Wave9Safety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def write_json(self, name, rows):
        path = self.base / name
        path.write_text(json.dumps({
            "schema": "spider-canon-claims-v1", "claims": rows,
        }), encoding="utf-8")
        return path

    def test_music_requires_manual_render_confirmation(self):
        draft = SongDraft("Original test", "Southern rock",
                          lyrics="Original placeholder lyrics")
        with self.assertRaises(PermissionError):
            render_song(draft, self.base, owner_approved=False)
        self.assertFalse(FakeClient.events)

    def test_music_preview_does_not_contact_engine(self):
        draft = SongDraft("Original test", "Southern rock", instrumental=True)
        with patch("wave9_music._studio_backend", return_value=(FakeClient, FakeSong)):
            result = draft.preview()
        self.assertFalse(result["generation_started"])
        self.assertFalse(FakeClient.events)

    def test_music_render_stays_in_selected_directory(self):
        draft = SongDraft("Original test", "Original style", instrumental=True)
        with patch("wave9_music._studio_backend", return_value=(FakeClient, FakeSong)):
            result = render_song(draft, self.base, owner_approved=True)
        self.assertTrue(result["generation_started"])
        self.assertTrue(str(result["output_job_directory"]).startswith(str(self.base)))
        self.assertEqual(FakeClient.events.pop()[0], "generate")

    def test_render_refuses_symlinked_destination(self):
        draft = SongDraft("Original", "Original style", instrumental=True)
        alias = self.base.parent / (self.base.name + "-alias")
        alias.symlink_to(self.base, target_is_directory=True)
        self.addCleanup(lambda: alias.unlink(missing_ok=True))
        with patch("wave9_music._studio_backend", return_value=(FakeClient, FakeSong)):
            with self.assertRaises(ValueError):
                render_song(draft, alias, owner_approved=True)

    def test_camera_or_screen_requires_fresh_approval(self):
        jpeg = b"\xff\xd8FRAME\xff\xd9"
        with self.assertRaises(PermissionError):
            analyze_one_frame(jpeg, source="screen")
        with self.assertRaises(PermissionError):
            capture_camera_once("/dev/video0")
        with patch("wave9_visual._existing_webbie_camera", return_value=FakeCamera()):
            result = analyze_one_frame(jpeg, user_approved=True, source="screen")
            self.assertFalse(result["image_saved"])
            self.assertEqual(result["source"], "screen")

    def test_camera_capture_is_one_shot(self):
        with patch("wave9_visual._existing_webbie_camera", return_value=FakeCamera()):
            self.assertEqual(camera_inventory()["devices"], ["/dev/video0"])
            result = capture_camera_once("/dev/video0", user_approved=True)
            self.assertEqual(result["source"], "camera")

    def test_author_detects_scoped_value_disagreement_and_source_quote(self):
        chapters = self.base / "chapters"
        chapters.mkdir()
        (chapters / "ch1.md").write_text(
            "Shayna is visiting Redfield.", encoding="utf-8"
        )
        a = self.write_json("canon.json", [{
            "entity": "Shayna", "attribute": "location", "scope": "book_1_ch1",
            "value": "Broken City", "status": "approved"
        }])
        b = self.write_json("proposal.json", [{
            "entity": "Shayna", "attribute": "location", "scope": "book_1_ch1",
            "value": "Redfield", "status": "proposed",
            "source_file": "ch1.md", "source_quote": "visiting Redfield",
        }])
        r = canon_proposal_review(a, b, chapters)
        self.assertEqual(r["candidate_value_disagreements_total"], 1)
        self.assertEqual(r["proposal_source_anchor_results"]["matched"], 1)
        self.assertFalse(r["canon_modified"])

    def test_author_different_time_scope_is_not_marked_conflict(self):
        chapters = self.base / "chapters"
        chapters.mkdir()
        (chapters / "ch1.txt").write_text("Chapter", encoding="utf-8")
        a = self.write_json("canon.json", [{
            "entity": "Shayna", "attribute": "location",
            "scope": "early", "value": "Redfield", "status": "approved",
        }])
        b = self.write_json("proposal.json", [{
            "entity": "Shayna", "attribute": "location",
            "scope": "later", "value": "Broken City", "status": "proposed",
        }])
        result = canon_proposal_review(a, b, chapters)
        self.assertEqual(result["candidate_value_disagreements_total"], 0)

    def test_desktop_audit_does_not_open_shell(self):
        root = self.base / "spider-os"
        apps = self.base / "applications"
        apps.mkdir()
        (root / "the-web/shell").mkdir(parents=True)
        (root / "the-web/shell/main.py").write_text("pass\n")
        from operations_services import WORKSPACES
        for name in ("Studio", "Author", "Study", "Forage", "Deep Forage", "Kali Bay"):
            rel = WORKSPACES[name][0]
            file = root / rel
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text("pass\n")
        (apps / "studio.desktop").write_text(
            "[Desktop Entry]\nType=Application\nName=Studio\n"
            "Exec=/usr/local/lib/spider-os/studio/bin/studio\n", encoding="utf-8"
        )
        result = desktop_continuity(root, apps)
        self.assertTrue(result["workspace_entries"]["studio"]["installed_desktop_entry_found"])
        self.assertFalse(result["workspace_entries"]["studio"]["manual_review_needed"])
        self.assertTrue(result["workspace_entries"]["author"]["manual_review_needed"])


if __name__ == "__main__":
    unittest.main()
