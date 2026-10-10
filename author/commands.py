"""Strict, opt-in commands for Webbie's Author Bay.

The parser never executes anything. Unrecognized or vague sentences remain
normal Webbie chat, and every recognized action is read-only until the writer
explicitly approves a separate manuscript edit.
"""
import re


def parse_author_command(value):
    """Return an Author action dictionary for an explicit imperative."""
    if not isinstance(value, str) or len(value) > 600:
        return None
    text = re.sub(r"\s+", " ", value.lower().strip())
    text = re.sub(r"^(?:hey\s+)?webb(?:ie|y)\s*[,!:]?\s*", "", text).strip()
    text = text.rstrip("!.?")
    if not text:
        return None
    # Commands target only the active selection. No guessed book/chapter.
    if re.fullmatch(r"(?:please\s+)?(?:stop|cancel)(?:\s+(?:the|my))?\s+(?:review|reviewing)", text):
        return {"action": "cancel_review"}
    if re.fullmatch(r"(?:please\s+)?(?:pause|resume|continue|stop)(?:\s+(?:the|my))?\s+(?:reading|narration|audiobook)", text):
        verb = re.match(r"(?:please\s+)?(pause|resume|continue|stop)", text).group(1)
        return {"action": "resume_reading" if verb == "continue" else verb + "_reading"}
    review = re.fullmatch(
        r"(?:please\s+)?(?:give\s+me\s+a\s+)?(?:(quick|deep|detailed|full|thorough)\s+)?"
        r"review(?:\s+of)?\s+(?:(?:this|the|my|current|entire|whole)\s+)*"
        r"(chapter|book|manuscript)(?:\s+(?:quickly|in\s+depth))?", text)
    if review:
        qualifier, kind = review.groups()
        return {"action": "review", "scope": "chapter" if kind == "chapter" else "book",
                "depth": "deep" if qualifier in ("deep", "detailed", "thorough", "full")
                or text.endswith("in depth") else "quick"}
    review = re.fullmatch(
        r"(?:please\s+)?review\s+(?:(?:this|the|my|current|entire|whole)\s+)*"
        r"(chapter|book|manuscript)(?:\s+(?:quickly|in\s+depth))?", text)
    if review:
        return {"action": "review", "scope": "chapter" if review.group(1) == "chapter" else "book",
                "depth": "deep" if text.endswith("in depth") else "quick"}
    reading = re.fullmatch(
        r"(?:please\s+)?(?:read|narrate)(?:\s+(?:me|to\s+me|aloud))?\s+"
        r"(?:(?:this|the|my|current|entire|whole)\s+)*(chapter|book|manuscript)"
        r"(?:\s+(?:to\s+me|aloud))?", text)
    if reading:
        return {"action": "read", "scope": "chapter" if reading.group(1) == "chapter" else "book"}
    return None
