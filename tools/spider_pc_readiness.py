#!/usr/bin/env python3
"""One-command read-only Spider OS installed-PC reconciliation report.

Requires a SEPARATE checkout of the exact reviewed source candidate. The
output is deliberately share-safe by default: no source code, hashes, paths
under HOME, unique audio device IDs, serials, recordings or credentials.
Never writes, installs, reboots, records, enrolls or starts a service.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INSTALL = Path("/usr/local/lib/spider-os")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Missing local read-only audit module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _current_checkout_sha(root):
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
            capture_output=True, text=True, timeout=5, check=False)
        value = result.stdout.strip().lower()
        if result.returncode == 0 and len(value) == 40 and all(
                c in "0123456789abcdef" for c in value):
            return value
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _daily_receipts(source_root, installed_root):
    """Count receipts only; never open or export their private manifest."""
    policy = source_root / "system/daily_install_policy.py"
    if not policy.is_file() or policy.is_symlink():
        return "unverified"
    try:
        module = _load("spider_owner_receipt_reader", policy)
        backup_root = Path(installed_root) / "upgrade-backups"
        receipts = module.existing_batch_receipts(
            backup_root, module.local_day())
        return "same_day_receipt_present" if receipts else "no_same_day_receipt_seen"
    except (OSError, RuntimeError, TypeError, ValueError):
        return "unverified"


def collect(source_root=ROOT, installed_root=DEFAULT_INSTALL, *,
            services=True, include_hashes=False, expected_sha=None,
            source_inspector=None, hardware_inspector=None,
            receipt_inspector=None, sha_reader=None):
    source_root, installed_root = Path(source_root), Path(installed_root)
    if source_root.resolve() == installed_root.resolve():
        raise ValueError("Candidate checkout must be separate from installed source")
    if not (source_root / "system/release_batch.py").is_file():
        raise ValueError("Not a Spider OS source checkout")
    acceptance = _load(
        "spider_readonly_pc_acceptance", source_root / "tools/daily_pc_acceptance.py")
    hardware_mod = _load(
        "spider_readonly_hardware", source_root / "tools/pc_hardware_compatibility.py")
    acceptance_inspect = source_inspector or acceptance.inspect
    hardware_inspect = hardware_inspector or hardware_mod.inspect_hardware
    receipt_check = receipt_inspector or _daily_receipts
    git_sha = (sha_reader or _current_checkout_sha)(source_root)
    file_report = acceptance_inspect(
        source_root, installed_root, phase="before", check_services=services)
    hardware = hardware_inspect(installed_root=installed_root)
    per_file = {}
    for name, item in file_report["files"].items():
        safe = {"file": item["file"], "state": item["state"]}
        if item.get("reason"):
            safe["reason"] = item["reason"]
        if include_hashes:
            safe["candidate_sha256"] = item.get("candidate_sha256")
            safe["installed_sha256"] = item.get("installed_sha256")
        per_file[name] = safe
    counts = dict(sorted(Counter(i["state"] for i in per_file.values()).items()))
    approvals_missing = [
        "No review of code differences against owner-customized installed files",
        "No physical owner voice verification or consented microphone test",
        "No owner-approved all-workspace installation",
        "No on-PC backup and rollback validation",
        "No functional GUI, GPU, Kali Bay, Nova and broadcast acceptance",
    ]
    if not git_sha or (expected_sha and git_sha != expected_sha):
        approvals_missing.append("Exact Git commit identity not confirmed")
    if not services:
        approvals_missing.append("Service/Nova runtime status was not checked")
    blocked = list(file_report["blockers"])
    if file_report.get("status") == "BLOCKED" and not blocked:
        blocked.append("Installed source inspection was blocked")
    result = {
        "schema_version": 1,
        "status": "BLOCKED" if blocked else "REVIEW REQUIRED",
        "safe_to_install": False,
        "checkout_commit": git_sha or "unverified",
        "expected_commit_matches": (git_sha == expected_sha
                                    if expected_sha else "not_requested"),
        "files_summary": counts,
        "files": per_file,
        "services": file_report.get("services", {}),
        "nova_health": file_report.get("nova_health", "not_checked"),
        "hardware": hardware,
        "same_day_install_receipt": receipt_check(source_root, installed_root),
        "blockers": blocked,
        "remaining_manual_verification": approvals_missing,
        "privacy": "No source bytes, secrets, device identifiers or HOME files reported",
        "install_action": "NONE; this report is observation only",
    }
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, default=ROOT)
    parser.add_argument("--installed-root", type=Path, default=DEFAULT_INSTALL)
    parser.add_argument("--expected-sha",
                        help="Optional pinned 40-character Git commit for candidate review")
    parser.add_argument("--skip-services", action="store_true")
    parser.add_argument("--include-hashes", action="store_true",
                        help="Show application file hashes locally; remove before sharing")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.expected_sha and (
            len(args.expected_sha) != 40 or
            any(c not in "0123456789abcdef" for c in args.expected_sha.lower())):
            raise ValueError("Expected SHA must contain 40 hexadecimal characters")
        report = collect(
            args.checkout, args.installed_root, services=not args.skip_services,
            include_hashes=args.include_hashes,
            expected_sha=args.expected_sha.lower() if args.expected_sha else None)
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print("READ-ONLY AUDIT BLOCKED: " + str(error), file=sys.stderr)
        return 3
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("SPIDER OS INSTALLED-PC REVIEW: " + report["status"])
        print("Candidate: " + report["checkout_commit"])
        print("File comparison counts: " + json.dumps(report["files_summary"]))
        print("Hardware review flags: " + str(len(report["hardware"]["review_flags"])))
        print("Daily install receipt: " + report["same_day_install_receipt"])
        for name, entry in report["files"].items():
            if entry["state"] != "matching":
                print("REVIEW: " + name + " = " + entry["state"])
        for issue in report["blockers"]:
            print("BLOCKED: " + issue)
        print("INSTALL NOT AUTHORIZED. This command changed nothing.")
    return 3 if report["blockers"] else 0


if __name__ == "__main__":
    sys.exit(main())
