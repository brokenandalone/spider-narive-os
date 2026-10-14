"""Bounded local input helpers for the Spider OS Wave 8 review tools.

No hidden file discovery, recursive crawls, telemetry, network calls, or writes.
"""
from __future__ import annotations
from pathlib import Path
import json
import re

TEXT_SUFFIXES = frozenset({".txt", ".md", ".markdown"})
MAX_TEXT = 2 * 1024 * 1024
MAX_JSON = 8 * 1024 * 1024
WORD = re.compile(r"\b[\w]+(?:['’][\w]+)?\b", re.UNICODE)


def selected_file(path, extensions, max_bytes=MAX_TEXT):
    source = Path(path).expanduser()
    if source.is_symlink() or not source.is_file() or source.suffix.lower() not in extensions:
        raise ValueError("Choose a regular file with the expected extension; symlinks are not accepted.")
    if source.stat().st_size > max_bytes:
        raise ValueError("Selected file is larger than the bounded review limit.")
    return source


def text_file(path):
    return selected_file(path, TEXT_SUFFIXES).read_text(encoding="utf-8-sig")


def json_file(path):
    obj = json.loads(selected_file(path, {".json"}, MAX_JSON).read_text(encoding="utf-8-sig"))
    if not isinstance(obj, dict):
        raise ValueError("Expected a JSON object, not an array or scalar.")
    return obj


def selected_folder(folder, suffixes, max_files):
    directory = Path(folder).expanduser()
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Select an ordinary existing folder, not a symlink.")
    files = []
    for count, item in enumerate(directory.iterdir(), start=1):
        if count > 5000:
            raise ValueError("Selected folder contains too many entries.")
        if item.is_symlink() or not item.is_file():
            continue
        if item.suffix.lower() in suffixes:
            files.append(item)
            if len(files) > max_files:
                raise ValueError("Selected folder exceeds this operation's file count limit.")
    return sorted(files, key=lambda p: p.name.casefold())


def count_words(text):
    return len(WORD.findall(text))


def words(text):
    return {word.casefold() for word in WORD.findall(text)}


def term_occurrences(text, phrase):
    phrase = str(phrase or "").strip()
    if not phrase or len(phrase) > 150:
        raise ValueError("A named term must contain 1 to 150 characters.")
    if not re.fullmatch(r"[\w .'-]+", phrase, re.UNICODE):
        raise ValueError("A named term contains unsupported punctuation.")
    # Case-insensitive literal phrase with Unicode-aware word boundaries.
    return len(re.findall(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text, re.I | re.UNICODE))
