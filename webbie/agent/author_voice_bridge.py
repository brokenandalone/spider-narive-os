"""Optional bridge called only AFTER Webbie's trusted voice-gate succeeds.

Never infer speaker identity from ASR text, webcam recognition, wake words
or the fact that the microphone captured a phrase.
"""
import sys
from pathlib import Path


def dispatch_verified_author_voice(transcript, *, speaker_verified=False,
                                   workspace="", root=None):
    if not speaker_verified or str(workspace).lower() != "author":
        return None
    author_root = (Path(root) if root is not None
                   else Path(__file__).resolve().parents[2] / "author")
    if not (author_root / "commands_client.py").is_file():
        return "Author Bay command bridge is not installed."
    if str(author_root) not in sys.path:
        sys.path.insert(0, str(author_root))
    from commands_client import send_author_command
    return send_author_command(str(transcript), source="voice",
                               speaker_verified=True)
