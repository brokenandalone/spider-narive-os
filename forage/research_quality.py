"""Transparent source audits and claim-citation checks for Deep Forage.

This is *not* an AI truth or credibility score. Metadata-only heuristics can
identify holes in evidence, not determine whether an article is correct.
"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import ipaddress
import re
from urllib.parse import urlsplit, urlunsplit


CLAIM_CITATION = re.compile(r"\[(\d+)\]")


def canonical_url(raw):
    parts = urlsplit(str(raw))
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return str(raw)
    host = parts.hostname.lower().rstrip(".")
    if ":" in host:  # IPv6 form
        host = "[" + host + "]"
    port = f":{parts.port}" if parts.port and parts.port not in (80, 443) else ""
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), host + port, path, parts.query, ""))


def repeated_evidence(sources, threshold=0.78):
    """Identify likely copied text, not factual agreements/disagreements.

    Same-site and cross-site mirrors can make independent-source counts look
    stronger than they are. This is a bounded lexical overlap signal only.
    """
    sets = []
    for source in sources[:30]:
        content = str(source.get("content") or source.get("snippet") or "").lower()
        words = re.findall(r"[^\\W_]+", content, flags=re.UNICODE)[:800]
        sets.append({tuple(words[i:i+4]) for i in range(len(words)-3)})
    pairs = []
    for a, left in enumerate(sets):
        if len(left) < 5:
            continue
        for b in range(a + 1, len(sets)):
            right = sets[b]
            if len(right) < 5:
                continue
            union = left | right
            overlap = len(left & right) / len(union) if union else 0
            if overlap >= threshold:
                pairs.append({"source_a": a + 1, "source_b": b + 1,
                              "lexical_overlap": round(overlap, 3)})
    return pairs


def source_summary(sources):
    kinds = Counter(str(s.get("evidence_kind", "unknown")) for s in sources)
    engines = Counter(str(s.get("engine", "unknown")) for s in sources)
    hosts = Counter()
    inspected = []
    for number, source in enumerate(sources, 1):
        host = (urlsplit(str(source.get("url", ""))).hostname or "").lower()
        if host:
            hosts[host] += 1
        evidence = str(source.get("content", ""))
        kind = str(source.get("evidence_kind", "unknown"))
        inspected.append({
            "number": number,
            "host": host,
            "kind": kind,
            "characters": len(evidence),
            "sha256": hashlib.sha256(evidence.encode("utf-8")).hexdigest() if evidence else None,
            "reported_date": str(source.get("published", "")).strip() or None,
        })
    repeated = repeated_evidence(sources)
    warnings = []
    if not sources:
        warnings.append("No retrievable evidence was obtained.")
    if kinds.get("page_text", 0) == 0 and sources:
        warnings.append("Only search snippets were available; no page text was read.")
    if repeated:
        warnings.append("Similar text appears in multiple sources; mirrors may not be independent corroboration.")
    if sources and len(hosts) < 2:
        warnings.append("Evidence comes from only one host; independent corroboration was not established.")
    if sources and all(not row["reported_date"] for row in inspected):
        warnings.append("No publication dates were supplied; currency cannot be assessed.")
    if sources and len(sources) != len({canonical_url(s.get("url", "")) for s in sources}):
        warnings.append("The retrieved collection contains repeated canonical URLs.")
    return {
        "source_count": len(sources),
        "page_text_count": kinds.get("page_text", 0),
        "snippet_count": kinds.get("search_snippet", 0),
        "unique_host_count": len(hosts),
        "host_counts": dict(hosts),
        "provider_counts": dict(engines),
        "source_details": inspected,
        "near_duplicate_evidence": repeated,
        "warnings": warnings,
        "note": "Counts and metadata are not verification that any claim is true.",
    }


def citation_audit(synthesis, source_count):
    """Check citation references and paragraph coverage, never fabricate matches."""
    text = str(synthesis or "")
    references = [int(m) for m in CLAIM_CITATION.findall(text)]
    invalid = sorted(set(n for n in references if n < 1 or n > source_count))
    cited = sorted(set(n for n in references if 1 <= n <= source_count))
    # Bibliography, headings and empty lines are not substantive claims.
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    unchecked = []
    for part in paragraphs:
        stripped = re.sub(r"(?m)^\s{0,3}#{1,6}\s+[^\n]+", "", part).strip()
        stripped = re.sub(r"(?m)^\s*[-*]\s*(?:What to investigate next|Next steps).*", "", stripped, flags=re.I)
        if len(stripped) >= 85 and not CLAIM_CITATION.search(stripped):
            unchecked.append(stripped[:145])
    return {
        "valid": bool(cited) and not invalid and not unchecked,
        "cited_sources": cited,
        "uncited_substantive_paragraphs": unchecked[:12],
        "invalid_references": invalid,
        "unused_sources": [i for i in range(1, source_count + 1) if i not in cited],
        "note": "Syntactically valid citations do not demonstrate that the cited source supports a claim.",
    }


def audit_markdown(audit):
    lines = ["## Source transparency", "",
             f"- Sources captured: {audit['source_count']}",
             f"- Full page texts: {audit['page_text_count']}",
             f"- Search snippets only: {audit['snippet_count']}",
             f"- Distinct source hosts: {audit['unique_host_count']}",
             "- These counts do **not** establish factual correctness.", ""]
    if audit["warnings"]:
        lines += ["### Limitations"] + ["- " + warning for warning in audit["warnings"]] + [""]
    return lines
