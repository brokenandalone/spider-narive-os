"""Private, append-only Deep Forage report archive and source exports."""
import json
import os
from pathlib import Path
import re
from uuid import uuid4


def save_research(topic, report_lines, sources, directory):
    folder = Path(directory).expanduser()
    if folder.is_symlink():
        raise ValueError("The research destination cannot be a symlink")
    folder.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", topic).strip("_")[:45] or "research"
    from datetime import datetime
    stem = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_" + slug + "_" + uuid4().hex[:8]
    report = folder / (stem + ".md")
    export = folder / (stem + ".sources.json")
    payload = {
        "topic": topic,
        "sources": [{
            "number": number,
            "title": str(source.get("title", "")),
            "url": str(source.get("url", "")),
            "engine": str(source.get("engine", "unknown")),
            "published": str(source.get("published", "")),
            "evidence_kind": str(source.get("evidence_kind", "unknown")),
            "snippet": str(source.get("snippet", "")),
            "content": str(source.get("content", "")),
        } for number, source in enumerate(sources, start=1)],
    }
    # New names are unpredictable; exclusive writes never replace existing work.
    created = []
    try:
        for path, content in (
            (report, "\n".join(report_lines).rstrip() + "\n"),
            (export, json.dumps(payload, indent=2, ensure_ascii=False) + "\n"),
        ):
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            created.append(path)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return str(report), str(export)


def list_reports(directory, limit=40):
    folder = Path(directory).expanduser()
    if folder.is_symlink() or not folder.is_dir():
        return []
    if not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("History limit must be 1 to 100")
    candidates = sorted(
        (p for p in folder.glob("*.md") if p.is_file() and not p.is_symlink()),
        key=lambda p: p.stat().st_mtime_ns, reverse=True,
    )
    results = []
    for path in candidates[:limit]:
        # Bounded inspection only. The saved report itself may be much larger.
        with path.open("r", encoding="utf-8", errors="replace") as stream:
            lines = [stream.readline().rstrip("\n") for _ in range(6)]
        title = lines[0].removeprefix("# Deep Forage: ").strip() or path.stem
        status = next((line.split(":", 1)[1].strip() for line in lines
                       if line.startswith("Evidence status:")), "unknown")
        results.append({"title": title, "evidence_status": status,
                        "path": str(path), "sources_path": str(path.with_suffix(".sources.json")),
                        "modified": path.stat().st_mtime})
    return results
