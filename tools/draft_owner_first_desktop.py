#!/usr/bin/env python3
"""Create a private, NON-INSTALLABLE local-first integration review.

The owner-installed desktop code is the base of every file. The candidate's
unique definitions, imports and safely literal new constants are added only
to private copies. Existing owner definitions are never replaced.
Overlapping methods, assignments and constructor differences remain UNRESOLVED.

This is neither an installer nor an executable release. The output includes
private source code and must stay on the owner's PC.
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

FORMAT = "spider-local-first-noninstallable-review-v1"


def _definitions(tree):
    classes = {}
    methods = {}
    functions = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            classes[node.name] = node
            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods[node.name + "." + member.name] = member
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions[node.name] = node
    return classes, methods, functions


def _imports(tree):
    return [node for node in tree.body
            if isinstance(node, (ast.Import, ast.ImportFrom))]


def _bindings(tree):
    result = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                result[target.id] = node
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            result[node.target.id] = node
    return result


def _literal_assignment(node):
    value = node.value
    try:
        ast.literal_eval(value)
    except (ValueError, TypeError, SyntaxError, RecursionError):
        return False
    return isinstance(node, (ast.Assign, ast.AnnAssign))


def _snippet(lines, node):
    first = min([node.lineno] +
                [decorator.lineno
                 for decorator in getattr(node, "decorator_list", ())])
    return "".join(lines[first - 1:node.end_lineno])


def _stitch(local: bytes, incoming: bytes, relative: str):
    original = local.decode("utf-8")
    offered = incoming.decode("utf-8")
    owner_ast = ast.parse(original)
    proposed_ast = ast.parse(offered)
    owner_classes, owner_methods, owner_functions = _definitions(owner_ast)
    candidate_classes, candidate_methods, candidate_functions = _definitions(
        proposed_ast)
    owner_lines = original.splitlines(keepends=True)
    candidate_lines = offered.splitlines(keepends=True)
    diff = structural_diff(local, incoming, relative)
    edits = {}
    added = []
    deferred = []

    for name, cls in candidate_classes.items():
        if name not in owner_classes:
            edits.setdefault(len(owner_lines), []).append(
                _snippet(candidate_lines, cls))
            added.append(name)
    for name, method in candidate_methods.items():
        if name in owner_methods:
            continue
        class_name, _ = name.split(".", 1)
        if class_name not in owner_classes:
            # Already included with the complete newly introduced class.
            continue
        owner = owner_classes[class_name]
        source_parent = candidate_classes[class_name]
        if owner.col_offset != source_parent.col_offset:
            raise ValueError("Class indentation mismatch: " + relative)
        edits.setdefault(owner.end_lineno, []).append(
            _snippet(candidate_lines, method))
        added.append(name)
    for name, method in candidate_functions.items():
        if name not in owner_functions:
            edits.setdefault(len(owner_lines), []).append(
                _snippet(candidate_lines, method))
            added.append(name)

    before = _bindings(owner_ast)
    after = _bindings(proposed_ast)
    for name, node in after.items():
        if name in before:
            continue
        if _literal_assignment(node):
            edits.setdefault(len(owner_lines), []).append(
                _snippet(candidate_lines, node))
            added.append(name + " [literal setting]")
        else:
            deferred.append(name + " [nonliteral setting]")

    revised = list(owner_lines)
    for line in sorted(edits, reverse=True):
        chunks = []
        for snippet in edits[line]:
            if not snippet.endswith("\n"):
                snippet += "\n"
            chunks.extend(["\n", snippet])
        revised[line:line] = chunks
    assembled = "".join(revised)
    check_ast = ast.parse(assembled)
    previous_imports = {
        ast.dump(node, include_attributes=False) for node in _imports(check_ast)
    }
    extra_imports = [
        node for node in _imports(proposed_ast)
        if ast.dump(node, include_attributes=False) not in previous_imports
    ]
    if extra_imports:
        # Place nonfuture imports after the last regular import and future
        # imports after the last existing future import, following docstrings.
        lines = assembled.splitlines(keepends=True)
        top = ast.parse(assembled)
        existing = _imports(top)
        future = [item for item in existing if isinstance(item, ast.ImportFrom)
                  and item.module == "__future__"]
        regular = [item for item in existing if item not in future]
        last_future = max((item.end_lineno for item in future), default=0)
        last_regular = max((item.end_lineno for item in regular), default=last_future)
        first_stmt = top.body[0] if top.body else None
        after_docstring = (
            first_stmt.end_lineno
            if isinstance(first_stmt, ast.Expr)
            and isinstance(first_stmt.value, ast.Constant)
            and isinstance(first_stmt.value.value, str) else 0
        )
        placement = {}
        for node in extra_imports:
            is_future = isinstance(node, ast.ImportFrom) and node.module == "__future__"
            line = max(after_docstring, last_future if is_future else last_regular)
            placement.setdefault(line, []).append(
                _snippet(candidate_lines, node))
        for line in sorted(placement, reverse=True):
            lines[line:line] = [
                snippet if snippet.endswith("\n") else snippet + "\n"
                for snippet in placement[line]
            ]
        assembled = "".join(lines)
        check_ast = ast.parse(assembled)

    result_classes, result_methods, result_functions = _definitions(check_ast)
    if (not set(owner_classes) <= set(result_classes) or
            not set(owner_methods) <= set(result_methods) or
            not set(owner_functions) <= set(result_functions) or
            not set(candidate_classes) <= set(result_classes) or
            not set(candidate_methods) <= set(result_methods) or
            not set(candidate_functions) <= set(result_functions)):
        raise ValueError("Local-first preview lost an existing or candidate definition")

    # Never mutate any owner's actual method/function bodies. Insertion
    # positions can move line numbers but their ASTs must remain equivalent.
    def stable(left, right):
        return ast.dump(left, include_attributes=False) == ast.dump(
            right, include_attributes=False)
    for name, node in owner_classes.items():
        if name not in result_classes:
            raise ValueError("Owner class lost")
        # Methods can legitimately be appended to this class. Verify all its
        # original nonfunction members individually below.
        left = [item for item in node.body
                if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))]
        right = [item for item in result_classes[name].body
                 if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))]
        if len(right) != len(left) or any(
                not stable(a, b) for a, b in zip(left, right)):
            raise ValueError("Owner non-method class body changed")
    for name, node in owner_methods.items():
        if not stable(node, result_methods[name]):
            raise ValueError("Owner method overwritten: " + name)
    for name, node in owner_functions.items():
        if not stable(node, result_functions[name]):
            raise ValueError("Owner function overwritten: " + name)
    resulting_bindings = _bindings(check_ast)
    for name, node in before.items():
        if not stable(node, resulting_bindings[name]):
            raise ValueError("Owner module setting overwritten: " + name)

    unresolved = list(diff["changed_shared_definitions"])
    unresolved.extend(
        name + " [existing module binding]" for name in before.keys() & after.keys()
        if not stable(before[name], after[name]))
    unresolved.extend(deferred)
    risks = {
        "file": relative,
        "owner_base_preserved": True,
        "added_candidate_definitions_and_literal_bindings": sorted(added),
        "candidate_import_statements_added": len(extra_imports),
        "unresolved_conflicts": sorted(set(unresolved)),
        "new_constructor_dependencies_not_validated": True,
        "install_allowed": False,
    }
    return assembled.encode("utf-8"), risks


def stage_local_first(private_stage: Path, output: Path, *, home=None):
    stage = Path(private_stage).expanduser()
    outcomes = inspect_stage(stage)
    if tuple(entry["file"] for entry in outcomes) != DESKTOP:
        raise ValueError("Desktop stage identity mismatch")
    drafts = []
    for file in DESKTOP:
        local = read_regular(stage, "installed/" + file, MAX_BYTES)
        candidate = read_regular(stage, "candidate/" + file, MAX_BYTES)
        compiled, report = _stitch(local, candidate, file)
        drafts.append((file, compiled, report))
    output = Path(output).expanduser()
    _private_folder(
        output, home=Path.home() if home is None else Path(home),
        source=stage, installed=Path("/usr/local/lib/spider-os"),
    )
    for name, data, _ in drafts:
        _private_write(output, "review-only/" + name, data)
    manifest = {
        "format": FORMAT,
        "contains_private_source": True,
        "release_installable": False,
        "installed_modified": False,
        "safe_to_overwrite": False,
        "files": [result for _, _, result in drafts],
    }
    _private_write(output, "summary.json", json.dumps(manifest, indent=2) + "\n")
    _private_write(output, "README.txt", (
        "SPIDER OS / PRIVATE OWNER-FIRST REVIEW\n"
        "NOT RUNNABLE, NOT INSTALLABLE. DO NOT DEPLOY.\n"
        "These owner-based files retain the original installed class/function\n"
        "bodies, while bringing in only candidate-unique definitions, imports,\n"
        "and literal-only settings for analysis. Shared methods and any new\n"
        "constructor/callback dependencies require human semantic review.\n"
        "Keep this folder and its source code private. Do not upload to GitHub.\n"
        "No installed files, services or packages have been changed.\n"
    ))
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True,
                        help="NEW owner-private directory in home")
    args = parser.parse_args(argv)
    try:
        report = stage_local_first(args.stage, args.output)
    except (OSError, ValueError, SyntaxError, UnicodeError) as error:
        print("SPIDER LOCAL-FIRST REVIEW REFUSED:", str(error), file=sys.stderr)
        return 3
    print("SPIDER OS / OWNER-FIRST INTEGRATION DRAFT (PRIVATE, NOT INSTALLABLE)")
    for item in report["files"]:
        print("FILE:", item["file"])
        print("  Candidate-only definitions/literals staged:",
              len(item["added_candidate_definitions_and_literal_bindings"]))
        print("  Candidate-only imports staged:",
              item["candidate_import_statements_added"])
        print("  UNRESOLVED shared and module changes:",
              len(item["unresolved_conflicts"]))
        print("  Owner code retained: YES | Installation authorized: NO")
    print("Private review folder:", args.output)
    print("Nothing installed, executed, uploaded, or changed on the host.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
