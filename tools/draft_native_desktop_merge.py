#!/usr/bin/env python3
"""Stage a NON-INSTALLABLE, owner-private desktop preservation overlay.

Copies candidate source to a private review folder, then adds *only* locally
unique imports, functions and class methods from the installed source.
Overlapping changed methods are NEVER automatically reconciled: they're
listed as UNRESOLVED, and the draft cannot be installed as a release.

Nothing in /usr/local/lib, services, Git branches, packages, music or
other original user-owned files is modified or executed.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import sys

from review_staged_desktop_methods import (
    DESKTOP, inspect_stage, read_regular, structural_diff, MAX_BYTES,
)
from stage_native_merge import _private_folder, _private_write

REVIEW_FORMAT = "spider-native-local-preservation-overlay-v1"


def _definitions(tree):
    found = {}
    classes = {}

    def scan(children, prefix=""):
        for item in children:
            if isinstance(item, ast.ClassDef):
                name = prefix + item.name
                classes[name] = item
                scan(item.body, name + ".")
            elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found[prefix + item.name] = item
    scan(tree.body)
    return found, classes


def _source_text(lines, node):
    first = min([node.lineno] +
                [decorator.lineno for decorator in getattr(node, "decorator_list", [])])
    return "".join(lines[first - 1:node.end_lineno])


def _new_imports(old_tree, new_tree, local_lines):
    seen = {
        ast.dump(item, include_attributes=False)
        for item in new_tree.body
        if isinstance(item, (ast.Import, ast.ImportFrom))
    }
    extras = []
    for item in old_tree.body:
        if not isinstance(item, (ast.Import, ast.ImportFrom)):
            continue
        ident = ast.dump(item, include_attributes=False)
        if ident not in seen:
            extras.append((_source_text(local_lines, item), item.module == "__future__"
                           if isinstance(item, ast.ImportFrom) else False))
    return extras


def preservation_overlay(local_bytes, candidate_bytes):
    """Return a REVIEW-ONLY candidate with local-only definitions restored.

    Shared definition bodies are left exactly as candidate, but ALL changed
    shared names are reported unresolved and must be manually reconciled.
    """
    original = local_bytes.decode("utf-8")
    proposed = candidate_bytes.decode("utf-8")
    local_tree = ast.parse(original)
    candidate_tree = ast.parse(proposed)
    local_defs, local_classes = _definitions(local_tree)
    candidate_defs, candidate_classes = _definitions(candidate_tree)
    notes = {
        "owner_only_members_added": [],
        "owner_only_imports_added": 0,
        "unresolved_shared": structural_diff(
            local_bytes, candidate_bytes, "desktop.py")["changed_shared_definitions"],
    }
    local_lines = original.splitlines(keepends=True)
    candidate_lines = proposed.splitlines(keepends=True)
    insertions = {}
    for name, node in local_defs.items():
        if name in candidate_defs:
            continue
        parts = name.rsplit(".", 1)
        parent_name = parts[0] if len(parts) == 2 else ""
        if parent_name:
            parent = candidate_classes.get(parent_name)
            if parent is None:
                if parent_name in local_classes:
                    # Copy the complete owner-only class in a separate pass.
                    continue
                raise ValueError("Cannot preserve owner-only member without parent: " + name)
            insertion = parent.end_lineno
        else:
            # Put owner-only top-level functions at the end of candidate file.
            insertion = len(candidate_lines)
        snippet = _source_text(local_lines, node)
        insertions.setdefault(insertion, []).append(snippet)
        notes["owner_only_members_added"].append(name)

    for name, node in local_classes.items():
        if name in candidate_classes:
            continue
        # Copy entire owner-only classes; their methods are included.
        insertion = len(candidate_lines)
        insertions.setdefault(insertion, []).append(_source_text(local_lines, node))
        notes["owner_only_members_added"].append(name)

    for pos in sorted(insertions, reverse=True):
        new_lines = []
        for snippet in insertions[pos]:
            if not snippet.endswith("\n"):
                snippet += "\n"
            new_lines.extend(["\n", snippet])
        candidate_lines[pos:pos] = new_lines
    assembled = "".join(candidate_lines)
    new_tree = ast.parse(assembled)
    extras = _new_imports(local_tree, new_tree, local_lines)
    if extras:
        revised = assembled.splitlines(keepends=True)
        imports = [node for node in new_tree.body
                   if isinstance(node, (ast.Import, ast.ImportFrom))]
        future = [node for node in imports
                  if isinstance(node, ast.ImportFrom) and node.module == "__future__"]
        regular = [node for node in imports if node not in future]
        future_end = max((node.end_lineno for node in future), default=0)
        last_import = max((node.end_lineno for node in imports), default=future_end)
        # Insert normal imports at end of existing top-level import area.
        regular_texts = [text for text, is_future in extras if not is_future]
        future_texts = [text for text, is_future in extras if is_future]
        if regular_texts:
            revised[last_import:last_import] = [
                text if text.endswith("\n") else text + "\n"
                for text in regular_texts]
        if future_texts:
            revised[future_end:future_end] = [
                text if text.endswith("\n") else text + "\n"
                for text in future_texts]
        assembled = "".join(revised)
        notes["owner_only_imports_added"] = len(extras)
    new_tree = ast.parse(assembled)
    resulting_defs, resulting_classes = _definitions(new_tree)
    if not (set(local_defs) <= set(resulting_defs) and
            set(candidate_defs) <= set(resulting_defs) and
            set(local_classes) <= set(resulting_classes) and
            set(candidate_classes) <= set(resulting_classes)):
        raise ValueError("Overlay would lose original or candidate definitions")
    notes["owner_only_members_added"].sort()
    notes["unresolved_shared"].sort()
    notes["install_allowed"] = False
    return assembled.encode("utf-8"), notes


def draft(stage, output, *, home=None):
    stage = Path(stage).expanduser()
    results = inspect_stage(stage)
    if tuple(result["file"] for result in results) != DESKTOP:
        raise ValueError("Staged desktop files do not match guarded release")
    # Compile each proposal completely in memory before writing any draft.
    compiled = []
    for name in DESKTOP:
        old = read_regular(stage, "installed/" + name, MAX_BYTES)
        new = read_regular(stage, "candidate/" + name, MAX_BYTES)
        payload, info = preservation_overlay(old, new)
        compiled.append((name, payload, info))
    output = Path(output).expanduser()
    _private_folder(output, home=Path.home() if home is None else Path(home),
                    source=stage, installed=Path("/usr/local/lib/spider-os"))
    for name, payload, _ in compiled:
        _private_write(output, "draft/" + name, payload)
    report = {
        "format": REVIEW_FORMAT,
        "source": "existing PRIVATE staged desktop code, not installed filesystem",
        "installed_modified": False,
        "release_installable": False,
        "safe_to_overwrite": False,
        "files": [dict(component=name, **info) for name, _, info in compiled],
    }
    _private_write(output, "merge-review.json", json.dumps(report, indent=2) + "\n")
    _private_write(output, "README.txt", (
        "SPIDER OS NON-INSTALLABLE PRIVATE MERGE OVERLAY\n"
        "This is a *review aid*, not an installer or deployable release.\n"
        "The candidate version remains the base of every draft file.\n"
        "Only unique owner methods/classes/imports were copied into draft.\n"
        "Every shared differing method still requires a human semantic merge.\n"
        "KEEP PRIVATE: these files contain code from your real computer.\n"
        "Do NOT copy this draft to /usr/local/lib/spider-os, run it as root,\n"
        "commit it publicly, or regard a passing syntax check as approval.\n"
        "The guarded 33-file release remains BLOCKED.\n"))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True,
                        help="NEW, private folder in owner HOME")
    args = parser.parse_args(argv)
    try:
        result = draft(args.stage, args.output)
    except (OSError, SyntaxError, UnicodeError, ValueError) as exc:
        print("SPIDER PRESERVATION DRAFT BLOCKED:", str(exc), file=sys.stderr)
        return 3
    print("SPIDER OS / PRIVATE NON-INSTALLABLE MERGE PREVIEW")
    for row in result["files"]:
        print("FILE", row["component"])
        print("  Local-only features preserved:", 
              ", ".join(row["owner_only_members_added"]) or "none")
        print("  Local-only imports retained:", row["owner_only_imports_added"])
        print("  UNRESOLVED overlapping methods:", len(row["unresolved_shared"]))
    print("Private draft only:", args.output)
    print("No running applications or installed files changed.")
    print("STRICT INSTALL GATE REMAINS BLOCKED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
