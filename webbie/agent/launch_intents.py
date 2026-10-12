"""Literal direct-owner workspace launch intent, not keyword guessing.

Only a complete addressed request can signal a launch. This parser NEVER
starts programs or approves GUI grants. Other sentences (including quoted
text, negations, TV/transcript noise and LLM output) are just conversation.
"""
from __future__ import annotations
import re

TARGETS={
    "the web":"web", "web":"web",
    "deep forage":"deep-forage", "forage":"forage",
    "kali bay":"kali-bay", "media":"media",
    "spider media center":"media","media center":"media",
    "study":"study","spider study":"study",
    "studio":"studio","spider studio":"studio",
    "terminal":"terminal", "konsole":"terminal",
    "system settings":"settings","settings":"settings",
}
DIRECT=re.compile(
    r"^\s*(?:(?:hey\s+)?(?:webbie|webby|web)\s*[,.:]?\s+)?"
    r"(?:please\s+)?(?:open|launch|start|enter)\s+"
    r"(?P<target>[a-z][a-z ]{0,50})[.!?]?\s*$",
    re.I,
)


def direct_launch_intent(message):
    if not isinstance(message,str) or len(message)>130:
        return None
    result=DIRECT.fullmatch(message.strip())
    if result is None:
        return None
    target=" ".join(result.group("target").lower().split())
    return TARGETS.get(target)
