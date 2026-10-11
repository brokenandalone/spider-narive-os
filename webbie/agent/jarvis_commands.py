"""Webbie Jarvis command reference; grounded in features actually implemented.

This is a SOURCE capability guide, not an assertion that a GitHub feature is
already installed, active, or functional on the owner's customized PC.
"""
from __future__ import annotations
import re

REQUESTS = frozenset({
    "help", "what can you do", "what can you control", "what are your abilities",
    "show me your commands", "jarvis help", "webbie help",
    "how do i use computer control", "what commands can i say",
    "what can webbie do", "how can you help me on my computer",
})

def is_capability_question(text):
    if not isinstance(text, str):
        return False
    clean = re.sub(r"\s+", " ", str(text).lower().strip(" ?.!"))
    clean = re.sub(r"^(?:hey\s+)?(?:webbie|webby|web)[\s,.:]+", "", clean)
    return clean in REQUESTS

def voice_guide():
    return (
        "In this Spider OS source, I can discuss your current workspace and "
        "approved task, propose website openings and searches, stage reviewed "
        "navigation missions, and report system checks. Open Computer Control "
        "to approve specific apps, windows and each navigation step. "
        "I do not have unrestricted hands-free computer access or verified "
        "speaker identity yet."
    )

def gui_guide():
    return (
        "JARVIS COMMANDS (available in this source build)\n\n"
        "WEBSITES\n"
        "  Webbie, open github.com\n"
        "  Webbie, open YouTube\n"
        "  Webbie, search the web for guitar recording tutorials\n"
        "  Each address requires approved browser control and confirmation.\n\n"
        "YOUR CONTEXT\n"
        "  Webbie, what am I working on?\n"
        "  Webbie, what workspace am I in?\n"
        "  Webbie, what step are we on?\n"
        "  Context requires The Web and expires automatically.\n\n"
        "SUPERVISED NAVIGATION\n"
        "  Webbie, scroll down twice\n"
        "  Webbie, next tab then go back\n"
        "  Webbie, refresh page\n"
        "  Speech or text only proposes steps. Bind a window, review and "
        "click Run Next Reviewed Step for each one. STOP cancels.\n\n"
        "LOCAL HELPERS\n"
        "  Webbie, proactive status\n"
        "  My local reminders: use the Webbie panel.\n"
        "  Webbie STOP, sleep and wake controls.\n\n"
        "PRIVACY AND LIMITATIONS\n"
        "  Live screen snapshots require explicit window approval; camera "
        "observations require separate camera consent. Speaker recognition "
        "does not prove Cory or Shayna has authorized a task. Remote control, "
        "automated credential entry and unrestricted Jarvis-style hands-free "
        "actions are NOT implemented here. Passing GitHub tests does not mean "
        "these source features have been installed on your PC."
    )
