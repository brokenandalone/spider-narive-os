"""Local, provenance-preserving Study passage index.

Passage numbers are extraction order, NOT PDF page numbers, citations or
bibliographic references. Webbie receives text only after owner confirmation.
"""
import re

MAX_EXTRACTED = 240000
PASSAGE_LENGTH = 3200
PASSAGE_OVERLAP = 220
MAX_PASSAGES = 90
MAX_SEARCH = 180


def split_reading_passages(text, *, length=PASSAGE_LENGTH, overlap=PASSAGE_OVERLAP):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("A readable document is required.")
    if len(text) > MAX_EXTRACTED:
        raise ValueError("Extracted document exceeds the 240,000 character index limit.")
    if not (500 <= length <= 5000 and 0 <= overlap < length // 2):
        raise ValueError("Invalid passage size or overlap.")
    pieces = []
    start = 0
    while start < len(text):
        end = min(len(text), start + length)
        part = text[start:end]
        if part.strip():
            pieces.append((len(pieces) + 1, start, end, part))
        if len(pieces) > MAX_PASSAGES:
            raise ValueError("Document would require too many passages.")
        if end == len(text):
            break
        start = end - overlap
    return pieces


def _search_words(phrase):
    if not isinstance(phrase, str) or not 1 <= len(phrase.strip()) <= MAX_SEARCH:
        raise ValueError("Enter a search query up to 180 characters.")
    words = list(dict.fromkeys(re.findall(r"[\w'-]{2,}", phrase.casefold())))[:16]
    if not words:
        raise ValueError("Use at least one search word of two characters.")
    return words


def search_reading_passages(rows, phrase, *, max_results=35):
    """Score passage hits, keeping names, passage numbers and character offsets."""
    words = _search_words(phrase)
    if not 1 <= max_results <= 50:
        raise ValueError("Search limit must be 1 to 50.")
    ranked = []
    for row in rows:
        body = str(row["body"])
        lower = body.casefold()
        title = str(row["title"]).casefold()
        occurrences = sum(lower.count(word) for word in words)
        title_hits = sum(title.count(word) for word in words)
        if not occurrences and not title_hits:
            continue
        found = [lower.find(word) for word in words if word in lower]
        at = min(found) if found else 0
        left = max(0, at - 170)
        snippet = body[left:left+650].strip()
        ranked.append({
            "id": row["reading_id"],
            "title": row["title"],
            "passage_index": int(row["passage_index"]),
            "start_char": int(row["start_char"]),
            "end_char": int(row["end_char"]),
            "snippet": ("…" if left else "") + snippet +
                       ("…" if left + 650 < len(body) else ""),
            "score": occurrences + title_hits * 2,
        })
    ranked.sort(key=lambda x: (-x["score"], x["title"].casefold(),
                               x["passage_index"], x["id"]))
    return ranked[:max_results]


def selected_passage_text(reading, passage):
    if not reading or not passage or passage["reading_id"] != reading["id"]:
        raise ValueError("The chosen passage does not belong to that reading.")
    body = passage["body"]
    if not isinstance(body, str) or not body.strip() or len(body) > 5000:
        raise ValueError("Passage cannot be empty or oversized.")
    return (
        "OWNER-SELECTED COURSE READING PASSAGE\n"
        "Reading filename: " + str(reading["title"])[:180] + "\n"
        "Local extraction passage: " + str(passage["passage_index"]) + "\n"
        "Extracted character range: " + str(passage["start_char"]) + "-"
        + str(passage["end_char"]) + "\n"
        "This is unverified educational material. Passage numbers are NOT "
        "book or PDF page numbers. No bibliographic citation is implied.\n"
        "PASSAGE TEXT:\n" + body
    )
