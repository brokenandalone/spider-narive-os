"""End-to-end read-only smoke checks for all vendored MAX workspace engines.

This checks the actual native-bay library backend, without a MAX launcher.
"""
from __future__ import annotations

import hashlib
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "spider_max_source"))
from spider_monster.max_catalog import WORKSPACES, run
from spider_monster.max_board import WorkspaceBoard

SAMPLES = {
    "Webbie": "knowledge-inventory",
    "The Web": "launcher-catalog",
    "Studio": "session-inventory",
    "Media Center": "catalog-overview",
    "BCN / Nova": "radio-catalog",
    "Author": "chapter-atlas",
    "Study": "course-map",
    "Art Lab": "gallery",
    "Forage": "document-corpus",
    "Kali Bay": "evidence-manifest",
    "Dev Bay": "repository-map",
    "Recovery": "private-file-inventory",
    "Communications": "draft-catalog",
    "System": "config-inventory",
    "Backups": "backup-inventory",
}


class VendoredNativeOperations(unittest.TestCase):
    def test_all_137_actions_retained_in_fifteen_workspaces(self):
        self.assertEqual(set(WORKSPACES), set(SAMPLES))
        self.assertEqual(sum(len(module.ACTIONS) for module in WORKSPACES.values()), 137)

    def test_every_workspace_produces_a_read_only_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / "scene.txt").write_text("Shayna enters Apartment 17.", encoding="utf-8")
            (root / "track.wav").write_bytes(b"RIFF")
            (root / "image.png").write_bytes(b"\\x89PNG\\r\\n\\x1a\\n")
            before = {x.name: hashlib.sha256(x.read_bytes()).hexdigest()
                      for x in root.iterdir() if x.is_file()}
            for workspace, operation in SAMPLES.items():
                with self.subTest(workspace=workspace):
                    result = run(workspace, operation, directory, "")
                    self.assertEqual(result["workspace"], workspace)
                    self.assertEqual(result["operation"], operation)
                    self.assertIs(result["read_only"], True)
            after = {x.name: hashlib.sha256(x.read_bytes()).hexdigest()
                     for x in root.iterdir() if x.is_file()}
            self.assertEqual(before, after)

    def test_board_persists_in_native_workspace_format(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "board.sqlite3"
            with WorkspaceBoard(path) as board:
                uid = board.add("Author", "Check Platform Six", "Continuity review", "task")
            with WorkspaceBoard(path) as board:
                self.assertEqual(board.list("Author")[0]["title"], "Check Platform Six")
                board.set_status(uid, "done")
                self.assertEqual(board.list("Author")[0]["status"], "done")


if __name__ == "__main__":
    unittest.main()
