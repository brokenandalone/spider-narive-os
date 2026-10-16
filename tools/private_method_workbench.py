#!/usr/bin/env python3
"""Private side-by-side view of *actual* Spider OS desktop merge conflicts.

The owner-reviewed Bridge stage is the input. Its SHA256 metadata and 0700
permissions are checked before reading any original code. This script never
imports/executes staged modules, installs, merges, commits or uploads code.
Only a brand-new owner-private folder with static HTML is created.

The HTML CONTAINS PRIVATE CODE. Never upload, share or serve it on a network.
"""
from __future__ import annotations

import argparse
import ast
import difflib
import html
from pathlib import Path
import sys

from review_staged_desktop_methods import (
    DESKTOP, MAX_BYTES, inspect_stage, read_regular, structural_diff,
)
from stage_native_merge import _private_folder, _private_write

PRIORITIES = (
    ("the-web/shell/main.py", "TheWeb.__init__", "Preserve startup/session state"),
    ("the-web/shell/main.py", "TheWeb.build_ui", "Connect native Home and bays"),
    ("the-web/shell/main.py", "TheWeb.open_workspace", "Actually embed Studio, Art and Webbie"),
    ("the-web/shell/main.py", "TheWeb.application_panel", "Preserve original installed apps"),
    ("the-web/shell/main.py", "TheWeb.open_installed", "Route old launchers to real bays"),
    ("the-web/shell/app_catalog.py", "workspace_for", "Keep app assignments"),
    ("the-web/shell/app_catalog.py", "discover_apps", "Keep app discovery compatible"),
    ("the-web/shell/workspace_files.py", "workspace_folders", "Keep existing project paths"),
    ("the-web/shell/webbie_panel.py", "WebbiePanel.__init__", "Keep Webbie native sessions"),
    ("the-web/shell/webbie_panel.py", "WebbiePanel.open_computer_dialog", "Preserve authorization boundary"),
    ("the-web/shell/webbie_panel.py", "WebbiePanel.stop_sensitive_actions", "Preserve STOP and revocation"),
    ("the-web/shell/webbie_panel.py", "WebbiePanel.send", "Preserve trusted message routing"),
    ("the-web/shell/webbie_panel.py", "WebbiePanel.set_face_sleeping", "Preserve sleep/camera revocation"),
    ("the-web/shell/webbie_cognitive_center.py", "WebbieCognitiveDialog.__init__", "Preserve owner workflow constructor"),
    ("the-web/shell/webbie_cognitive_center.py", "WebbieCognitiveDialog.open_workflow", "Preserve workflow callback semantics"),
)
LIMIT_HTML_BYTES = 4_000_000


def definition_text(code: bytes, symbol: str):
    source = code.decode("utf-8")
    root = ast.parse(source)
    pieces = symbol.split(".")
    nodes = root.body
    match = None
    for index, piece in enumerate(pieces):
        kind = (ast.ClassDef,) if index < len(pieces) - 1 else (
            ast.FunctionDef, ast.AsyncFunctionDef)
        match = next(
            (node for node in nodes if isinstance(node, kind)
             and node.name == piece), None)
        if match is None:
            raise ValueError("Expected definition missing: " + symbol)
        nodes = match.body if isinstance(match, ast.ClassDef) else ()
    start = min(
        [match.lineno] +
        [item.lineno for item in getattr(match, "decorator_list", ())])
    return "".join(source.splitlines(keepends=True)[start - 1:match.end_lineno])


def build_html(entries):
    title = "SPIDER OS | PRIVATE NATIVE METHOD REVIEW"
    chunks = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; script-src 'none'; img-src 'none'; connect-src 'none'; style-src 'unsafe-inline'; form-action 'none';\">",
        "<meta name='referrer' content='no-referrer'>",
        "<title>" + title + "</title>",
        "<style>body{background:#110d19;color:#ebe8f4;font:15px system-ui;margin:26px}",
        "h1,h2{color:#ccadff}p,li{line-height:1.5}",
        "a{color:#b69cff} .guard{border:1px solid #9f7aea;padding:14px}",
        "table.diff{font:12px monospace;border-collapse:collapse;background:#201a30;color:#fff;max-width:100%;overflow:auto}",
        "table.diff td{padding:3px 8px;white-space:pre-wrap;overflow-wrap:anywhere;vertical-align:top}",
        ".diff_header{background:#41365e}.diff_add{background:#28563d}",
        ".diff_sub{background:#6b2a38}.diff_chg{background:#77562a}",
        "section{margin:42px 0;border-top:1px solid #5e4a7c;padding-top:18px}",
        ".scroll{max-width:100%;overflow:auto}.tag{color:#c4b5fd}</style></head><body>",
        "<h1>SPIDER OS / LOCAL-ONLY MERGE WORKBENCH</h1>",
        "<p class='guard'><strong>DO NOT INSTALL OR UPLOAD THIS FILE.</strong> ",
        "It contains private owner source code. These are <strong>differences to review</strong>, ",
        "not resolved merges. A candidate-only import or method does not prove the ",
        "working native bay is safely integrated. No system changes occurred.</p>",
        "<p>Prioritized actual conflicts (owner-installed code on left; GitHub candidate on right). ",
        "Review native desktop construction, navigation, application catalog, then ",
        "Webbie safety functions. Preserve both expected behaviors.</p><ol>",
    ]
    for index, row in enumerate(entries, 1):
        path, symbol, _, _, desc = row
        chunks.append("<li><a href='#item-" + str(index) + "'>" +
                      html.escape(path + " :: " + symbol) +
                      "</a> | " + html.escape(desc) + "</li>")
    chunks.append("</ol>")
    differ = difflib.HtmlDiff(tabsize=4, wrapcolumn=96)
    for index, (path, symbol, owner, candidate, desc) in enumerate(entries, 1):
        chunks.append("<section id='item-" + str(index) + "'><h2>" +
                      html.escape(path + " :: " + symbol) + "</h2>")
        chunks.append("<p class='tag'>" + html.escape(desc) +
                      " | UNRESOLVED, KEEP PRIVATE</p><div class='scroll'>")
        chunks.append(differ.make_table(
            owner.splitlines(), candidate.splitlines(),
            fromdesc="WORKING OWNER", todesc="GITHUB CANDIDATE",
            context=False, numlines=3))
        chunks.append("</div></section>")
    chunks.append("<p>End of private review. All original files remain unchanged.</p></body></html>")
    output = "".join(chunks)
    if len(output.encode("utf-8")) > LIMIT_HTML_BYTES:
        raise ValueError("Local review HTML too large; use Meld on staged pairs")
    return output


def prepare(stage, output, *, home=None):
    stage = Path(stage).expanduser()
    checked = inspect_stage(stage)
    changed = {name: set(item["changed_shared_definitions"])
               for name, item in zip(DESKTOP, checked)}
    for file, name, _ in PRIORITIES:
        if name not in changed.get(file, set()):
            raise ValueError("Priority conflict changed; regenerate review: " + file + " " + name)
    entries = []
    originals = {}
    for file, name, purpose in PRIORITIES:
        if file not in originals:
            originals[file] = (
                read_regular(stage, "installed/" + file, MAX_BYTES),
                read_regular(stage, "candidate/" + file, MAX_BYTES))
        installed, candidate = originals[file]
        entries.append((
            file, name, definition_text(installed, name),
            definition_text(candidate, name), purpose))
    content = build_html(entries)
    output = Path(output).expanduser()
    _private_folder(output, home=Path.home() if home is None else Path(home),
                    source=stage, installed=Path("/usr/local/lib/spider-os"))
    _private_write(output, "index.html", content)
    _private_write(output, "README.txt",
                   "PRIVATE: contains owner-installed Python source.\n"
                   "Open index.html locally. Never upload or serve this folder.\n"
                   "Nothing has been merged or installed.\n")
    return {"reviewed": len(entries), "output": str(output / "index.html"),
            "install_allowed": False, "host_modified": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True,
                        help="Brand-new local private directory under HOME")
    args = parser.parse_args(argv)
    try:
        result = prepare(args.stage, args.output)
    except (ValueError, OSError, UnicodeError, SyntaxError) as exc:
        print("PRIVATE METHOD WORKBENCH REFUSED:", str(exc), file=sys.stderr)
        return 3
    print("SPIDER OS / PRIVATE METHOD MERGE WORKBENCH")
    print("Prioritized method conflicts visible:", result["reviewed"])
    print("Local HTML file:", result["output"])
    print("Private owner source stays on THIS PC. Do not upload.")
    print("NOT INSTALLABLE. 33 customized release files remain protected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
