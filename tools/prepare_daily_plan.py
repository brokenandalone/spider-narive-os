#!/usr/bin/env python3
"""Open a NEW Spider OS daily release plan without recycling old approvals.

Developer/release-author step ONLY, performed before CI. It never installs,
touches the PC, uses credentials, or overwrites an existing day's plan. The
daily release checkout must be committed and re-tested on its exact final SHA.
"""
from __future__ import annotations
import argparse
from datetime import date, datetime
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
TIMEZONE = ZoneInfo("America/Indiana/Indianapolis")
PATTERN = re.compile(r"daily_release_plan_(\d{8})\.json$")
FLAGS = (
    "source_ci_verified", "installed_pc_reconciled", "rollback_validated",
    "owner_approved_install", "installer_daily_guard_connected",
    "voice_pipeline_verified", "model_compatibility_verified",
)


def current_day(now=None):
    at = datetime.now(TIMEZONE) if now is None else now
    if at.tzinfo is None:
        raise ValueError("Release planning clock must include timezone")
    return at.astimezone(TIMEZONE).date()


def daily_file(root, day):
    if not isinstance(day, date):
        raise TypeError("Release day must be a date")
    return Path(root) / "system" / ("daily_release_plan_" + day.strftime("%Y%m%d") + ".json")


def previous_daily_file(root, before):
    folder = Path(root) / "system"
    choices = []
    for p in folder.iterdir():
        match = PATTERN.fullmatch(p.name)
        if p.is_symlink() or not p.is_file() or match is None:
            continue
        recorded = datetime.strptime(match.group(1), "%Y%m%d").date()
        if recorded < before:
            choices.append((recorded, p))
    if not choices:
        raise ValueError("No historical Spider OS daily plan found")
    return max(choices)[1]


def prepare(*, root=ROOT, day=None, source=None):
    """Prepare a new plan, with ALL approvals revoked."""
    root = Path(root)
    day = current_day() if day is None else day
    target = daily_file(root, day)
    if target.exists() or target.is_symlink():
        raise ValueError("Today's daily plan already exists; cannot overwrite")
    previous = Path(source) if source else previous_daily_file(root, day)
    if previous.is_symlink() or not previous.is_file() or previous.parent != (root / "system"):
        raise ValueError("Prior plan must be in this checkout's system folder")
    plan = json.loads(previous.read_text(encoding="utf-8"))
    if plan.get("schema_version") != 1:
        raise ValueError("Unsupported previous daily plan")
    plan["release_date"] = day.isoformat()
    plan["timezone"] = "America/Indiana/Indianapolis"
    plan["max_system_installs_per_local_day"] = 1
    plan["candidate_commit"] = None
    for flag in FLAGS:
        plan[flag] = False
    plan["resolved_shared_paths"] = []
    plan["previous_release_plan"] = previous.name
    plan["rollover_notice"] = (
        "Everything must be revalidated for this exact day's candidate. "
        "No CI, real-PC reconciliation, voice, model, approval or rollback "
        "proof transfers from yesterday.")
    # The output is an unapproved candidate, not a receipt/installed state.
    with target.open("x", encoding="utf-8") as stream:
        json.dump(plan, stream, indent=2)
        stream.write("\n")
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="YYYY-MM-DD, defaults to owner-local day")
    parser.add_argument("--source", type=Path, help="Explicit previous system plan path")
    args = parser.parse_args(argv)
    try:
        day = date.fromisoformat(args.date) if args.date else current_day()
        path = prepare(day=day, source=args.source)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as e:
        parser.exit(3, "Daily plan creation blocked: " + str(e) + "\n")
    print("Unapproved daily release plan created:", path)
    print("All approval gates reset. Stage code, reconcile actual PC, then commit and test the exact candidate.")


if __name__ == "__main__":
    main()
