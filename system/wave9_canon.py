"""Wave 9: source-anchored Broken World canon proposal review.

The Canon Store and manuscript remain authoritative. This tool compares
owner-selected JSON entries, never edits canon or invents story history.
Potential conflicts are advisory only, not definitive contradictions.
"""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
import re

from operations_wave8_core import json_file, selected_folder

MAX_CLAIMS = 600
MAX_TEXT = 2 * 1024 * 1024
NAME = re.compile(r"^[\w .,'-]{1,100}$", re.UNICODE)
SOURCE_BASENAME = re.compile(r"^[\w .,'()-]{1,160}\.(?:md|markdown|txt)$", re.I | re.UNICODE)


def _text(value, label, size):
    if not isinstance(value, str) or len(value.strip()) > size:
        raise ValueError(f"{label} must be a string of at most {size} characters.")
    return value.strip()


def _facts(path, *, authoritative):
    obj = json_file(path)
    if obj.get("schema") != "spider-canon-claims-v1":
        raise ValueError("Choose a Spider Canon Claims v1 JSON file.")
    rows = obj.get("claims")
    if not isinstance(rows, list) or len(rows) > MAX_CLAIMS:
        raise ValueError("Claim list must have at most 600 entries.")
    accepted = []
    for index, entry in enumerate(rows, 1):
        if not isinstance(entry, dict):
            raise ValueError("Every claim must be a JSON object.")
        entity = _text(entry.get("entity"), "Entity", 100)
        attribute = _text(entry.get("attribute"), "Attribute", 100)
        scope = _text(entry.get("scope", "unspecified"), "Temporal scope", 100)
        value = _text(entry.get("value"), "Claim value", 500)
        status = entry.get("status")
        if not (entity and attribute and scope and value):
            raise ValueError("Empty entity, attribute, scope, or value.")
        if not NAME.fullmatch(entity) or not NAME.fullmatch(attribute):
            raise ValueError("Entity and attribute must be plain named references.")
        if status not in (("approved",) if authoritative else ("proposed", "approved")):
            raise ValueError("Source claims need approved status; proposals need a known status.")
        source_file = _text(entry.get("source_file", ""), "Source filename", 160)
        quote = _text(entry.get("source_quote", ""), "Source quote", 500)
        if source_file and not SOURCE_BASENAME.fullmatch(source_file):
            raise ValueError("Source file must be a basename for a local text chapter.")
        accepted.append({
            "index": index,
            "entity": entity,
            "attribute": attribute,
            "scope": scope,
            "value": value,
            "status": status,
            "source_file": source_file,
            "source_quote": quote,
        })
    return accepted


def _key(item):
    return tuple(" ".join(item[field].casefold().split())
                 for field in ("entity", "attribute", "scope"))


def _value(item):
    return " ".join(item["value"].casefold().split())


def canon_proposal_review(approved_json, proposal_json, manuscript_folder):
    approved = _facts(approved_json, authoritative=True)
    proposals = _facts(proposal_json, authoritative=False)
    folder = Path(manuscript_folder).expanduser()
    chapters = selected_folder(folder, {".txt", ".md", ".markdown"}, 60)
    by_filename = {path.name: path for path in chapters}
    current = defaultdict(set)
    for item in approved:
        current[_key(item)].add(_value(item))
    flags = []
    anchors = {"matched": 0, "missing_quote": 0, "missing_file": 0,
               "not_supplied": 0}
    for entry in proposals:
        key = _key(entry)
        other_values = current.get(key, set())
        if other_values and _value(entry) not in other_values:
            flags.append({
                "proposal_index": entry["index"],
                "entity": entry["entity"],
                "attribute": entry["attribute"],
                "scope": entry["scope"],
                "review_reason": "Different value for same named entity, property and time scope",
                "requires_author_decision": True,
            })
        file = by_filename.get(entry["source_file"])
        quote = entry["source_quote"]
        if not quote or not entry["source_file"]:
            anchors["not_supplied"] += 1
        elif file is None:
            anchors["missing_file"] += 1
        elif file.stat().st_size > MAX_TEXT:
            anchors["missing_quote"] += 1
        else:
            content = file.read_text(encoding="utf-8-sig")
            anchors["matched" if quote in content else "missing_quote"] += 1
    return {
        "workspace": "Author",
        "mode": "read_only",
        "operation": "canon_proposal_review",
        "approved_claims": len(approved),
        "proposed_claims": len(proposals),
        "local_chapters_available": len(chapters),
        "candidate_value_disagreements": flags[:100],
        "candidate_value_disagreements_total": len(flags),
        "proposal_source_anchor_results": anchors,
        "canon_modified": False,
        "note": "Signals only when a named entity, property and scope have "
                "different recorded text. A different claim may be intentional "
                "or reflect later development. Author must decide all canon changes.",
    }
