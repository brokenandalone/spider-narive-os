"""Explicit verified-speaker Webbie -> Deep Forage UI bridge.

A recognized wake phrase is NOT speaker verification.  This bridge defaults
to denying voice actions until the PC provides a separate trusted signal.
"""
import importlib.util
from pathlib import Path
import re
import subprocess
import sys

APP_ROOT = Path("/usr/local/lib/spider-os")


def voice_research_request(text):
    value = " ".join(str(text or "").split())
    patterns = (
        r"^(?:please )?(?:start|open|launch) deep forage (?:research )?(?:on|about|for) (.+)$",
        r"^(?:please )?(?:research|investigate) (.+) (?:with|in|using) deep forage$",
    )
    for pattern in patterns:
        found = re.fullmatch(pattern, value, flags=re.I)
        if found:
            topic = found.group(1).strip()
            if 3 <= len(topic) <= 600:
                return ("open", topic)
    if re.fullmatch(r"(?:show|list|read) (?:my )?(?:deep forage |forage )?(?:research )?history", value, re.I):
        return ("history", None)
    if re.fullmatch(r"what (?:has |did )?deep forage (?:research|find|finish)(?: recently)?\??", value, re.I):
        return ("history", None)
    return None


def handle_verified_research(text, *, speaker_verified=False, asleep=False,
                             root=APP_ROOT, launcher=None):
    """Returns None when not a recognized/authorized research command.

    Does not execute model-generated shell commands, fetch data, run deep
    research invisibly, or publish source text into general conversation.
    """
    request = voice_research_request(text)
    if request is None or speaker_verified is not True or asleep:
        return None
    action, topic = request
    source = Path(root) / "forage"
    if action == "open":
        script = source / "deep-forage" / "deep_forage.py"
        if not script.is_file() or script.is_symlink():
            return "Deep Forage is not installed at the expected safe location."
        launch = launcher or subprocess.Popen
        launch([sys.executable, str(script), topic], start_new_session=True)
        return f"Deep Forage is open with the question: {topic}. Select Begin Research in its window."
    archive = source / "research_archive.py"
    if not archive.is_file() or archive.is_symlink():
        return "The Deep Forage history module is unavailable."
    # Imported directly from the selected Spider OS source. No arbitrary
    # plugin path, cwd or user transcript interpolation is involved.
    spec = importlib.util.spec_from_file_location("spider_forage_archive_voice", archive)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    folder = Path.home() / "Documents" / "Spider OS" / "Forage" / "Research"
    records = module.list_reports(folder, limit=5)
    if not records:
        return "No saved Deep Forage research reports were found."
    entries = [f"{r['title']} ({r['evidence_status']})" for r in records]
    return "Recent Deep Forage saved reports: " + "; ".join(entries) + "."
