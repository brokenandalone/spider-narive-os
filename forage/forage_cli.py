#!/usr/bin/env python3
"""Spider OS Forage command-line interface. All network research is opt-in.

Examples:
    python3 forage/forage_cli.py status
    python3 forage/forage_cli.py search --web --query "topic"
    python3 forage/forage_cli.py research --topic "question" --depth quick
    python3 forage/forage_cli.py history
    python3 forage/forage_cli.py local --query "notes"
"""
import argparse
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request

from engine import REPORT_DIR, deep_research, web_search, local_search, index_local_files
from research_archive import list_reports


def check_local(url):
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "SpiderOS-Forage-Status"})
        with urllib.request.urlopen(request, timeout=3) as response:
            return response.status == 200
    except (OSError, ValueError, TimeoutError):
        return False


def status():
    return {
        "ollama_reachable": check_local("http://127.0.0.1:11434/api/tags"),
        "searxng_reachable": check_local("http://127.0.0.1:8888/search?q=test&format=json"),
        "ddgs_installed": bool(__import__("engine").enable_ddgs()),
        "reports": len(list_reports(REPORT_DIR, limit=100)),
        "spider_os_path": str(Path(__file__).resolve()),
        "note": "Reachability does not verify model quality, provider availability or PC integration.",
    }


def cli(args=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Check LOCAL research services; no external search")
    search = sub.add_parser("search", help="Explicit public search")
    search.add_argument("--query", required=True)
    search.add_argument("--web", action="store_true", help="Required to confirm external web search")
    local = sub.add_parser("local", help="Read-only explicitly selected local index")
    local.add_argument("--query", required=True)
    local.add_argument("--limit", type=int, default=15)
    run = sub.add_parser("research", help="Explicit multi-source web research + local Ollama")
    run.add_argument("--topic", required=True)
    run.add_argument("--depth", default="standard", choices=["quick", "standard", "intensive"])
    run.add_argument("--focus", default="general", choices=["general", "academic", "technical", "creative"])
    sub.add_parser("history", help="List recent saved reports, without network")
    index = sub.add_parser("index", help="Rebuild already configured selected local roots")
    index.add_argument("--root", action="append", help="Explicit source folder; avoid secrets")

    a = parser.parse_args(args)
    os.umask(0o077)
    try:
        if a.command == "status":
            result = status()
        elif a.command == "search":
            if not a.web:
                parser.error("Provide --web to explicitly authorize this public search")
            result = web_search(a.query)
        elif a.command == "local":
            result = local_search(a.query, limit=a.limit)
        elif a.command == "research":
            result = deep_research(
                a.topic, depth=a.depth, focus=a.focus,
                progress=lambda text: print(text, file=sys.stderr, flush=True),
            )
            # Do not print potentially huge retrieved documents by default.
            result = {
                "topic": result["topic"],
                "depth": result["depth"],
                "focus": result["focus"],
                "sources": len(result["sources"]),
                "evidence_status": result["evidence_status"],
                "report_path": result["report_path"],
                "sources_path": result["sources_path"],
                "quality_audit": result["quality_audit"],
                "citation_audit": result["citation_audit"],
            }
        elif a.command == "history":
            result = list_reports(REPORT_DIR)
        elif a.command == "index":
            result = index_local_files(roots=a.root)
        else:
            parser.error("Unknown mode")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        # Never replace source failures with a fabricated success.
        print(json.dumps({"error": str(error), "command": a.command}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(cli())
