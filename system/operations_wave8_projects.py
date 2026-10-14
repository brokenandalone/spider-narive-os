"""Owner-click local project checklists for Spider OS.

No task execution, automated due dates, cloud sync or background jobs.
Files are written only when the owner selects Save from the GUI.
"""
from __future__ import annotations
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from uuid import uuid4

SCHEMA = "spider-operations-manual-plan-v1"
TEMPLATES = {
    "record_song": (
        "Studio / Produce a song",
        ("Choose the arrangement and reference mix",
         "Review locally approved tracks and recording setup",
         "Record and align stems in Spider Studio",
         "Inspect sample rates, peaks and possible clipping",
         "Review mix with ears and reference recordings",
         "Approve master and separate release artwork"),
    ),
    "write_chapter": (
        "Author / Develop a Broken World chapter",
        ("Review the established Master Canon and approved chapter plan",
         "Check relevant character locations and prior chapters",
         "Draft scenes without silently changing established lore",
         "Review character continuity and evidence anchors",
         "Revise prose and confirm all intentional canon changes",
         "Export or snapshot the approved manuscript"),
    ),
    "finish_assignment": (
        "Study / Complete an SNHU assignment",
        ("Read the current module instructions and grading rubric",
         "Locate original course readings and verify citations",
         "Outline arguments with your own experience where appropriate",
         "Write draft and review each rubric item",
         "Check APA layout and unresolved source placeholders",
         "Personally approve and submit through the school portal"),
    ),
    "purple_lab": (
        "Kali Bay / Authorized Purple lab",
        ("Define the owned or explicitly authorized lab scope",
         "Check Kali Purple tools without starting unnecessary sensors",
         "Choose an approved offline training dataset",
         "Run the authorized exercise manually and record observations",
         "Identify false positives and cleanup obligations",
         "Complete a private evidence summary"),
    ),
    "system_release": (
        "System / Release acceptance",
        ("Confirm protected backup and current installed code fingerprints",
         "Reconcile upgrades without overwriting the live installed baseline",
         "Run controlled unit/source checks",
         "Test desktop, audio, owner access and workspaces when ready",
         "Review release notes and explicitly approve the installation",
         "Record install receipt, functional verification and rollback plan"),
    ),
}


def new_plan(template, title):
    if template not in TEMPLATES:
        raise ValueError("Choose a reviewed plan template.")
    if not isinstance(title, str) or not (1 <= len(title.strip()) <= 90):
        raise ValueError("A project name must have 1 to 90 characters.")
    if any(ord(c) < 32 for c in title):
        raise ValueError("Project names cannot contain control characters.")
    label, steps = TEMPLATES[template]
    return {
        "schema": SCHEMA,
        "id": str(uuid4()),
        "template": template,
        "title": title.strip(),
        "template_label": label,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "steps": [{"title": name, "complete": False} for name in steps],
        "note": "Owner-directed checklist only. Nothing is executed automatically.",
    }


def validate_plan(plan):
    if not isinstance(plan, dict) or plan.get("schema") != SCHEMA:
        raise ValueError("Invalid Spider Operations project plan schema.")
    name = plan.get("template")
    if name not in TEMPLATES:
        raise ValueError("Unknown project template.")
    title = plan.get("title")
    if not isinstance(title, str) or not 1 <= len(title) <= 90:
        raise ValueError("Invalid project title.")
    steps = plan.get("steps")
    original = TEMPLATES[name][1]
    if not isinstance(steps, list) or len(steps) != len(original):
        raise ValueError("Plan step count does not match its template.")
    for index, (item, expected) in enumerate(zip(steps, original)):
        if not isinstance(item, dict) or item.get("title") != expected:
            raise ValueError(f"Unreviewed step at position {index + 1}.")
        if type(item.get("complete")) is not bool:
            raise ValueError("Completion markers must be boolean.")
    return True


def mark_step(plan, index, complete):
    validate_plan(plan)
    if not isinstance(index, int) or not 0 <= index < len(plan["steps"]):
        raise ValueError("Choose an existing project step.")
    if type(complete) is not bool:
        raise ValueError("Choose a true or false completion state.")
    copy = json.loads(json.dumps(plan))
    copy["steps"][index]["complete"] = complete
    return copy


def plan_summary(plan):
    validate_plan(plan)
    done = sum(item["complete"] for item in plan["steps"])
    return {
        "workspace": "Operations",
        "mode": "manual_plan",
        "template": plan["template"],
        "tasks_total": len(plan["steps"]),
        "tasks_completed": done,
        "tasks_remaining": len(plan["steps"]) - done,
        "note": "Manual completion only. No external system action or automatic task.",
    }


def save_plan(plan, selected_path):
    validate_plan(plan)
    target = Path(selected_path).expanduser()
    if target.suffix.lower() != ".json" or target.is_symlink() or target.exists():
        raise ValueError("Choose a new unused JSON filename. Existing work is preserved.")
    if not target.parent.is_dir() or target.parent.is_symlink():
        raise ValueError("Choose an existing ordinary destination folder.")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    payload = (json.dumps(plan, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    fd = os.open(target, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return target


def load_plan(selected_path):
    source = Path(selected_path).expanduser()
    if source.is_symlink() or not source.is_file() or source.suffix.lower() != ".json":
        raise ValueError("Choose a regular Spider Operations JSON plan.")
    if source.stat().st_size > 128 * 1024:
        raise ValueError("Plan exceeds the private file size limit.")
    obj = json.loads(source.read_text(encoding="utf-8-sig"))
    validate_plan(obj)
    return obj
