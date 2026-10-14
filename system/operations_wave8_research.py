"""Offline claim-citation coverage and source provenance checks for Deep Forage."""
from __future__ import annotations
from collections import Counter
import re
from urllib.parse import urlsplit

from operations_wave8_core import json_file, text_file


def research_provenance(report_path, sources_path):
    body = text_file(report_path)
    data = json_file(sources_path)
    sources = data.get("sources")
    if not isinstance(sources, list) or len(sources) > 1000:
        raise ValueError("The saved research JSON must contain at most 1000 sources.")
    hostnames = Counter()
    urls = Counter()
    dates = 0
    missing_titles = 0
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("Research source entries must be JSON objects.")
        raw_url = str(source.get("url") or "").strip()
        try:
            parsed = urlsplit(raw_url)
            hostname = parsed.hostname
        except ValueError:
            hostname = None
        if hostname and parsed.scheme in ("https", "http"):
            hostnames[hostname.casefold()] += 1
            urls[(parsed.scheme.lower(), hostname.casefold(), parsed.path.rstrip("/"),
                  parsed.query)] += 1
        if str(source.get("published") or "").strip():
            dates += 1
        if not str(source.get("title") or "").strip():
            missing_titles += 1
    markers = [int(number) for number in re.findall(r"(?<!\w)\[(\d{1,4})\](?!\w)", body)]
    recognized = {n for n in markers if 1 <= n <= len(sources)}
    out_of_range = sorted({n for n in markers if n not in recognized})
    repeated = sum(n - 1 for n in urls.values() if n > 1)
    return {
        "workspace": "Deep Forage",
        "mode": "read_only",
        "operation": "offline_citation_provenance",
        "sources_listed": len(sources),
        "unique_website_hosts": len(hostnames),
        "sources_with_publication_metadata": dates,
        "sources_without_title": missing_titles,
        "duplicated_normalized_urls": repeated,
        "numeric_citation_occurrences": len(markers),
        "unique_in_range_citation_ids": len(recognized),
        "out_of_range_citation_ids": out_of_range[:30],
        "uncited_source_entries": len(sources) - len(recognized),
        "strongest_single_host_source_count": max(hostnames.values(), default=0),
        "note": "This is metadata/marker coverage only. Does not open links, verify "
                "claims, determine credibility or prove independent reporting.",
    }
