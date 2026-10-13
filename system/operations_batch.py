"""Read-only, bounded folder-level production checks.

Only the folder explicitly selected in the GUI is examined. No recursion,
renaming, audio rendering, network calls, file writes or model invocations.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import wave

from operations_quality import manuscript_report, study_report, wav_report

MAX_DIRECTORY_ENTRIES = 5000


def _files(folder, extensions, *, limit):
    directory = Path(folder).expanduser()
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Choose an existing ordinary directory, not a symlink.")
    matching = []
    for inspected, entry in enumerate(directory.iterdir(), start=1):
        if inspected > MAX_DIRECTORY_ENTRIES:
            raise ValueError("This directory is too large for a bounded inspection.")
        if entry.is_symlink() or not entry.is_file():
            continue
        if entry.suffix.lower() in extensions:
            matching.append(entry)
            if len(matching) > limit:
                raise ValueError(f"Review at most {limit} matching files at once.")
    if not matching:
        raise ValueError("No supported files in the selected directory.")
    return sorted(matching, key=lambda p: p.name.casefold())


def studio_session_report(directory):
    """Inspect max 24 WAV stems and identify potentially incompatible formats."""
    tracks = _files(directory, {".wav"}, limit=24)
    reports = []
    unreadable = []
    for index, track in enumerate(tracks, start=1):
        try:
            report = wav_report(track)
        except (OSError, ValueError, EOFError, RuntimeError, wave.Error) as error:
            unreadable.append({"track_index": index, "reason": type(error).__name__})
            continue
        reports.append(report)
    rates = Counter(r["sample_rate_hz"] for r in reports)
    depths = Counter(r["pcm_bits"] for r in reports)
    durations = [r["duration_seconds"] for r in reports]
    potential_near_full_scale = sum(r["near_full_scale_samples"] for r in reports)
    return {
        "workspace": "Studio",
        "operation": "recording_session_preflight",
        "mode": "read_only",
        "wav_files_found": len(tracks),
        "wav_files_inspected": len(reports),
        "unreadable_track_indices": unreadable,
        "sample_rates_hz": dict(sorted(rates.items())),
        "pcm_bit_depths": dict(sorted(depths.items())),
        "format_mismatch": len(rates) > 1 or len(depths) > 1,
        "duration_spread_seconds": (
            round(max(durations) - min(durations), 2) if durations else None
        ),
        "near_full_scale_samples_in_sampled_edges": potential_near_full_scale,
        "note": "Checks only first/last 2 seconds of each WAV. Different "
                "durations may be intentional; no stem synchronization verified.",
    }


def author_chapter_folder_report(directory):
    """Check up to 60 user-selected text chapters without touching manuscript data."""
    chapters = _files(directory, {".md", ".markdown", ".txt"}, limit=60)
    words = placeholders = headings = 0
    unreadable = 0
    empty = 0
    for chapter in chapters:
        try:
            report = manuscript_report(chapter)
        except (OSError, ValueError, UnicodeError):
            unreadable += 1
            continue
        words += report["approximate_words"]
        headings += report["chapter_headings_detected"]
        placeholders += report["editorial_placeholders"]
        empty += int(report["approximate_words"] == 0)
    return {
        "workspace": "Author",
        "operation": "chapter_folder_preflight",
        "mode": "read_only",
        "text_chapters_found": len(chapters),
        "readable_chapters": len(chapters) - unreadable,
        "unreadable_chapters": unreadable,
        "empty_chapters": empty,
        "approximate_total_words": words,
        "detected_chapter_headings": headings,
        "editorial_placeholders": placeholders,
        "note": "A text-folder overview, not a Master Canon validation, "
                "manuscript import, or Author database modification.",
    }


def study_assignment_folder_report(directory):
    """Inspect up to 50 local draft text files for placeholders and word totals."""
    drafts = _files(directory, {".md", ".markdown", ".txt"}, limit=50)
    words = placeholders = references = 0
    unreadable = 0
    for draft in drafts:
        try:
            report = study_report(draft)
        except (OSError, ValueError, UnicodeError):
            unreadable += 1
            continue
        words += report["approximate_words"]
        placeholders += report["unresolved_source_placeholders"]
        references += int(report["references_heading_found"])
    return {
        "workspace": "Study",
        "operation": "assignment_folder_preflight",
        "mode": "read_only",
        "draft_files_found": len(drafts),
        "readable_drafts": len(drafts) - unreadable,
        "unreadable_drafts": unreadable,
        "approximate_total_words": words,
        "unresolved_source_placeholders": placeholders,
        "drafts_with_references_heading": references,
        "note": "This does not determine submission readiness or validate APA "
                "sources. Only local TXT/Markdown files explicitly selected.",
    }
