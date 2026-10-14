"""Wave 8 study rubric checklist. No grades or claim of APA compliance."""
from __future__ import annotations
import re
from operations_wave8_core import count_words, text_file, words

MAX_RUBRIC_ITEMS = 40


def _rubric_items(rubric):
    # Accept only explicit headings and checklist items, not every sentence.
    found = []
    for row in rubric.splitlines()[:600]:
        row = row.strip()
        match = re.match(r"^(?:#{1,4}\s+|[-*]\s+|\d{1,2}[.)]\s+)(.{4,150})$", row)
        if match:
            title = match.group(1).strip()
            if title and title not in found:
                found.append(title)
        if len(found) > MAX_RUBRIC_ITEMS:
            raise ValueError("Rubric has too many checklist items (max 40).")
    return found


def rubric_signals(draft_path, rubric_path):
    draft = text_file(draft_path)
    rubric = text_file(rubric_path)
    items = _rubric_items(rubric)
    if not items:
        raise ValueError("Rubric must contain Markdown headings, bullets or numbered items.")
    draft_terms = words(draft)
    checks = []
    for position, item in enumerate(items, 1):
        key_words = [w for w in re.findall(r"\b[a-zA-Z]{4,}\b", item.casefold())
                     if w not in {"with", "that", "from", "this", "your",
                                  "have", "will", "must", "should", "include"}]
        if not key_words:
            signal = "manual_review"
        else:
            found = sum(word in draft_terms for word in set(key_words))
            signal = ("related_terms_detected" if found else "no_matching_terms_detected")
        checks.append({"rubric_item": position, "topic_match_signal": signal})
    unresolved = len(re.findall(
        r"(?i)\[(?:source needed|citation needed|verify source|todo)\]", draft
    ))
    return {
        "workspace": "Study",
        "mode": "read_only",
        "operation": "rubric_signals",
        "draft_approximate_words": count_words(draft),
        "rubric_items_detected": len(items),
        "rubric_topic_signals": checks,
        "unresolved_source_markers": unresolved,
        "references_heading_present": bool(re.search(
            r"(?im)^\s*(?:#{1,3}\s+)?references\s*$", draft
        )),
        "note": "Keyword overlap cannot determine whether a requirement is met, "
                "whether a citation exists, or whether work is ready for submission.",
    }
