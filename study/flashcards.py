"""Course-local flashcard import and practice with no automatic AI or cloud transfer."""
import csv
from pathlib import Path

MAX_CARDS = 400
MAX_FIELD = 1500
MAX_CSV = 512 * 1024


def normalize_card(front, back):
    if not isinstance(front, str) or not isinstance(back, str):
        raise ValueError("Flashcards must use plain text.")
    front, back = front.strip(), back.strip()
    if not front or not back or len(front) > MAX_FIELD or len(back) > MAX_FIELD:
        raise ValueError("Each flashcard needs a front and back (up to 1,500 characters each).")
    if "\x00" in front or "\x00" in back:
        raise ValueError("Flashcards cannot contain NUL characters.")
    return front, back


def parse_flashcards_csv(filename, existing=()):
    file = Path(filename)
    if file.suffix.lower() != ".csv" or file.is_symlink() or not file.is_file():
        raise ValueError("Select a regular CSV file, not a symbolic link.")
    if file.stat().st_size > MAX_CSV:
        raise ValueError("CSV file exceeds 512 KB.")
    known = {(r["front"].strip().casefold(), r["back"].strip().casefold()) for r in existing}
    cards = []
    skipped = 0
    with file.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = {str(k).strip().casefold(): k for k in (reader.fieldnames or ())}
        first = headers.get("front") or headers.get("question")
        second = headers.get("back") or headers.get("answer")
        if not first or not second:
            raise ValueError("CSV must have Front,Back or Question,Answer columns.")
        for i, row in enumerate(reader, 1):
            if i > MAX_CARDS:
                raise ValueError("CSV contains more than 400 flashcards.")
            if None in row:
                raise ValueError("Flashcard row has extra columns.")
            front, back = normalize_card(row.get(first), row.get(second))
            key = front.casefold(), back.casefold()
            if key in known:
                skipped += 1
            else:
                cards.append((front, back))
                known.add(key)
    return {"cards": cards, "skipped": skipped}


def next_card(cards):
    """Review lowest-scored or oldest cards first; preserve deterministic order."""
    return sorted(cards, key=lambda x: (x["correct"] - x["incorrect"],
                                        x["last_review"] or "", x["id"]))
