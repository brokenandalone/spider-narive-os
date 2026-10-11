"""Owner-controlled assignment CSV import and iCalendar export for Study.

There is no SNHU scraping, network access, background synchronization, or
automatic school submission. Import always targets the selected local course.
"""
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import os
from pathlib import Path
import re
import tempfile


MAX_CSV_BYTES = 512 * 1024
MAX_ROWS = 500
MAX_TITLE_CHARS = 240
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


def valid_due(value):
    value = str(value or "").strip()
    if not value:
        return ""
    if not DATE_PATTERN.fullmatch(value):
        raise ValueError("Use due dates in YYYY-MM-DD format, or leave them blank.")
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("Invalid due date: " + value) from error
    return value


def _clean_title(value):
    title = str(value or "").strip()
    if not title or len(title) > MAX_TITLE_CHARS or any(ord(c) < 32 for c in title):
        raise ValueError("Assignment titles must be 1 to 240 characters without control characters.")
    return title


def parse_assignment_csv(path, existing=()):
    """Return new (title, due) rows and counts, without writing to the database.

    Accepted headings: title/assignment, due/due date/deadline and optional
    status. Rows marked Complete are not reintroduced as open assignments.
    """
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Choose a regular CSV file, not a link.")
    if path.suffix.lower() != ".csv" or path.stat().st_size > MAX_CSV_BYTES:
        raise ValueError("Select a CSV file smaller than 512 KB.")
    known = {(str(row["title"]).strip().casefold(), str(row["due"] or "").strip())
             for row in existing}
    pending = []
    skipped = 0
    completed = 0
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError("CSV needs headings: Title, Due and optionally Status.")
        columns = {name.strip().casefold(): name for name in reader.fieldnames if name}
        title_col = columns.get("title") or columns.get("assignment")
        due_col = columns.get("due") or columns.get("due date") or columns.get("deadline")
        status_col = columns.get("status")
        if not title_col or not due_col:
            raise ValueError("CSV must include Title (or Assignment) and Due (or Due Date).")
        for number, row in enumerate(reader, start=2):
            if number > MAX_ROWS + 1:
                raise ValueError("Import at most 500 assignments at once.")
            if None in row:
                raise ValueError("CSV row " + str(number) + " has extra columns.")
            try:
                title = _clean_title(row.get(title_col))
                due = valid_due(row.get(due_col))
                status = str(row.get(status_col) or "").strip().casefold() if status_col else ""
            except ValueError as error:
                raise ValueError("CSV row " + str(number) + ": " + str(error)) from error
            if status and status not in ("open", "complete"):
                raise ValueError("CSV row " + str(number) + ": Status must be Open or Complete.")
            if status == "complete":
                completed += 1
                continue
            key = title.casefold(), due
            if key in known:
                skipped += 1
                continue
            known.add(key)
            pending.append((title, due))
    return {"rows": pending, "skipped": skipped, "completed": completed}


def _escape(value):
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace(";", "\\;").replace(",", "\\,")


def _fold(line):
    """Fold UTF-8 iCalendar content at 75 octets without breaking characters."""
    output, chunk, count = [], "", 0
    for char in line:
        size = len(char.encode("utf-8"))
        if count + size > 75:
            output.append(chunk)
            chunk, count = " " + char, 1 + size
        else:
            chunk += char
            count += size
    output.append(chunk)
    return output


def calendar_text(assignments, now=None):
    """Create an RFC 5545 calendar for dated, noncompleted local assignments."""
    now = now or datetime.now(timezone.utc)
    stamp = now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Spider OS//Study//EN",
             "CALSCALE:GREGORIAN", "X-WR-CALNAME:Spider OS Study"]
    count = 0
    for row in assignments:
        if row["status"] == "Complete":
            continue
        try:
            due = valid_due(row["due"])
        except ValueError:
            continue  # Preserve uncertain dates in Study; never guess them.
        if not due:
            continue
        day = date.fromisoformat(due)
        course = str(row["course"])
        title = str(row["title"])
        ident = hashlib.sha256((str(row["id"]) + "|" + course).encode("utf-8")).hexdigest()[:32]
        lines.extend(["BEGIN:VEVENT",
                      "UID:study-" + ident + "@spider-os.local",
                      "DTSTAMP:" + stamp,
                      "DTSTART;VALUE=DATE:" + day.strftime("%Y%m%d"),
                      "DTEND;VALUE=DATE:" + (day + timedelta(days=1)).strftime("%Y%m%d"),
                      "SUMMARY:" + _escape(course + ": " + title),
                      "DESCRIPTION:Assignment tracked locally in Spider OS Study.",
                      "END:VEVENT"])
        count += 1
    lines.append("END:VCALENDAR")
    return "\r\n".join(part for line in lines for part in _fold(line)) + "\r\n", count


def write_calendar(path, assignments, overwrite=False):
    """Save privately and atomically; a cancelled or failed export keeps old data."""
    data, count = calendar_text(assignments)
    if not count:
        raise ValueError("No open assignments have valid YYYY-MM-DD due dates.")
    path = Path(path)
    if path.suffix.lower() != ".ics" or not path.parent.is_dir():
        raise ValueError("Choose an .ics file in an existing folder.")
    if path.is_symlink():
        raise ValueError("Refusing to overwrite a symbolic link.")
    if path.exists() and not overwrite:
        raise FileExistsError(str(path))
    fd, temp = tempfile.mkstemp(prefix=".study-cal-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if overwrite:
            os.replace(temp, path)
        else:
            os.link(temp, path)  # Exclusive create without replacing a race winner.
    finally:
        Path(temp).unlink(missing_ok=True)
    return count
