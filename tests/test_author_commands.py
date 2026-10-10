"""Fail-closed Author voice/text command and socket integration tests."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "author"))
sys.path.insert(0, str(ROOT / "webbie/agent"))
from PyQt5.QtWidgets import QApplication
from commands import parse_author_command
from commands_client import send_author_command
from control_socket import AuthorCommandServer
from author_voice_bridge import dispatch_verified_author_voice

APP = QApplication.instance() or QApplication([])


class AuthorCommandTests(unittest.TestCase):
    def test_only_explicit_review_or_reading_intents(self):
        expected = {
            "Webbie, review this entire chapter": {
                "action": "review", "scope": "chapter", "depth": "quick"},
            "review the whole book": {
                "action": "review", "scope": "book", "depth": "quick"},
            "give me a deep review of this book": {
                "action": "review", "scope": "book", "depth": "deep"},
            "review this chapter in depth": {
                "action": "review", "scope": "chapter", "depth": "deep"},
            "Webbie read me the book": {"action": "read", "scope": "book"},
            "narrate the entire chapter": {"action": "read", "scope": "chapter"},
            "pause reading": {"action": "pause_reading"},
            "resume narration": {"action": "resume_reading"},
            "stop reading": {"action": "stop_reading"},
            "cancel review": {"action": "cancel_review"},
        }
        for spoken, intent in expected.items():
            with self.subTest(spoken=spoken):
                self.assertEqual(parse_author_command(spoken), intent)
        for vague in ("review", "this book is a review", "can you review someday",
                      "please think about reading", "open Author", "I wrote a chapter"):
            self.assertIsNone(parse_author_command(vague))

    def test_unverified_voice_cannot_send_a_command(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "missing.sock"
            self.assertIn("not verified", send_author_command(
                "read the entire book", source="voice", socket_path=path))
            self.assertIsNone(dispatch_verified_author_voice(
                "review the book", speaker_verified=False,
                workspace="author", root=ROOT / "author"))
            self.assertIsNone(dispatch_verified_author_voice(
                "review the book", speaker_verified=True,
                workspace="studio", root=ROOT / "author"))

    def test_owned_socket_rejects_invalid_messages_and_dispatches_valid_intent(self):
        with tempfile.TemporaryDirectory() as folder:
            socket_path = Path(folder) / "author-control.sock"
            server = AuthorCommandServer(socket_path=socket_path)
            received = []
            server.intentReady.connect(received.append)
            try:
                server.start()
                for _ in range(70):
                    APP.processEvents()
                    if socket_path.is_socket():
                        break
                    time.sleep(0.025)
                self.assertTrue(socket_path.is_socket(), "socket not started")
                reply = send_author_command(
                    "review the whole book", source="typed", socket_path=socket_path)
                self.assertIn("queued", reply)
                for _ in range(30):
                    APP.processEvents()
                    if received:
                        break
                    time.sleep(0.025)
                self.assertEqual(received, [{
                    "action": "review", "scope": "book", "depth": "quick"}])
                self.assertEqual(parse_author_command("Book review thoughts"), None)
            finally:
                server.stop()
                APP.processEvents()

    def test_window_route_only_invokes_requested_action(self):
        from main import AuthorWindow
        with tempfile.TemporaryDirectory() as folder:
            win = AuthorWindow(folder)
            try:
                book = win.store.create_book("Draft book")
                win.store.create_chapter(book, "Opening", "Testing.")
                win.load_books()
                win.books.setCurrentRow(0)
                win.chapters.setCurrentRow(0)
                win.show()
                APP.processEvents()
                with patch.object(win.toolkit, "start_review") as review, (
                    patch.object(win.toolkit, "read_book") as narrate):
                    win.handle_author_intent({
                        "action": "review", "scope": "book", "depth": "deep"})
                    review.assert_called_once_with("book")
                    narrate.assert_not_called()
                    self.assertEqual(win.toolkit.review_depth.currentIndex(), 1)
                    win.handle_author_intent({"action": "read", "scope": "book"})
                    narrate.assert_called_once()
            finally:
                win.close()
                APP.processEvents()


if __name__ == "__main__":
    unittest.main()
