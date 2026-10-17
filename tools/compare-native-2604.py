#!/usr/bin/env python3
"""Read-only native 26.04 reconciliation: compare *structure*, not private code.

Reads only known application files named in the vetted batch release catalog.
Does not execute installed modules, read user libraries, upload diffs, install,
delete, change Git state, restart services, or access privileged configuration.
The output contains code symbol *names* and counts, never line contents.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
from pathlib import Path
import subprocess

APPROVED_BRANCHES = frozenset({
    "reconciliation/ubuntu-studio-26.04-lts-20261015",
    "feature/native-monster-bays-20261015",
})
SHELL = "the-web/shell/main.py"
PRIORITY_GROUPS = {
    "desktop": (
        "the-web/shell/main.py",
        "the-web/shell/app_catalog.py",
        "the-web/shell/workspace_files.py",
        "the-web/shell/webbie_panel.py",
        "the-web/shell/webbie_cognitive_center.py",
    ),
    "webbie": (
        "webbie/agent/webbie.py",
        "webbie/brain/brain.py",
        "webbie/voice/whisper_listener.py",
        "webbie/voice/interruptible_speech.py",
        "the-web/shell/webbie_computer_panel.py",
        "the-web/shell/webbie_operator_bridge.py",
        "the-web/shell/webbie_camera.py",
    ),
    "creative": (
        "studio/main.py", "studio/ai_panel.py",
        "author/main.py", "author/web_features.py",
        "forage/engine.py", "forage/forage.py",
        "forage/deep-forage/deep_forage.py",
        "study/study.py", "study/homework_ui.py",
    ),
    "services": (
        "media/ai-dj/service.py", "media/ai-dj/spider-ai-dj.service",
        "kali-bay/bin/kali-bay", "kali-bay/ui/kali_bay.py",
        "webbie/actions/task_grants.py",
    ),
}
PRIMARY = (
    SHELL,
    "the-web/shell/webbie_panel.py",
    "webbie/agent/webbie.py",
    "webbie/voice/whisper_listener.py",
    "webbie/brain/brain.py",
    "author/main.py",
    "author/web_features.py",
    "studio/main.py",
    "media/ai-dj/service.py",
    "kali-bay/ui/kali_bay.py",
    "study/study.py",
    "forage/forage.py",
)


def managed_paths(repository: Path) -> tuple[str, ...]:
    """Read the installer's literal allowlist, without importing/installing it."""
    source = repository / "system/release_batch.py"
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "APP_FILES"
            for target in node.targets
        ):
            paths = tuple(ast.literal_eval(node.value))
            if not all(
                isinstance(p, str)
                and p
                and not Path(p).is_absolute()
                and ".." not in Path(p).parts
                for p in paths
            ):
                raise ValueError("Release catalog includes an unsafe path")
            return paths
    raise ValueError("APP_FILES allowlist not found")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(131072), b""):
            h.update(block)
    return h.hexdigest()


def symbols(source: str) -> dict[str, str]:
    """A stable fingerprint of each Python definition; don't expose contents."""
    tree = ast.parse(source)
    found = {}

    def visit(body, scope=""):
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                key = scope + node.name
                found[key] = hashlib.sha256(
                    ast.dump(node, include_attributes=False).encode()
                ).hexdigest()
                if isinstance(node, ast.ClassDef):
                    visit(node.body, key + ".")
    visit(tree.body)
    return found


def summarize_python(local: str, candidate: str) -> dict:
    existing, incoming = symbols(local), symbols(candidate)
    return {
        "local_only": sorted(set(existing) - set(incoming)),
        "candidate_only": sorted(set(incoming) - set(existing)),
        "changed_common": sum(
            existing[name] != incoming[name] for name in existing.keys() & incoming.keys()
        ),
    }


def safe_installed_file(root: Path, relative: str) -> Path | None:
    target = root / relative
    # Never follow symlinks out of the native program tree.
    if any(part.is_symlink() for part in (target, *target.parents)
           if part == root or root in part.parents):
        return None
    return target


def inspect(repository: Path, installed_root: Path) -> dict:
    current, changed, missing, skipped = [], [], [], []
    for relative in managed_paths(repository):
        source = repository / relative
        target = safe_installed_file(installed_root, relative)
        if not source.is_file():
            skipped.append((relative, "source missing"))
        elif target is None:
            skipped.append((relative, "installed symlink"))
        elif not target.exists():
            missing.append(relative)
        elif not target.is_file():
            skipped.append((relative, "not a regular installed file"))
        elif digest(source) == digest(target):
            current.append(relative)
        else:
            changed.append(relative)
    return {"current": current, "changed": changed, "missing": missing, "skipped": skipped}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--installed-root", type=Path, default=Path("/usr/local/lib/spider-os"))
    p.add_argument("--all", action="store_true", help="Show structural summary of all changed application files")
    p.add_argument("--focus", choices=("desktop", "webbie", "creative", "services"),
                   default="desktop", help="Subset of locally customized files to inspect, default desktop")
    args = p.parse_args(argv)
    source, installed = args.source.resolve(), args.installed_root.resolve()
    branch = subprocess.run(
        ["git", "-C", str(source), "branch", "--show-current"],
        check=True, text=True, capture_output=True
    ).stdout.strip()
    if branch not in APPROVED_BRANCHES:
        p.error("Expected a reviewed Spider OS 26.04 development branch, got " +
                (branch or "(detached)"))
    if not (installed / SHELL).is_file():
        p.error("Installed native shell not found under the selected root")
    report = inspect(source, installed)
    print("SPIDER OS 26.04 | LOCAL CODE RECONCILIATION (READ ONLY)")
    print("Identical allowed application files:", len(report["current"]))
    print("Changed allowed application files:", len(report["changed"]))
    print("Missing allowed application files:", len(report["missing"]))
    print("Uninspectable paths:", len(report["skipped"]))
    print("Changed: unknown local customizations must NOT be overwritten.")
    print("No files installed, services restarted, or data uploaded.\n")

    for name, reason in report["skipped"]:
        print("SKIP", name, "(" + reason + ")")

    names = report["changed"] if args.all else PRIORITY_GROUPS[args.focus]
    show = [path for path in names if path in report["changed"]]
    print("Review selection:", "all" if args.all else args.focus,
          "|", len(show), "locally changed files")
    for relative in show:
        source_file = source / relative
        installed_file = installed / relative
        print("REVIEW:", relative)
        if relative.endswith(".py"):
            try:
                status = summarize_python(installed_file.read_text(encoding="utf-8"),
                                          source_file.read_text(encoding="utf-8"))
                for label in ("local_only", "candidate_only"):
                    values = status[label]
                    print("  {} symbols ({}): {}".format(
                        label, len(values), ", ".join(values[:8]) or "none"))
                    if len(values) > 8:
                        print("    ... {} more".format(len(values) - 8))
                print("  modified shared definitions:", status["changed_common"])
            except (SyntaxError, UnicodeError) as error:
                print("  UNABLE TO PARSE PYTHON:", type(error).__name__)
        else:
            print("  Non-Python file; differences withheld for manual review.")
    remaining = [p for p in report["changed"] if p not in show]
    if remaining:
        print("\nOther locally changed files:", ", ".join(remaining))
    print("\nMissing candidate modules:")
    for relative in report["missing"]:
        print("  ADD ONLY AFTER REVIEW:", relative)
    if SHELL in report["changed"] and (args.all or args.focus == "desktop"):
        old = (installed / SHELL).read_text(encoding="utf-8", errors="replace")
        new = (source / SHELL).read_text(encoding="utf-8", errors="replace")
        for token in ("from immersive_bays import", "from workspace_max_native import",
                      "from webbie_native_operations import",
                      "from home_dashboard import",
                      "from art_workbench import", "from instrument_panel import",
                      "ImmersiveBay(", "NativeWorkspaceTools("):
            print("Native shell integration {!r}: installed={}, GitHub={}".format(
                token, token in old, token in new))
    print("\nNOT AUTHORIZED: automatic replacement of locally customized code.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
