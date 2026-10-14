"""Explicit, read-only Broken World/Author term coverage review.

Never assert invented lore, alter canon or treat missing names as contradictions.
"""
from __future__ import annotations
from operations_wave8_core import (
    MAX_TEXT, count_words, json_file, selected_folder, term_occurrences,
)

CANON_LIMIT = 80
ALIAS_LIMIT = 12


def continuity_coverage(chapter_folder, canon_path):
    """User selects an explicit character-name JSON map and a text chapter folder.

    Example: {"characters":{"Shayna Kinser":["Shayna","Shayna Kinser"]}}
    """
    source = json_file(canon_path)
    characters = source.get("characters")
    if not isinstance(characters, dict) or not 1 <= len(characters) <= CANON_LIMIT:
        raise ValueError("Canon reference must have a characters object (1-80 names).")
    validated = {}
    for name, aliases in characters.items():
        if not isinstance(name, str) or not isinstance(aliases, list) or len(aliases) > ALIAS_LIMIT:
            raise ValueError("Every character must have a list of at most 12 aliases.")
        if not 1 <= len(name.strip()) <= 150:
            raise ValueError("Character name length is invalid.")
        names = [name, *aliases]
        for alias in names:
            if not isinstance(alias, str):
                raise ValueError("Alias must be a string.")
            term_occurrences("verification", alias)
        validated[name] = list(dict.fromkeys(names))
    chapters = selected_folder(chapter_folder, {".md", ".markdown", ".txt"}, 60)
    if not chapters:
        raise ValueError("Select a folder containing up to 60 text chapters.")
    counts = {name: 0 for name in validated}
    by_chapter = []
    total_words = 0
    for index, chapter in enumerate(chapters, 1):
        if chapter.stat().st_size > MAX_TEXT:
            raise ValueError("A chapter exceeds the 2 MiB review limit.")
        text = chapter.read_text(encoding="utf-8-sig")
        total_words += count_words(text)
        active = []
        for name, aliases in validated.items():
            # Overlapping aliases describe one character; count covered chapters,
            # not total literal matches.
            if any(term_occurrences(text, alias) for alias in aliases):
                active.append(name)
                counts[name] += 1
        by_chapter.append({"chapter_index": index, "named_characters_found": len(active)})
    return {
        "workspace": "Author",
        "mode": "read_only",
        "operation": "character_coverage",
        "chapters_inspected": len(chapters),
        "approximate_words": total_words,
        "canonical_characters_listed": len(validated),
        "chapters_containing_each_character": counts,
        "chapter_coverage_counts": by_chapter,
        "note": "Names are counted only from the user-selected alias map. "
                "Absence is not a contradiction. No origin, chronology, powers, "
                "or Broken World continuity facts are invented.",
    }
