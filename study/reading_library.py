"""Explicit, private course-reading imports and excerpt search for Spider OS.

No directory scans, network requests, background indexing or automatic
Webbie transfer. Files are copied, never moved; user originals are untouched.
The indexed text is explicitly bounded. Only TXT, MD, DOCX and text PDF work.
"""
import hashlib
import os
from pathlib import Path
import re

try:
    from .reading_passages import MAX_EXTRACTED, split_reading_passages
except ImportError:
    from reading_passages import MAX_EXTRACTED, split_reading_passages

try:
    from .course_materials import read_course_document, SUPPORTED, MAX_FILE_BYTES
except ImportError:
    from course_materials import read_course_document, SUPPORTED, MAX_FILE_BYTES

MAX_INDEXED_TEXT = 12000
MAX_QUERY = 180
MAX_RESULTS = 30


def safe_reading_name(filename):
    name = Path(str(filename)).name
    if (not name or name in (".", "..") or len(name) > 180
            or any(ord(c) < 32 for c in name)
            or "\\" in name or ":" in name or "/" in name
            or name.startswith(".")):
        raise ValueError("Choose a regular, clearly named document.")
    if Path(name).suffix.lower() not in SUPPORTED:
        raise ValueError("Only TXT, Markdown, DOCX or text PDFs are supported.")
    return name


def file_digest(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while True:
            chunk = stream.read(131072)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def import_course_reading(store, course_id, chosen_path):
    """Create a *new* local copy and index; never overwrite an existing file."""
    course = store.course(course_id)
    if course is None:
        raise ValueError("Select a valid existing course.")
    original = Path(chosen_path)
    name = safe_reading_name(original.name)
    if original.is_symlink() or not original.is_file():
        raise ValueError("Choose an existing regular reading, not a symbolic link.")
    if original.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("Document exceeds the 8 MB reader limit.")
    # Parse before writing anything, including scanned/image-only PDFs.
    extracted = read_course_document(original, max_chars=MAX_EXTRACTED)
    passages = split_reading_passages(extracted)
    excerpt = extracted[:MAX_INDEXED_TEXT]
    checksum = file_digest(original)
    if store.find_course_reading_by_hash(course_id, checksum) is not None:
        return {"created": False, "name": name, "reason": "identical reading already indexed"}
    root = store.course_folder(course_id) / "Readings"
    if root.is_symlink():
        raise ValueError("Course Readings directory cannot be a symbolic link.")
    root.mkdir(parents=True, exist_ok=True)
    if root.is_symlink():
        raise ValueError("Course Readings directory must be a real folder.")
    if not root.resolve().is_relative_to(store.course_folder(course_id).resolve()):
        raise ValueError("Unsafe course reading destination.")
    stem, extension = Path(name).stem, Path(name).suffix.lower()
    copied = None
    for index in range(1, 101):
        suffix = "" if index == 1 else f"-{index}"
        candidate = root / (stem + suffix + extension)
        try:
            # Exclusive create, private mode and no overwrite even in a race.
            with candidate.open("xb") as output:
                os.fchmod(output.fileno(), 0o600)
                with original.open("rb") as source:
                    while True:
                        block = source.read(131072)
                        if not block:
                            break
                        output.write(block)
                    output.flush()
                    os.fsync(output.fileno())
            copied = candidate
            break
        except FileExistsError:
            continue
        except Exception:
            candidate.unlink(missing_ok=True)  # Remove incomplete new copies.
            raise
    if copied is None:
        raise ValueError("Too many similarly named readings; choose a different filename.")
    try:
        if file_digest(copied) != checksum:
            raise ValueError("Document changed during copy; index was not saved.")
        relative = "Readings/" + copied.name
        created = store.add_course_reading(
            course_id, name, relative, checksum, excerpt[:MAX_INDEXED_TEXT],
            passages=passages)
        if not created:
            copied.unlink(missing_ok=True)
            return {"created": False, "name": name, "reason": "reading already indexed"}
        return {"created": True, "name": name, "location": str(copied)}
    except Exception:
        copied.unlink(missing_ok=True)
        raise


def find_course_excerpts(rows, phrase):
    """Search only indexed owner-selected readings with simple scoring."""
    phrase = str(phrase).strip()
    if not phrase or len(phrase) > MAX_QUERY or "\x00" in phrase:
        raise ValueError("Enter a search phrase of 1 to 180 characters.")
    words = list(dict.fromkeys(re.findall(r"[\w'-]{2,}", phrase.casefold())))[:16]
    if not words:
        raise ValueError("Search requires a word with at least two characters.")
    results = []
    for row in rows:
        text = str(row["excerpt"])
        lower = text.casefold()
        term_hits = sum(lower.count(word) for word in words)
        title_hits = sum(str(row["title"]).casefold().count(word) for word in words)
        if not term_hits and not title_hits:
            continue
        positions = [lower.find(word) for word in words if word in lower]
        position = min(positions) if positions else 0
        start = max(0, position - 170)
        snippet = text[start:start + 650].strip()
        results.append({
            "id": row["id"], "title": row["title"],
            "snippet": ("…" if start else "") + snippet +
                       ("…" if start + 650 < len(text) else ""),
            "score": term_hits + title_hits * 4,
        })
    results.sort(key=lambda x: (-x["score"], x["title"].casefold(), x["id"]))
    return results[:MAX_RESULTS]


def selected_reading_excerpt(row, *, limit=9000):
    """Clearly label user-selected, unverified educational material."""
    if not row or not 500 <= limit <= 12000:
        raise ValueError("Choose a valid reading and excerpt size.")
    text = str(row["excerpt"])[:limit]
    if not text.strip():
        raise ValueError("This reading contains no indexed text.")
    return ("OWNER-SELECTED LOCAL COURSE READING: " + str(row["title"]) +
            "\nThis is a text excerpt, NOT a verified reference or complete chapter.\n" +
            text)



def reindex_course_reading(store, course_id, reading_id):
    """Owner-triggered expansion of an earlier 12K-only reading.

    The copied file must still have its original SHA-256 checksum. A failed
    reindex does not modify the existing record or its previous text.
    """
    row = store.course_reading(course_id, reading_id)
    if row is None:
        raise ValueError("The selected reading was not found in this course.")
    course = store.course_folder(course_id)
    relative = str(row["relative_path"])
    parts = Path(relative).parts
    if (len(parts) != 2 or parts[0] != "Readings"
            or parts[1] in ("", ".", "..")):
        raise ValueError("Invalid original reading path.")
    file = course / relative
    if (file.is_symlink() or not file.is_file()
            or not file.resolve().is_relative_to(course.resolve())):
        raise ValueError("The saved reading file is unavailable or unsafe.")
    checksum = file_digest(file)
    if checksum != row["sha256"]:
        raise ValueError("The reading file changed since import. Reimport deliberately.")
    if store.reading_passages(course_id, reading_id):
        return {"updated": False, "reason": "passages already indexed"}
    extracted = read_course_document(file, max_chars=MAX_EXTRACTED)
    chunks = split_reading_passages(extracted)
    store.update_reading_passages(course_id, reading_id, checksum, chunks)
    return {"updated": True, "passages": len(chunks)}
