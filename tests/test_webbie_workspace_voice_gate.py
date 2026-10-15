"""Offline verified-workspace voice authorization contract.

Isolate the single small dispatcher AST; never import or start the resident
Webbie process, microphone, graphical desktop or any Kali tools.
"""
import ast
import inspect
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "webbie/agent/webbie.py"


def dispatcher(verified_workspace="author", sleeping=False):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    chosen = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "verified_workspace_voice_action"
    )
    isolated = ast.Module(body=[chosen], type_ignores=[])
    ast.fix_missing_locations(isolated)
    local = {
        "quiet_asleep": lambda: sleeping,
        "current_workspace": lambda: verified_workspace,
    }
    exec(compile(isolated, str(SOURCE), "exec"), local)
    return local["verified_workspace_voice_action"]


class SpeakerVerifiedRoutes(unittest.TestCase):
    def test_unverified_voice_cannot_dispatch(self):
        action = dispatcher()
        author = types.ModuleType("author_voice_bridge")
        author.dispatch_verified_author_voice = Mock()
        kali = types.ModuleType("kali_assistant")
        kali.handle_kali_request = Mock()
        with patch.dict(sys.modules, {
            "author_voice_bridge": author, "kali_assistant": kali
        }):
            self.assertIsNone(action("read my book"))
            self.assertIsNone(action("open Wireshark", workspace="kali-bay"))
        author.dispatch_verified_author_voice.assert_not_called()
        kali.handle_kali_request.assert_not_called()

    def test_sleep_prevents_even_verified_dispatch(self):
        action = dispatcher(sleeping=True)
        self.assertIsNone(action("read my book", speaker_verified=True))

    def test_author_requires_explicit_external_voice_proof(self):
        action = dispatcher(verified_workspace="author")
        author = types.ModuleType("author_voice_bridge")
        author.dispatch_verified_author_voice = Mock(return_value="Author answer")
        with patch.dict(sys.modules, {"author_voice_bridge": author}):
            self.assertEqual(
                action("read my chapter", speaker_verified=True), "Author answer")
        author.dispatch_verified_author_voice.assert_called_once_with(
            "read my chapter", speaker_verified=True, workspace="author")

    def test_kali_is_allowlisted_bridge_only_and_only_when_verified(self):
        action = dispatcher(verified_workspace="kali-bay")
        kali = types.ModuleType("kali_assistant")
        kali.handle_kali_request = Mock(return_value="Tool menu opened")
        with patch.dict(sys.modules, {"kali_assistant": kali}):
            self.assertEqual(
                action("open Wireshark", speaker_verified=True),
                "Tool menu opened")
        kali.handle_kali_request.assert_called_once_with("open Wireshark")

    def test_no_routing_outside_author_and_kali(self):
        self.assertIsNone(
            dispatcher(verified_workspace="study")(
                "open a tool", speaker_verified=True
            )
        )

    def test_all_existing_agent_callers_default_unverified(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        handler = next(node for node in tree.body
                       if isinstance(node, ast.FunctionDef)
                       and node.name == "handle_command")
        named = [arg.arg for arg in handler.args.args]
        last = handler.args.defaults[-1]
        self.assertEqual(named[-1], "speaker_verified")
        self.assertIs(ast.literal_eval(last), False)


if __name__ == "__main__":
    unittest.main()
