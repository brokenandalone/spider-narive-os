"""Privacy-mode state, redaction and brain behavior regressions."""
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"webbie/brain"))
from privacy_controls import (private_session_active,set_private_session,
                              privacy_explanation)
import brain


class PrivacyTests(unittest.TestCase):
    def setUp(self):
        directory=tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.folder=Path(directory.name)
        self.path=self.folder/"private.json"

    def test_off_by_default(self):
        self.assertFalse(private_session_active(self.path))
        self.assertIn("OFF",privacy_explanation(self.path))

    def test_enable_disable_private_session_owner_only(self):
        set_private_session(True,path=self.path)
        self.assertTrue(private_session_active(self.path))
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode),0o600)
        set_private_session(False,path=self.path)
        self.assertFalse(private_session_active(self.path))

    def test_only_real_boolean(self):
        for enabled in ("true",1,None,0):
            with self.subTest(enabled=enabled),self.assertRaises(ValueError):
                set_private_session(enabled,path=self.path)

    def test_privacy_symlink_denied(self):
        target=self.folder/"data.json"
        target.write_text("safe")
        self.path.symlink_to(target)
        with self.assertRaises(PermissionError):
            set_private_session(True,path=self.path)
        self.assertEqual(target.read_text(),"safe")
        self.assertFalse(private_session_active(self.path))

    def test_world_readable_or_invalid_state_not_trusted(self):
        set_private_session(True,path=self.path)
        os.chmod(self.path,0o644)
        self.assertFalse(private_session_active(self.path))
        os.chmod(self.path,0o600)
        self.path.write_text("{not json")
        self.assertFalse(private_session_active(self.path))

    def test_private_brain_skips_history_recall_and_memory(self):
        with patch.object(brain,"private_session_active",return_value=True):
            self.assertEqual(brain.load_conversation(),[])
            self.assertEqual(brain.recall_memories("family"),[])
            self.assertEqual(brain.recent_memories(),[])
            self.assertFalse(brain.remember_memory("Don't save this"))
            self.assertFalse(brain.maybe_auto_remember("I am a person"))
            with patch.object(brain,"CONVERSATION_FILE",
                              self.folder/"conversation.json") as file:
                brain.remember_turn("secret phrase","secret answer")
                brain.save_conversation([
                    {"role":"user","content":"something private"}])
                self.assertFalse(file.exists())

    def test_private_explicit_memory_request_is_declined(self):
        with patch.object(brain,"private_session_active",return_value=True):
            answer=brain.respond("Remember that I am working on a song")
            self.assertIn("will not save",answer)

    def test_clear_recent_conversation_does_not_touch_longterm(self):
        storage=self.folder/"conversation.json"
        storage.write_text('[{"role":"user","content":"old"}]')
        with patch.object(brain,"CONVERSATION_FILE",storage),patch.object(
                brain,"private_session_active",return_value=True):
            self.assertTrue(brain.clear_conversation())
            self.assertFalse(storage.exists())

if __name__=="__main__":
    unittest.main()
