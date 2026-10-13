"""Opt-in, read-only project preflight tools for the Spider Operations Hub.

None of these functions updates source files, transmits content, grades work,
or changes manuscripts, assignments, recordings, or research archives.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import re
import struct
import wave
from urllib.parse import urlsplit

MAX_TEXT_BYTES = 2 * 1024 * 1024
MAX_SOURCES_BYTES = 8 * 1024 * 1024
WORD_RE = re.compile(r"\b[\w]+(?:['’][\w]+)?\b", re.UNICODE)
CHAPTER_RE = re.compile(r"(?im)^\s*(?:#{1,3}\s*)?chapter\s+[\divxlcdm]+\b[^\n]*")
PLACEHOLDER_RE = re.compile(
    r"(?i)\[(?:source needed|citation needed|verify source|todo|tk)\]|\bTODO:"
)


def _read_text(path):
    source = Path(path).expanduser()
    if source.is_symlink() or not source.is_file():
        raise ValueError("Choose an existing ordinary text file, not a symlink.")
    if source.suffix.lower() not in {".txt", ".md", ".markdown"}:
        raise ValueError("Only TXT or Markdown text is accepted.")
    if source.stat().st_size > MAX_TEXT_BYTES:
        raise ValueError("Text file exceeds the 2 MiB review limit.")
    return source.read_text(encoding="utf-8-sig")


def manuscript_report(path):
    """Summarize an explicitly selected Author text file, without modifying it."""
    text = _read_text(path)
    words = WORD_RE.findall(text)
    chapters = CHAPTER_RE.findall(text)
    headings = re.findall(r"(?m)^#{1,3}\s+(.{1,150})$", text)
    return {
        "workspace": "Author",
        "mode": "read_only",
        "approximate_words": len(words),
        "chapter_headings_detected": len(chapters),
        "markdown_headings_detected": len(headings),
        "nonempty_lines": sum(bool(line.strip()) for line in text.splitlines()),
        "editorial_placeholders": len(PLACEHOLDER_RE.findall(text)),
        "note": "Structural hints only; the Author project database and canon are not changed.",
    }


def study_report(path, directions=""):
    """Draft-only indicators, not an APA audit, grade, or citation verification."""
    text = _read_text(path)
    words = len(WORD_RE.findall(text))
    directions = str(directions or "")[:10000]
    low = high = None
    match = re.search(
        r"(?i)\b(\d{2,5})\s*(?:-|–|to)\s*(\d{2,5})\s+words?\b",
        directions,
    )
    if match:
        a, b = map(int, match.groups())
        if 50 <= a <= b <= 50000:
            low, high = a, b
    approx = None
    if low is not None:
        approx = "within_detected_range" if low <= words <= high else "outside_detected_range"
    citations = len(re.findall(r"\([^)\n]{2,100},\s*(?:19|20)\d{2}[a-z]?\)", text))
    return {
        "workspace": "Study",
        "mode": "read_only",
        "approximate_words": words,
        "detected_word_range": [low, high] if low is not None else None,
        "word_range_signal": approx,
        "parenthetical_citation_patterns": citations,
        "references_heading_found": bool(re.search(r"(?im)^\s*(?:#+\s*)?references\s*$", text)),
        "unresolved_source_placeholders": len(PLACEHOLDER_RE.findall(text)),
        "note": "Heuristic checklist only. Confirm the actual SNHU rubric, sources and APA rules yourself.",
    }


def _pcm_values(raw, width):
    if width == 1:
        for value in raw:
            yield (value - 128) / 128.0
    elif width == 2:
        for (value,) in struct.iter_unpack("<h", raw):
            yield value / 32768.0
    elif width == 3:
        for i in range(0, len(raw), 3):
            yield int.from_bytes(raw[i:i + 3], "little", signed=True) / 8388608.0
    elif width == 4:
        for (value,) in struct.iter_unpack("<i", raw):
            yield value / 2147483648.0
    else:
        raise ValueError("Only 8/16/24/32-bit PCM WAV is supported.")


def wav_report(path):
    """Inspect up to the first and last 2 seconds of PCM samples; no sound playback."""
    source = Path(path).expanduser()
    if source.is_symlink() or source.suffix.lower() != ".wav" or not source.is_file():
        raise ValueError("Choose an existing ordinary .wav file.")
    with wave.open(str(source), "rb") as reader:
        rate = reader.getframerate()
        channels = reader.getnchannels()
        width = reader.getsampwidth()
        frames = reader.getnframes()
        if (reader.getcomptype() != "NONE" or not 8000 <= rate <= 192000
                or channels not in (1, 2) or width not in (1, 2, 3, 4)
                or frames <= 0):
            raise ValueError("Select nonempty mono/stereo uncompressed PCM WAV (8–192 kHz).")
        edge = min(frames, rate * 2)
        intervals = [(0, edge)]
        if frames > edge:
            trailing_start = max(edge, frames - edge)
            if trailing_start < frames:
                intervals.append((trailing_start, frames - trailing_start))
        peak = squares = total = 0.0
        samples = clipped = 0
        for start, count in intervals:
            reader.setpos(start)
            remaining = count
            while remaining:
                take = min(4096, remaining)
                raw = reader.readframes(take)
                if not raw:
                    break
                for value in _pcm_values(raw, width):
                    peak = max(peak, abs(value))
                    squares += value * value
                    total += value
                    samples += 1
                    if abs(value) >= 0.9999:
                        clipped += 1
                remaining -= take
    rms = math.sqrt(squares / samples) if samples else 0.0
    dc = total / samples if samples else 0.0
    return {
        "workspace": "Studio",
        "mode": "read_only",
        "channels": channels,
        "sample_rate_hz": rate,
        "pcm_bits": width * 8,
        "duration_seconds": round(frames / rate, 2),
        "samples_inspected": samples,
        "sample_peak": round(peak, 5),
        "rms": round(rms, 5),
        "dc_offset_estimate": round(dc, 5),
        "near_full_scale_samples": clipped,
        "note": "Samples only beginning/end. Not a LUFS, true-peak, clipping-proof or mix-quality certification.",
    }


def research_sources_report(path):
    """Audit only an explicitly selected Deep Forage JSON export."""
    source = Path(path).expanduser()
    if (source.is_symlink() or not source.is_file()
            or source.suffix.lower() != ".json"
            or source.stat().st_size > MAX_SOURCES_BYTES):
        raise ValueError("Select an ordinary JSON export smaller than 8 MiB.")
    data = json.loads(source.read_text(encoding="utf-8-sig"))
    sources = data.get("sources") if isinstance(data, dict) else None
    if not isinstance(sources, list) or len(sources) > 1000:
        raise ValueError("Expected a Deep Forage export with at most 1000 sources.")
    hosts = set()
    links = set()
    duplicate_links = missing_title = missing_date = 0
    for item in sources:
        if not isinstance(item, dict):
            raise ValueError("Source entries must be objects.")
        title = str(item.get("title") or "")
        url = str(item.get("url") or "").strip()
        published = str(item.get("published") or "")
        if not title.strip():
            missing_title += 1
        if not published.strip():
            missing_date += 1
        if url:
            if url in links:
                duplicate_links += 1
            links.add(url)
            try:
                hostname = urlsplit(url).hostname
            except ValueError:
                hostname = None
            if hostname:
                hosts.add(hostname.casefold())
    return {
        "workspace": "Deep Forage",
        "mode": "read_only",
        "sources": len(sources),
        "unique_hosts": len(hosts),
        "duplicate_exact_urls": duplicate_links,
        "sources_missing_title": missing_title,
        "sources_missing_publication_date": missing_date,
        "note": "Metadata completeness only. No URLs were opened, downloaded or fact-checked.",
    }
