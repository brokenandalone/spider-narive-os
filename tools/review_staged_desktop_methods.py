#!/usr/bin/env python3
"""Read-only AST reconciliation review of ALREADY staged Spider OS code.

Never imports/executes staged code. Never writes files, uploads content,
attempts a merge, touches /usr/local/lib, or changes the installed OS.
Only prints source definition identifiers/counts and structural comparisons.
A passing report never authorizes overwrite or release installation.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import stat
import sys

FORMAT = "spider-native-private-merge-stage-v1"
DESKTOP = (
    "the-web/shell/main.py",
    "the-web/shell/app_catalog.py",
    "the-web/shell/workspace_files.py",
    "the-web/shell/webbie_panel.py",
    "the-web/shell/webbie_cognitive_center.py",
)
MAX_BYTES = 1_000_000
MAX_MANIFEST = 300_000


def read_regular(root: Path, relative: str, max_bytes: int):
    if not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError("Unsafe staged path")
    path = root
    for piece in Path(relative).parts:
        path = path / piece
        if path.is_symlink():
            raise ValueError("Refusing symlink in private stage")
    try:
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > max_bytes:
            raise ValueError("Unsafe staged file format or size")
        return path.read_bytes()
    except OSError as error:
        raise ValueError("Staged file unavailable") from error


def _fingerprint(node):
    return hashlib.sha256(
        ast.dump(node, include_attributes=False).encode("utf-8")
    ).hexdigest()


def _functions(tree):
    """Return definition fingerprints by qualified class.method name.

    Top-level function identities and class methods are reported separately
    from class bodies. No code, values, literals, or expressions are returned.
    """
    result = {}
    signatures = {}
    class_bases = {}
    def scan(nodes, prefix=""):
        for node in nodes:
            if isinstance(node, ast.ClassDef):
                name = prefix + node.name
                class_bases[name] = _fingerprint(
                    ast.Tuple(elts=node.bases, ctx=ast.Load()))
                scan(node.body, name + ".")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = prefix + node.name
                result[name] = _fingerprint(node)
                signatures[name] = _fingerprint(
                    ast.Tuple(elts=[
                        node.args, *node.decorator_list
                    ], ctx=ast.Load()))
    scan(tree.body)
    return result, signatures, class_bases


def _top_level(tree):
    imports = set()
    bindings = {}
    executable_calls = 0
    for node in tree.body:
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add((node.level * "." + (node.module or "")))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    bindings[target.id] = _fingerprint(node)
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            executable_calls += 1
    return imports, bindings, executable_calls


def _method_nodes(tree):
    """Qualified method nodes for dependency review. Never executes code."""
    classes = {}
    methods = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        classes[node.name] = node
        for member in node.body:
            if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods[node.name + "." + member.name] = member
    return classes, methods


def _self_fields_written(node):
    if node is None:
        return set()
    result = set()
    for item in ast.walk(node):
        if isinstance(item, ast.Attribute) and isinstance(item.ctx, ast.Store):
            if isinstance(item.value, ast.Name) and item.value.id == "self":
                result.add(item.attr)
    return result


def preservation_dependencies(installed_bytes: bytes, candidate_bytes: bytes):
    """Local-only methods referencing removed constructor state or changed calls.

    Only inspect current AST owner/candidate data. Output symbols and counts,
    never values, literals, source text, credentials or runtime state.
    An empty warning list still does NOT mean a merge is safe.
    """
    try:
        old = ast.parse(installed_bytes.decode("utf-8"))
        incoming = ast.parse(candidate_bytes.decode("utf-8"))
    except (SyntaxError, UnicodeError) as error:
        raise ValueError("Cannot analyze private source syntax") from error
    _, old_methods = _method_nodes(old)
    _, new_methods = _method_nodes(incoming)
    shared_changed = {
        name for name in old_methods.keys() & new_methods.keys()
        if _fingerprint(old_methods[name]) != _fingerprint(new_methods[name])
    }
    results = []
    for name in sorted(old_methods.keys() - new_methods.keys()):
        if "." not in name:
            continue
        owner = name.split(".", 1)[0]
        old_init = old_methods.get(owner + ".__init__")
        new_init = new_methods.get(owner + ".__init__")
        old_fields = _self_fields_written(old_init)
        new_fields = _self_fields_written(new_init)
        reads = {
            item.attr for item in ast.walk(old_methods[name])
            if isinstance(item, ast.Attribute)
            and isinstance(item.ctx, ast.Load)
            and isinstance(item.value, ast.Name)
            and item.value.id == "self"
        }
        calls = {
            owner + "." + item.func.attr for item in ast.walk(old_methods[name])
            if isinstance(item, ast.Call)
            and isinstance(item.func, ast.Attribute)
            and isinstance(item.func.value, ast.Name)
            and item.func.value.id == "self"
        }
        results.append({
            "owner_only_method": name,
            "locally_initialized_fields_missing_from_candidate": sorted(
                (old_fields - new_fields) & reads),
            "calls_to_changed_shared_methods": sorted(calls & shared_changed),
            "owner_constructor_changed": owner + ".__init__" in shared_changed,
            "safe_to_install": False,
        })
    return results


def structural_diff(installed_bytes: bytes, candidate_bytes: bytes, path: str):
    try:
        old = ast.parse(installed_bytes.decode("utf-8"))
        new = ast.parse(candidate_bytes.decode("utf-8"))
    except (SyntaxError, UnicodeError) as error:
        raise ValueError("Staged Python cannot be parsed: " + path) from error
    old_defs, old_sigs, old_bases = _functions(old)
    new_defs, new_sigs, new_bases = _functions(new)
    old_imports, old_bindings, old_calls = _top_level(old)
    new_imports, new_bindings, new_calls = _top_level(new)
    common = old_defs.keys() & new_defs.keys()
    local_only = sorted(old_defs.keys() - new_defs.keys())
    candidate_only = sorted(new_defs.keys() - old_defs.keys())
    changed = sorted(name for name in common if old_defs[name] != new_defs[name])
    signatures = sorted(name for name in common
                        if old_sigs[name] != new_sigs[name])
    added_bindings = new_bindings.keys() - old_bindings.keys()
    changed_bindings = [name for name in old_bindings.keys() & new_bindings.keys()
                        if old_bindings[name] != new_bindings[name]]
    result = {
        "file": path,
        "local_only_definitions": local_only,
        "candidate_only_definitions": candidate_only,
        "changed_shared_definitions": changed,
        "signature_or_decorator_changes": signatures,
        "existing_class_base_changes": sum(
            old_bases[name] != new_bases[name]
            for name in old_bases.keys() & new_bases.keys()),
        "local_only_class_count": len(old_bases.keys() - new_bases.keys()),
        "candidate_only_class_count": len(new_bases.keys() - old_bases.keys()),
        "module_binding_changes": len(changed_bindings),
        "module_bindings_added": len(added_bindings),
        "module_bindings_removed": len(old_bindings.keys() - new_bindings.keys()),
        "installed_module_import_count": len(old_imports),
        "candidate_module_import_count": len(new_imports),
        "candidate_only_import_count": len(new_imports - old_imports),
        "local_only_import_count": len(old_imports - new_imports),
        "module_level_call_counts": {
            "installed": old_calls, "candidate": new_calls,
        },
        "manual_merge_required": installed_bytes != candidate_bytes,
        "safe_to_overwrite": False,
    }
    return result


def inspect_stage(stage: Path):
    stage = Path(stage).expanduser()
    if stage.is_symlink() or not stage.is_dir():
        raise ValueError("Private merge stage missing or symlinked")
    if stage.stat().st_mode & 0o077:
        raise ValueError("Private staging directory permissions must be 0700")
    raw = read_regular(stage, "manifest.json", MAX_MANIFEST)
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as error:
        raise ValueError("Malformed private merge manifest") from error
    if not isinstance(doc, dict) or doc.get("format") != FORMAT:
        raise ValueError("Unrecognized private merge stage")
    if doc.get("focus") != "desktop" or doc.get("release_installable") is not False:
        raise ValueError("Only non-installable desktop stages are reviewable here")
    entries = doc.get("files", [])
    if not isinstance(entries, list) or len(entries) != len(DESKTOP):
        raise ValueError("Unexpected private desktop staging manifest")
    by_name = {item.get("component"): item for item in entries
               if isinstance(item, dict) and isinstance(item.get("component"), str)}
    if len(by_name) != len(DESKTOP) or set(by_name) != set(DESKTOP):
        raise ValueError("Missing/duplicate staged desktop file")
    results = []
    for name in DESKTOP:
        item = by_name[name]
        original = read_regular(stage, "installed/" + name, MAX_BYTES)
        incoming = read_regular(stage, "candidate/" + name, MAX_BYTES)
        if (hashlib.sha256(original).hexdigest() != item.get("installed_sha256") or
                hashlib.sha256(incoming).hexdigest() != item.get("candidate_sha256")):
            raise ValueError("Staged file hash mismatch; regenerate a private stage")
        result = structural_diff(original, incoming, name)
        result["owner_only_dependencies"] = preservation_dependencies(
            original, incoming)
        results.append(result)
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True, type=Path,
                        help="Already-created owner-only private desktop staging folder")
    args = parser.parse_args(argv)
    try:
        results = inspect_stage(args.stage)
    except (OSError, ValueError) as error:
        print("DESKTOP MERGE REVIEW STOPPED: " + str(error), file=sys.stderr)
        return 3
    print("SPIDER OS / PRIVATE DESKTOP METHOD RECONCILIATION")
    print("Read-only AST comparison: no local code bodies, files or strings uploaded.")
    for result in results:
        print("\nFILE:", result["file"])
        for field, desc in (
            ("local_only_definitions", "LOCAL-ONLY methods/functions"),
            ("candidate_only_definitions", "CANDIDATE-ONLY methods/functions"),
            ("changed_shared_definitions", "CHANGED SHARED methods/functions"),
            ("signature_or_decorator_changes", "SIGNATURE/DECORATOR changes"),
        ):
            names = result[field]
            print("  {} ({}): {}".format(
                desc, len(names), ", ".join(names[:20]) or "none"))
            if len(names) > 20:
                print("    ... plus", len(names) - 20, "other definitions")
        print("  Module constant/setting bindings changed:",
              result["module_binding_changes"])
        print("  Module bindings added:", result["module_bindings_added"])
        print("  Module bindings removed:", result["module_bindings_removed"])
        print("  New import count:", result["candidate_only_import_count"])
        print("  Local-only import count:", result["local_only_import_count"])
        print("  Class base changes:", result["existing_class_base_changes"])
        for risk in result["owner_only_dependencies"]:
            print("  PRESERVE OWNER METHOD:", risk["owner_only_method"])
            print("    Candidate constructor missing owner-initialized fields:",
                  ", ".join(risk["locally_initialized_fields_missing_from_candidate"])
                  or "none detected")
            print("    Calls a changed shared method:",
                  ", ".join(risk["calls_to_changed_shared_methods"])
                  or "none detected")
            if risk["owner_constructor_changed"]:
                print("    Constructor changed; verify callback/state compatibility")
        print("  CANDIDATE IS NOT AN AUTHORIZED REPLACEMENT.")
    print("\nAll five files still require reviewed semantic merging.")
    print("Nothing installed, copied, committed, executed or modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
