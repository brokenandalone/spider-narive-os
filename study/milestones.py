"""Offline assignment milestone and weekly-planning helpers for Spider OS Study.

Only user-entered dates are interpreted; no automatic SNHU access or guessed
deadline. Text cannot execute commands or change Webbie's instructions.
"""
from datetime import date, timedelta
import re


STARTER_STEPS = (
    "Read instructions and rubric",
    "Collect and verify sources",
    "Prepare an outline",
    "Write the first draft",
    "Revise against the rubric",
    "Verify citations and references",
    "Proofread and review the final document",
)


def valid_step(title, due=""):
    title = str(title).strip()
    due = str(due or "").strip()
    if not title or len(title) > 240 or any(ord(ch) < 32 for ch in title):
        raise ValueError("A step title must be 1 to 240 characters of plain text.")
    if due:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", due):
            raise ValueError("Step date must be YYYY-MM-DD, or blank.")
        try:
            date.fromisoformat(due)
        except ValueError as error:
            raise ValueError("Invalid calendar date: " + due) from error
    return title, due


def valid_source(reference, locator="", notes=""):
    reference = str(reference).strip()
    locator = str(locator).strip()
    notes = str(notes).strip()
    for label, value, limit in (
        ("Reference", reference, 2500), ("Locator", locator, 500),
        ("Notes", notes, 4000)
    ):
        if len(value) > limit or "\x00" in value or any(
                ord(c) < 32 and c not in "\n\t" for c in value):
            raise ValueError(label + " contains invalid characters or is too long.")
    if not reference or "\n" in reference or "\t" in reference:
        raise ValueError("Enter one manually checked reference per source.")
    return reference, locator, notes


def weekly_plan(rows, *, today=None, days=7, include_completed=False):
    """Return overdue, upcoming, and undated owner-entered assignments.

    This view is not a background scheduler; all times are date-only and local.
    """
    today = today or date.today()
    if days not in (7, 14, 30):
        raise ValueError("Choose a 7, 14, or 30 day planning window.")
    results = []
    for row in rows:
        item = dict(row)
        if not include_completed and item["status"] == "Complete":
            continue
        raw_due = str(item.get("due") or "").strip()
        try:
            due = date.fromisoformat(raw_due) if re.fullmatch(
                r"\d{4}-\d{2}-\d{2}", raw_due) else None
        except ValueError:
            due = None
        if due is None:
            item["urgency"] = "No valid date"
            priority = (2, date.max)
        elif due < today:
            item["urgency"] = "Overdue"
            priority = (0, due)
        elif due <= today + timedelta(days=days):
            item["urgency"] = ("Due today" if due == today else
                               f"Due in {(due - today).days} day(s)")
            priority = (1, due)
        else:
            continue
        item["progress"] = (
            f"{int(item.get('steps_done') or 0)}/{int(item.get('steps_total') or 0)}")
        item["next_action"] = str(item.get("next_step") or "Plan the next step")
        item["_priority"] = priority
        results.append(item)
    results.sort(key=lambda x: (x["_priority"], str(x["course"]).casefold(),
                                str(x["title"]).casefold(), int(x["id"])))
    for item in results:
        del item["_priority"]
    return results


def workload_totals(items):
    return {
        "overdue": sum(x["urgency"] == "Overdue" for x in items),
        "due_today": sum(x["urgency"] == "Due today" for x in items),
        "undated": sum(x["urgency"] == "No valid date" for x in items),
        "visible": len(items),
        "steps_left": sum(max(0, int(x.get("steps_total") or 0) -
                               int(x.get("steps_done") or 0)) for x in items),
    }
