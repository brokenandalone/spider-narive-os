#!/usr/bin/env python3
"""Spider OS Wave Five read-only, whole-system downgrade prevention report.

This only inventories fixed Spider OS application files, the frozen source
manifest and (on explicit --pc) installed Ollama status. It never installs,
pulls models, restarts services, imports user files, loads voiceprints, or
claims that hashes prove physical hardware continuity.
"""
from __future__ import annotations
import argparse
import ast
from datetime import date
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]
INSTALLED = Path("/usr/local/lib/spider-os")
PLAN = "system/daily_release_plan_20261011.json"
BATCH = "system/release_batch.py"
GUARDED = ("webbie/agent/webbie.py", "webbie/brain/brain.py",
           "webbie/voice/whisper_listener.py", "the-web/shell/main.py",
           "the-web/shell/webbie_panel.py", "the-web/shell/webbie_computer_panel.py",
           "studio/main.py", "author/main.py", "study/study.py",
           "kali-bay/ui/kali_bay.py", "forage/forage.py",
           "media/ai-dj/nova_host.py")
PRIVATE_PREFIXES = ("webbie/config/", "webbie/models/", "webbie/private/",
                    "study/documents/", "author/manuscripts/", "studio/projects/",
                    "webbie/voiceprints/", "data/", "user/")
RELEASE_GATES = ("candidate_commit", "source_ci_verified",
                 "installed_pc_reconciled", "rollback_validated",
                 "owner_approved_install", "installer_daily_guard_connected",
                 "voice_pipeline_verified", "model_compatibility_verified")


def _strict_file(root, name, *, limit=6_000_000):
    if not isinstance(name, str) or not name or name.startswith("/"):
        raise ValueError("Bad source path")
    segments = name.split("/")
    if any(part in ("", ".", "..") for part in segments):
        raise ValueError("Unsafe source path")
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Unsafe source root")
    target = root
    for part in segments:
        target = target / part
        if target.is_symlink():
            raise ValueError("Symlinked source path")
    info = target.stat()
    if not stat.S_ISREG(info.st_mode) or not (0 < info.st_size <= limit):
        raise ValueError("Unsafe source file")
    return target


def _sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest(source):
    code = _strict_file(source, BATCH).read_text(encoding="utf-8")
    for node in ast.parse(code).body:
        if isinstance(node, ast.Assign) and any(
                isinstance(x, ast.Name) and x.id == "APP_FILES" for x in node.targets):
            values = ast.literal_eval(node.value)
            if not isinstance(values, (list, tuple)) or not all(
                    isinstance(v, str) for v in values):
                raise ValueError("Invalid application file manifest")
            return values
    raise ValueError("Missing single installer application manifest")


def _plan(source):
    data = json.loads(_strict_file(source, PLAN).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("workspaces"), list):
        raise ValueError("Invalid single release plan")
    return data


def inspect(source=ROOT, installed=INSTALLED, *, scan_pc=False,
            model_checker=None):
    """One stable, JSON-safe snapshot. Never changes machine state."""
    source, installed = Path(source), Path(installed)
    problems, warnings, counts = [], [], {}
    try:
        listed = _manifest(source)
    except (OSError, UnicodeError, SyntaxError, ValueError) as error:
        return {"status": "BLOCKED", "blockers": ["Single installer manifest invalid: "
                + type(error).__name__], "warnings": [], "counts": {}, "gates": {}}
    if len(listed) != len(set(listed)):
        problems.append("Duplicate application path in system-wide installer")
    if not listed or not all(isinstance(s, str) for s in listed):
        problems.append("Installer application file list empty or malformed")
    protected = [x for x in listed if x.startswith(PRIVATE_PREFIXES)
                 or x in ("webbie/config/default.json", "webbie/brain/models",)]
    if protected:
        problems.append("Installer includes protected user/model/config material")
    missing_source = []
    for name in dict.fromkeys(listed):
        try:
            _strict_file(source, name, limit=16_000_000)
        except (OSError, ValueError, TypeError):
            missing_source.append(name)
    if missing_source:
        problems.append("Candidate has missing/unsafe tracked application files")
    counts["candidate_files"] = len(listed)
    counts["candidate_missing_or_unsafe"] = len(missing_source)
    missing_critical = [x for x in GUARDED if x not in listed]
    if missing_critical:
        problems.append("Essential PC components dropped from central installer")
    try:
        release = _plan(source)
    except (OSError, UnicodeError, ValueError, TypeError) as error:
        problems.append("Release plan invalid: " + type(error).__name__)
        release = {}
    gates = {key: release.get(key) for key in RELEASE_GATES}
    pending = [x.get("pr") for x in release.get("pull_requests", [])
               if isinstance(x, dict) and x.get("integrated") is not True]
    counts["tracked_prs"] = len(release.get("pull_requests", []))
    counts["unresolved_prs"] = len(pending)
    counts["workspaces"] = len(release.get("workspaces", []))
    if pending:
        warnings.append("Unintegrated PRs remain; staging is not approval")
    if any(gates[key] is not True for key in RELEASE_GATES):
        warnings.append("Release approval gates remain closed; do not apply")
    states = {}
    if scan_pc:
        for name in GUARDED:
            try:
                expected = _sha(_strict_file(source, name))
                actual = _sha(_strict_file(installed, name))
                states[name] = "matching" if expected == actual else "different"
            except (OSError, ValueError):
                states[name] = "unavailable"
        # Read the central installer receipt directory only; never create locks
        # or scan user private files. An interrupted same-day attempt counts too.
        try:
            receipt_root = installed / "upgrade-backups"
            policy_path = source / "system/daily_install_policy.py"
            spec = importlib.util.spec_from_file_location("wave5_receipts", policy_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            day = date.fromisoformat(release["release_date"])
            receipts = module.existing_batch_receipts(receipt_root, day)
            counts["same_day_batch_receipts"] = len(receipts)
            if receipts:
                problems.append("A successful, partial or ambiguous same-day system install already used the slot")
            elif not receipt_root.is_dir():
                warnings.append("Daily install receipt folder not found; confirm with installed owner")
        except (OSError, ValueError, RuntimeError, TypeError, KeyError, ImportError):
            counts["same_day_batch_receipts"] = None
            problems.append("Daily installation receipts could not be independently verified")
        counts["pc_matches"] = sum(x == "matching" for x in states.values())
        counts["pc_differs"] = sum(x == "different" for x in states.values())
        counts["pc_unavailable"] = sum(x == "unavailable" for x in states.values())
        if counts["pc_differs"] or counts["pc_unavailable"]:
            warnings.append("Live PC differs or is unavailable. Preserve customizations and reconcile every difference")
        if model_checker is None:
            try:
                path = source / "tools/webbie_model_compatibility.py"
                spec = importlib.util.spec_from_file_location("wave5_installed_model", path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                model_status = mod.review(installed_root=installed,
                                          candidate_root=source)["status"]
            except (OSError, ValueError, TypeError, AttributeError, ImportError):
                model_status = "BLOCKED"
        else:
            model_status = model_checker(source, installed)
        if model_status == "BLOCKED":
            problems.append("Installed Webbie model compatibility not verified")
    else:
        model_status = "NOT_CHECKED"
        warnings.append("Installed PC never inspected; use --pc on Spider OS")
    # No file-only report may certify hardware, ownership or the install slot.
    return {"status": "REVIEW_ONLY" if not problems else "BLOCKED",
            "installation_ready": False,
            "blockers": problems, "warnings": warnings,
            "counts": counts, "gates": gates,
            "model_status": model_status, "critical_files": states,
            "pending_pr_numbers": pending[:100],
            "limitations": ["Hash comparisons do not prove audio, GPU, camera, keyboard, boot or rollback",
                            "This script never installs or reserves a daily slot"]}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, default=ROOT)
    p.add_argument("--installed", type=Path, default=INSTALLED)
    p.add_argument("--pc", action="store_true", help="Read-only comparison against installed Spider OS")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    result = inspect(args.source, args.installed, scan_pc=args.pc)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("SPIDER OS SYSTEM-WIDE RELEASE: " + result["status"])
        for s in result["blockers"]:
            print("BLOCKED:", s)
        for s in result["warnings"]:
            print("REVIEW:", s)
        print("No installation or service changes performed.")
    return 3 if result["status"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
