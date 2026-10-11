"""Validated, user-controlled assignment workspace helpers.

Only the owner-supplied content is saved. Sources are never fabricated or
presented as verified citations, and the content never leaves the local PC
unless the owner explicitly asks Webbie to draft or exports a document.
"""
import re

WORK_FIELDS = ("instructions", "rubric", "research", "outline", "draft",
               "references", "feedback")
MAX_FIELD = 120_000
MAX_WEBBIE_CONTEXT = 14_000


def normalized_fields(values):
    if set(values) != set(WORK_FIELDS):
        raise ValueError("The assignment workspace fields are incomplete.")
    result = {}
    for name in WORK_FIELDS:
        value = values[name]
        if not isinstance(value, str):
            raise ValueError("Assignment section " + name + " must be plain text.")
        if len(value) > MAX_FIELD:
            raise ValueError("Assignment section " + name + " exceeds 120,000 characters.")
        if "\x00" in value:
            raise ValueError("Assignment content cannot contain NUL characters.")
        result[name] = value
    return result


def word_count(text):
    return len(re.findall(r"\b[\w'-]+\b", str(text), flags=re.UNICODE))


def readiness_report(values):
    data = normalized_fields(values)
    draft = data["draft"]
    references = [line.strip() for line in data["references"].splitlines() if line.strip()]
    missing = []
    if not data["instructions"].strip():
        missing.append("No assignment instructions saved")
    if not draft.strip():
        missing.append("No draft saved")
    if "[SOURCE NEEDED]" in draft.upper():
        missing.append("Draft contains [SOURCE NEEDED] placeholders")
    if re.search(r"\b(?:https?://\S+|doi:\S+)\b", draft, re.IGNORECASE):
        missing.append("Verify every URL and DOI in your draft")
    if draft.strip() and not references:
        missing.append("References have not been supplied")
    return {
        "words": word_count(draft),
        "reference_lines": len(references),
        "missing": missing,
        "ready_for_review": bool(draft.strip()) and not missing,
    }


def webbie_directions(values):
    """Bound untrusted, explicitly selected coursework text for the AI editor."""
    data = normalized_fields(values)
    result = [data["instructions"].strip()]
    if data["rubric"].strip():
        result.append("ASSIGNMENT RUBRIC (user provided):\n" + data["rubric"].strip())
    instructions = "\n\n".join(x for x in result if x)
    if not instructions:
        raise ValueError("Enter the assignment instructions or rubric before using Webbie.")
    return instructions[:MAX_WEBBIE_CONTEXT]


def webbie_materials(values):
    data = normalized_fields(values)
    result = []
    if data["research"].strip():
        result.append("OWNER NOTES / RESEARCH, UNVERIFIED:\n" + data["research"].strip())
    if data["references"].strip():
        result.append("OWNER-ENTERED REFERENCE STRINGS, VERIFY BEFORE CITING:\n"
                      + data["references"].strip())
    return "\n\n".join(result)[:MAX_WEBBIE_CONTEXT]
