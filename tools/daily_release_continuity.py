#!/usr/bin/env python3
"""Read-only Spider OS daily cross-workspace continuity audit.

Tests the *candidate*, not remote PR branches, hardware or the installed PC.
This tool never installs a package, starts a service, or accesses user files.
"""
import argparse
import ast
from collections import defaultdict
from datetime import date, datetime
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

PLAN = Path(__file__).resolve().parents[1] / "system/daily_release_plan_20261011.json"
REQUIRED = {
    "System/Recovery", "The Web", "Webbie", "Study", "Studio",
    "Author", "Kali Bay", "Forage/Deep Forage", "Media Center/Nova Radio",
}
SHA = re.compile(r"^[a-f0-9]{40}$")


def release_manifest(root):
    path = Path(root) / "system/release_batch.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "APP_FILES"
            for target in node.targets
        ):
            value = ast.literal_eval(node.value)
            if not isinstance(value, (tuple, list)) or not all(
                isinstance(p, str) for p in value
            ):
                raise ValueError("Invalid APP_FILES")
            return set(value)
    raise ValueError("Missing APP_FILES")


def overlapping_paths(plan):
    paths = defaultdict(set)
    for pr in plan.get("pull_requests", []):
        for path in pr.get("paths", []):
            paths[path].add(pr["pr"])
    return {
        path: sorted(numbers)
        for path, numbers in sorted(paths.items())
        if len(numbers) > 1
    }


def audit(plan, root, receipt_root=None, now=None):
    """Return (blockers, findings). No modifications, no network requests."""
    root = Path(root)
    blocked, findings = [], []
    if plan.get("schema_version") != 1:
        blocked.append("UNSUPPORTED RELEASE PLAN FORMAT")
    if plan.get("timezone") != "America/Indiana/Indianapolis":
        blocked.append("OWNER TIMEZONE NOT PRESERVED")
    if plan.get("max_system_installs_per_local_day") != 1:
        blocked.append("DAILY INSTALL LIMIT MUST BE ONE")
    try:
        release_day = date.fromisoformat(plan["release_date"])
    except (ValueError, KeyError, TypeError):
        blocked.append("INVALID RELEASE DATE")
        release_day = None
    local_now = now or datetime.now(ZoneInfo("America/Indiana/Indianapolis"))
    if local_now.tzinfo is None:
        blocked.append("CURRENT TIME MUST HAVE A TIMEZONE")
    elif release_day and local_now.astimezone(
        ZoneInfo("America/Indiana/Indianapolis")
    ).date() != release_day:
        blocked.append("RELEASE DAY DOES NOT MATCH OWNER LOCAL DAY")

    streams = plan.get("workspaces", [])
    names = [entry.get("name") for entry in streams]
    if len(names) != len(set(names)):
        blocked.append("DUPLICATE WORKSPACE IN DAILY PLAN")
    for missing in sorted(REQUIRED - set(names)):
        blocked.append("MISSING SYSTEM WORKSPACE: " + missing)
    prs = plan.get("pull_requests", [])
    by_id = {entry.get("pr"): entry for entry in prs}
    if len(by_id) != len(prs):
        blocked.append("DUPLICATE PR REFERENCE")
    for entry in prs:
        number = entry.get("pr")
        if not SHA.fullmatch(str(entry.get("observed_sha", ""))):
            blocked.append("UNPINNED BRANCH HEAD: PR " + str(number))
        if entry.get("integrated") is not True:
            blocked.append("NOT YET INTEGRATED INTO ONE CANDIDATE: PR " + str(number))
    try:
        manifest = release_manifest(root)
    except (OSError, SyntaxError, UnicodeError, ValueError) as error:
        blocked.append("UNREADABLE SINGLE INSTALLER: " + type(error).__name__)
        manifest = set()
    for entry in streams:
        for number in entry.get("pull_requests", []):
            if number not in by_id:
                blocked.append("UNKNOWN PR IN " + str(entry.get("name")) + ": " + str(number))
        for name in entry.get("required_files", []):
            file = root / name
            if not file.is_file() or file.is_symlink():
                blocked.append("MISSING IN CANDIDATE: " + name)
            if not name.startswith(("system/", "tools/")) and name not in manifest:
                blocked.append("NOT IN ONE BATCH INSTALLER: " + name)

    approved = {
        x.get("path"): set(x.get("pull_requests", []))
        for x in plan.get("resolved_shared_paths", [])
        if x.get("reviewed") is True
    }
    collisions = overlapping_paths(plan)
    for path, numbers in collisions.items():
        if approved.get(path) != set(numbers):
            blocked.append(
                "UNRESOLVED CROSS-BRANCH OVERLAP: " + path
                + " (PRs " + ", ".join(str(n) for n in numbers) + ")"
            )
    findings.append("Cross-branch shared paths detected: " + str(len(collisions)))
    findings.append("Tracked system workspaces: " + str(len(names)))
    findings.append("Tracked PR heads: " + str(len(prs)))

    # Candidate and approvals must be actual evidence, never inferred from
    # passing tests on independent branches.
    if not SHA.fullmatch(str(plan.get("candidate_commit") or "")):
        blocked.append("NO PINNED COMBINED CANDIDATE")
    gates = {
        "model_compatibility_verified": "WEBBIE INSTALLED MODEL COMPATIBILITY NOT VERIFIED",
        "source_ci_verified": "FULL COMBINED SOURCE TESTS NOT VERIFIED",
        "installed_pc_reconciled": "INSTALLED PC CUSTOMIZATIONS NOT RECONCILED",
        "rollback_validated": "COMBINED ROLLBACK NOT VALIDATED",
        "owner_approved_install": "INSTALLATION NOT APPROVED",
        "installer_daily_guard_connected": "ONCE-DAILY INSTALLER GUARD NOT VERIFIED",
        "voice_pipeline_verified": "OWNER VOICE AUTHENTICATION AND MICROPHONE CONTINUITY NOT VERIFIED",
    }
    for key, reason in gates.items():
        if plan.get(key) is not True:
            blocked.append(reason)

    installer = root / "system/release_batch.py"
    if installer.is_file() and "daily_install_guard(backup_root)" not in installer.read_text(
        encoding="utf-8"
    ):
        blocked.append("DAILY GUARD NOT WIRED TO MAIN BATCH INSTALLER")

    if receipt_root is None:
        blocked.append("INSTALLED PC DAILY RECEIPT STATUS UNVERIFIED")
    else:
        from importlib.util import module_from_spec, spec_from_file_location
        policy = root / "system/daily_install_policy.py"
        if not policy.is_file():
            blocked.append("DAILY RECEIPT POLICY MISSING")
        elif release_day is not None:
            spec = spec_from_file_location("spider_daily_receipt_reader", policy)
            module = module_from_spec(spec)
            spec.loader.exec_module(module)
            try:
                recorded = module.existing_batch_receipts(receipt_root, release_day)
                if recorded:
                    blocked.append("DAILY INSTALL SLOT ALREADY USED OR AMBIGUOUS")
                else:
                    findings.append("No same-day batch receipts in supplied backup root")
            except (OSError, RuntimeError, ValueError):
                blocked.append("DAILY RECEIPT INVENTORY NEEDS REVIEW")
    return sorted(set(blocked)), findings


def active_daily_plan():
    """Prefer today's plan; earlier plans only produce a blocked stale-day audit."""
    today = datetime.now(ZoneInfo("America/Indiana/Indianapolis")).strftime("%Y%m%d")
    desired = PLAN.parent / ("daily_release_plan_" + today + ".json")
    return desired if desired.is_file() or desired.is_symlink() else PLAN


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=active_daily_plan())
    parser.add_argument("--checkout", type=Path, default=PLAN.parents[1])
    parser.add_argument("--backup-root", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        blockers, findings = audit(plan, args.checkout, args.backup_root)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        blockers, findings = ["RELEASE AUDIT CANNOT COMPLETE: " + type(exc).__name__], []
    status = "BLOCKED" if blockers else "SOURCE CONTINUITY READY; PC END-TO-END TEST STILL REQUIRED"
    if args.json:
        print(json.dumps({"status": status, "blockers": blockers, "findings": findings}, indent=2))
    else:
        print("SPIDER OS DAILY CONTINUITY: " + status)
        for note in findings:
            print("INFO: " + note)
        for block in blockers:
            print("BLOCKED: " + block)
        print("Read-only audit. No install, restart, or user-data access.")
    return 3 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
