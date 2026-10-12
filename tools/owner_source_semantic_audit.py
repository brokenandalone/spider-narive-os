#!/usr/bin/env python3
"""Offline semantic reconciliation inventory for the 31 owner-installed files.

Uses local owner archive and pinned Git source. Reads Python AST, never imports
or runs uploaded code. Output is metadata only (no source or secrets); the
optional private patch previews remain on the owner PC, never on GitHub.
This diagnostic does NOT approve a release or automatically change a module.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from build_owner_preserving_stage import (
    OWNER_FILES, load_owner_zip, parse_only, checked_path,
    verified_head, digest,
)


def index_code(raw: bytes, name: str) -> dict:
    """Return the effective public class/function ASTs, never source text."""
    if not name.endswith(".py"):
        return {"symbols": {}, "imports": [], "init_attrs": {}, "self_calls": {}}
    tree = ast.parse(raw.decode("utf-8"), filename=name)
    symbols: dict[str, dict] = {}
    imports = []
    init_attrs: dict[str, list[str]] = {}
    self_calls: dict[str, list[str]] = {}

    def add_function(prefix: str, item):
        key = prefix + item.name
        # Keep signature separate so we can detect non-additive interface drift.
        try:
            signature = ast.unparse(item.args)
        except Exception:
            signature = "<unparsable>"
        symbols[key] = {
            "signature": signature,
            "ast_sha256": digest(
                ast.dump(item, annotate_fields=True, include_attributes=False).encode()
            ),
        }
        methods = set()
        for child in ast.walk(item):
            if isinstance(child, ast.Attribute) and isinstance(child.value, ast.Name):
                if child.value.id == "self":
                    methods.add(child.attr)
        self_calls[key] = sorted(methods)

    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            try:
                imports.append(ast.unparse(node))
            except Exception:
                imports.append("<unparsable import>")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            add_function("", node)
        elif isinstance(node, ast.ClassDef):
            symbols[node.name] = {
                "signature": "<class>",
                "ast_sha256": digest(ast.dump(node, include_attributes=False).encode()),
            }
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    add_function(node.name + ".", child)
                    if child.name == "__init__":
                        attrs = set()
                        for item in ast.walk(child):
                            if isinstance(item, ast.Attribute) and isinstance(item.value, ast.Name):
                                if item.value.id == "self" and isinstance(item.ctx, ast.Store):
                                    attrs.add(item.attr)
                        init_attrs[node.name] = sorted(attrs)
    return {
        "symbols": symbols,
        "imports": sorted(imports),
        "init_attrs": init_attrs,
        "self_calls": self_calls,
    }


def classify(name: str, owner: bytes, candidate: bytes) -> dict:
    record = {
        "path": name,
        "owner_sha256": digest(owner),
        "candidate_sha256": digest(candidate),
        "exactly_equal": owner == candidate,
        "action": "OWNER_BASIS_RETAINED; NO_AUTOMATIC_REPLACEMENT",
    }
    if name.endswith(".py"):
        a, b = index_code(owner, name), index_code(candidate, name)
        mine, theirs = a["symbols"], b["symbols"]
        akeys, bkeys = set(mine), set(theirs)
        shared_changed = sorted(k for k in akeys & bkeys if
                                mine[k]["ast_sha256"] != theirs[k]["ast_sha256"])
        shared_api_changed = sorted(k for k in akeys & bkeys if
                                    mine[k]["signature"] != theirs[k]["signature"])
        proposed_only = sorted(bkeys - akeys)
        owner_only = sorted(akeys - bkeys)
        added_init_attrs = {
            cls: sorted(set(v) - set(a["init_attrs"].get(cls, [])))
            for cls, v in b["init_attrs"].items()
            if set(v) - set(a["init_attrs"].get(cls, []))
        }
        proposed_new_methods_called_by_owner = sorted(
            f"{key} -> {member}"
            for key, refs in a["self_calls"].items()
            for member in refs
            if key.rpartition(".")[0] + "." + member in (bkeys - akeys)
        )
        record.update({
            "owner_only_symbols": owner_only,
            "candidate_only_symbols": proposed_only,
            "shared_behavior_changed": shared_changed,
            "shared_signature_changed": shared_api_changed,
            "candidate_only_imports": sorted(set(b["imports"]) - set(a["imports"])),
            "owner_only_imports": sorted(set(a["imports"]) - set(b["imports"])),
            "candidate_only_constructor_fields": added_init_attrs,
            "owner_code_referencing_candidate_only_methods": proposed_new_methods_called_by_owner,
            "needs_constructor_or_ui_wiring_review": bool(added_init_attrs or
                                                any(x.endswith(".__init__") for x in shared_changed)),
            "safe_to_auto_install": False,
        })
    else:
        record.update({"shell_semantic_diff_requires_review": owner != candidate,
                       "safe_to_auto_install": False})
    return record


def summarize(rows: list[dict]) -> dict:
    aggregate = {
        "files": len(rows), "exact_matches": sum(r["exactly_equal"] for r in rows),
        "candidate_only_symbol_count": sum(len(r.get("candidate_only_symbols", [])) for r in rows),
        "owner_only_symbol_count": sum(len(r.get("owner_only_symbols", [])) for r in rows),
        "shared_changed_symbol_count": sum(len(r.get("shared_behavior_changed", [])) for r in rows),
        "shared_signature_changed_count": sum(len(r.get("shared_signature_changed", [])) for r in rows),
        "constructor_or_ui_review_files": [r["path"] for r in rows if r.get("needs_constructor_or_ui_wiring_review")],
        "owner_protection": "all 31 live files remain authoritative; nothing overwritten",
        "release_status": "NOT_READY_CODE_RECONCILIATION_REQUIRED",
    }
    return aggregate


def audit(repo: Path, archive: Path, live: Path, commit: str) -> dict:
    tracked = set(verified_head(repo, commit))
    originals = load_owner_zip(archive)
    if set(originals) != set(OWNER_FILES):
        raise ValueError("Owner ZIP membership changed")
    rows = []
    for name in OWNER_FILES:
        if name not in tracked:
            raise ValueError("Candidate missing tracked owner entrypoint: " + name)
        owner = originals[name]
        pc = checked_path(live, name).read_bytes()
        if digest(pc) != digest(owner):
            raise ValueError("Live source changed since reviewed owner ZIP: " + name)
        proposed = checked_path(repo, name).read_bytes()
        parse_only(name, proposed)
        rows.append(classify(name, owner, proposed))
    return {
        "status": "RECONCILIATION_AUDIT_NO_INSTALL",
        "candidate_sha": commit,
        "scope": "NATIVE_SPIDER_OS_ONLY",
        "media_center_and_website_excluded": True,
        "code_source_in_report": False,
        "readiness": summarize(rows),
        "files": rows,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--owner-archive", type=Path, required=True)
    p.add_argument("--installed-root", type=Path,
                   default=Path("/usr/local/lib/spider-os"))
    p.add_argument("--expected-commit", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        output = args.output.expanduser().absolute()
        if output.exists() or output.is_symlink():
            raise ValueError("Refusing to overwrite previous reconciliation report")
        result = audit(args.source.resolve(), args.owner_archive.resolve(),
                       args.installed_root.resolve(), args.expected_commit)
        # Sensitive workstation metadata: owner only (0600).
        fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as out:
                json.dump(result, out, indent=2)
                out.write("\n")
        except BaseException:
            output.unlink(missing_ok=True)
            raise
    except (OSError, ValueError, TypeError, SyntaxError, UnicodeError,
            subprocess.TimeoutExpired) as exc:
        print("SEMANTIC AUDIT BLOCKED:", type(exc).__name__, str(exc)[:250],
              file=sys.stderr)
        return 3
    print("OFFLINE SEMANTIC AUDIT:", result["status"])
    print("Reviewed customized native OS entrypoints:", result["readiness"]["files"])
    print("Candidate-only Python symbols:", result["readiness"]["candidate_only_symbol_count"])
    print("Owner-only Python symbols:", result["readiness"]["owner_only_symbol_count"])
    print("Changed shared Python symbols:", result["readiness"]["shared_changed_symbol_count"])
    print("Constructor/UI wiring review needed:",
          len(result["readiness"]["constructor_or_ui_review_files"]))
    print("Report:", output)
    print("NOT INSTALLABLE. NO LIVE FILES MODIFIED. NO MEDIA CENTER OR BCN WEBSITE.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
