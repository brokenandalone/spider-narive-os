#!/usr/bin/env python3
"""Static scope guard for the native Spider OS release ONLY.

Spider Media Center and BCN Website are distinct products with independent
releases. They are neither source/PR dependencies nor readiness gates for
the native spider-narive-os installation. This audit cannot install or approve.
"""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/releases/2026-10-12-master-cross-repo-inventory.json"
NATIVE_REPO = "brokenandalone/spider-narive-os"
NATIVE_REQUIRED = {100, 101, 102, 99, 98, 97, 96, 95, 94, 93, 92, 90, 89, 88}
EXCLUSIONS = ("Spider Media Center", "BCN Network", "Spider-OS1")
HASH = re.compile(r"^[a-f0-9]{40}$")


def review(data):
    problems = []
    if not isinstance(data, dict) or data.get("schema") != 1:
        return {"status": "BLOCKED", "blockers": ["Invalid native OS inventory schema"]}
    if data.get("status") != "AUDIT_ONLY_NO_INSTALL":
        problems.append("Release inventory cannot grant install approval")
    if data.get("scope") != "SPIDER_OS_NATIVE_ONLY" or data.get("release_target") != "spider-narive-os owner desktop OS":
        problems.append("Release scope must be exclusively native Spider OS")
    repos = data.get("repos")
    if not isinstance(repos, dict) or set(repos) != {"spider_os"}:
        problems.append("Separate projects are not OS release repositories")
        repos = {"spider_os": {}} if not isinstance(repos, dict) else repos
    native = repos.get("spider_os")
    if not isinstance(native, dict):
        native = {}
        problems.append("Native Spider OS repository inventory missing")
    if native.get("repository") != NATIVE_REPO or not HASH.fullmatch(str(native.get("main_commit_at_audit", ""))):
        problems.append("Native Spider OS repository and pinned main commit missing")
    open_prs = native.get("open_prs")
    if not isinstance(open_prs, list):
        problems.append("Native OS open PR list missing")
        open_prs = []
    ids = [item.get("n") for item in open_prs if isinstance(item, dict)]
    if len(ids) != len(open_prs) or len(ids) != len(set(ids)):
        problems.append("Native OS PR list malformed or duplicated")
    if native.get("open_count") != len(ids):
        problems.append("Native OS PR count inconsistent")
    priorities = data.get("priority_pulls")
    if not isinstance(priorities, dict) or set(priorities) != {"spider_os"}:
        problems.append("Media Center, BCN and legacy PRs must not gate OS")
        priorities = {}
    targets = priorities.get("spider_os")
    if not isinstance(targets, list) or set(targets) != NATIVE_REQUIRED or len(targets) != len(NATIVE_REQUIRED):
        problems.append("Mandatory native Spider OS PR audit incomplete")
    identified = set(ids) | {
        p.get("n") for p in native.get("recent_closed", []) if isinstance(p, dict)
    }
    if not NATIVE_REQUIRED.issubset(identified):
        problems.append("An audited native OS PR missing from snapshot")
    exclusions = data.get("exclude_from_release")
    if not isinstance(exclusions, list) or len(exclusions) < 3 or not all(
        any(term in statement for statement in exclusions
            if isinstance(statement, str)) for term in EXCLUSIONS
    ):
        problems.append("Media Center, BCN and Spider-OS1 must be explicitly excluded")
    acceptance = data.get("acceptance")
    if not isinstance(acceptance, dict) or not acceptance:
        problems.append("Native OS approval gates missing")
    else:
        if any(v is not False for v in acceptance.values()):
            problems.append("OS source scope audit is not approval or PC installation")
        if any("media_center" in name.lower() or "bcn" in name.lower() or
               "website" in name.lower() or "legacy" in name.lower()
               for name in acceptance):
            problems.append("External project readiness must not gate OS release")
    special = native.get("special")
    if not isinstance(special, dict) or special.get("nova_voice_merged_to_main_pr") != 102:
        problems.append("Latest native OS Nova shared voice PR is unaccounted for")
    if not data.get("external_project_reference_only"):
        problems.append("External project list must remain reference only")
    requirements = data.get("requirements")
    if not isinstance(requirements, list) or len(requirements) < 7:
        problems.append("Native OS upgrade scope is incomplete")
    notes = [
        "Read-only audit: this only records native Spider OS scope, never approves install.",
        "Spider Media Center and BCN Website have independent PRs, releases and installation schedules.",
        "Do not count external repo updates as native OS install blockers or merge inputs.",
        "Open native OS PRs may be stacked ancestors. Deduplicate by code ancestry, not title.",
        "The actual 31-file semantic reconciliation and physical tests remain outstanding.",
    ]
    return {"status": "BLOCKED" if problems else "OS_SCOPE_RECORDED_NOT_INSTALLABLE",
            "blockers": problems, "notes": notes,
            "native_os_open_pr_count": native.get("open_count")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        outcome = review(json.loads(args.manifest.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        outcome = {"status": "BLOCKED", "blockers": ["Cannot read OS inventory: " + type(exc).__name__]}
    if args.json:
        print(json.dumps(outcome, indent=2))
    else:
        print("SPIDER OS ONLY:", outcome["status"])
        for message in outcome.get("blockers", []):
            print("BLOCKED:", message)
        print("MEDIA CENTER AND BCN ARE NOT INCLUDED. NO INSTALLATION.")
    return 3 if outcome["status"] == "BLOCKED" else 0


if __name__ == "__main__":
    sys.exit(main())
