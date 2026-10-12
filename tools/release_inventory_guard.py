#!/usr/bin/env python3
"""Source-only guard for a COMPLETE, still-unapproved multi-repo release scope.

Verifies that the as-of-date GitHub PR inventory, external deployments, latest
Nova voices, Media Center playlists, BCN story hub and installed-PC holds were
not accidentally omitted from the frozen release checklist. Does not fetch
GitHub or inspect/install the PC. A newly created PR requires a fresh audit.
"""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/releases/2026-10-12-master-cross-repo-inventory.json"
REQUIRED = {
    "spider_os": {100, 101, 102, 99, 98, 97, 96, 95, 94, 93, 92, 90, 89, 88},
    "media_center": {23, 22, 21, 20, 18, 16, 11},
    "bcn_network": {14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1},
    "legacy_spider_os1": {10, 9, 8, 7, 6, 5, 4, 3, 2},
}
HASH = re.compile(r"^[a-f0-9]{40}$")


def review(data):
    blockers, notes = [], []
    if not isinstance(data, dict) or data.get("schema") != 1:
        return {"status":"BLOCKED","blockers":["Invalid release inventory schema"],"notes":[]}
    if data.get("status") != "AUDIT_ONLY_NO_INSTALL":
        blockers.append("Never treat upgrade inventory as installation approval")
    repos = data.get("repos")
    if not isinstance(repos, dict):
        return {"status":"BLOCKED","blockers":["Missing repository inventory"],"notes":[]}
    for name, expected in REQUIRED.items():
        record = repos.get(name)
        if not isinstance(record, dict):
            blockers.append("Missing scoped repository: " + name)
            continue
        if not HASH.fullmatch(str(record.get("main_commit_at_audit", ""))):
            blockers.append("Missing exact default-branch commit: " + name)
        listed = record.get("open_prs")
        if not isinstance(listed, list):
            blockers.append("Missing list of open PRs: " + name)
            continue
        names = [v.get("n") for v in listed if isinstance(v, dict)]
        if len(names) != len(listed) or len(names) != len(set(names)):
            blockers.append("Duplicate/bad open PR entries: " + name)
        if record.get("open_count") != len(names):
            blockers.append("Open count mismatch: " + name)
        present = set(names) | {v.get("n") for v in record.get("recent_closed", []) if isinstance(v, dict)}
        classified = data.get("priority_pulls", {}).get(name)
        if not isinstance(classified, list) or set(classified) != expected:
            blockers.append("Missing/unknown mandatory tracked PRs: " + name)
        elif not expected.issubset(present):
            blockers.append("Mandatory PR not covered in snapshot: " + name)
    special = repos.get("spider_os", {}).get("special", {})
    if special.get("nova_voice_merged_to_main_pr") != 102 or not special.get("merged_voice_module_missing_from_wave_six"):
        blockers.append("Lost track of newly merged Nova voice module absent from Wave Six")
    media = repos.get("media_center", {}).get("special", {})
    if media.get("playlist_workshop_merged_pr") != 21 or media.get("four_artist_merged_pr") != 22:
        blockers.append("V7 bulk playlist and four-artist generator lost from scope")
    if media.get("new_voice_pr_open") != 23 or media.get("open_shutdown_pr") != 11:
        blockers.append("Outstanding Media Center voice and radio shutdown work missing")
    site = repos.get("bcn_network", {}).get("special", {})
    if site.get("merged_command_center_pr") != 13 or site.get("draft_story_pages_pr") != 14:
        blockers.append("Latest BCN Command Center/story-page work missing")
    acceptance = data.get("acceptance")
    if not isinstance(acceptance, dict) or len(acceptance) < 9 or any(v is not False for v in acceptance.values()):
        blockers.append("Release readiness flags must all remain false in the audit snapshot")
    if len(data.get("requirements", [])) < 9:
        blockers.append("Master upgrade conditions incomplete")
    notes.append("Static audit only; cannot detect a newer GitHub PR or local PC change.")
    notes.append("Open PRs may be stacked ancestors; deduplicate by actual code diff and ancestry.")
    notes.append("One owner release session requires separate native OS, Media Center and website deployments.")
    return {"status":"BLOCKED" if blockers else "SCOPE_RECORDED_NOT_INSTALLABLE",
            "blockers":blockers,"notes":notes,
            "counts":{k:repos[k].get("open_count") for k in REQUIRED if k in repos}}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest",type=Path,default=MANIFEST)
    p.add_argument("--json",action="store_true")
    a=p.parse_args(argv)
    try:
        status=review(json.loads(a.manifest.read_text(encoding="utf-8")))
    except (OSError,UnicodeError,ValueError,TypeError) as error:
        status={"status":"BLOCKED","blockers":["Cannot read scope inventory: "+type(error).__name__]}
    if a.json:
        print(json.dumps(status,indent=2))
    else:
        print("FULL SYSTEM UPGRADE SCOPE:",status["status"])
        for message in status.get("blockers",[]):print("BLOCKED:",message)
        print("NO INSTALL, NO LIVE PC CHANGE")
    return 3 if status["status"]=="BLOCKED" else 0


if __name__=="__main__":
    sys.exit(main())
