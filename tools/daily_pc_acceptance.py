#!/usr/bin/env python3
"""Read-only PC acceptance and continuity checks for one Spider OS daily batch.

Does not install, restart, scan HOME, copy, or change any files. Only checks
a fixed allowlist of installed application source and two existing services.
Use --phase before for the pre-install review or --phase after for acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import subprocess
import sys
from urllib.request import urlopen
from urllib.error import URLError

FILES = {
    "The Web": "the-web/shell/main.py",
    "Webbie": "webbie/agent/webbie.py",
    "Webbie voice trust": "webbie/agent/voice_trust.py",
    "Webbie workflow core": "webbie/agent/workflow_board.py",
    "Webbie workflow dialog": "the-web/shell/webbie_workflow_dialog.py",
    "Webbie Voice Lab": "webbie/agent/voice_lab.py",
    "Webbie speaker gate": "webbie/agent/segment_speaker_gate.py",
    "Webbie speaker provider": "webbie/agent/speaker_provider_loader.py",
    "Webbie hearing test": "webbie/voice/hearing_test.py",
    "Webbie readiness": "webbie/agent/runtime_readiness.py",
    "Study": "study/study.py",
    "Study coach": "study/study_coach.py",
    "Study readings": "study/reading_library.py",
    "Author": "author/main.py",
    "Author Story Atlas": "author/story_atlas.py",
    "Author Master Canon": "author/master_canon.py",
    "Author canon panel": "author/master_canon_widget.py",
    "Studio": "studio/main.py",
    "Studio Release Desk": "studio/release_panel.py",
    "Studio Production Board": "studio/production_board.py",
    "Studio board panel": "studio/production_board_panel.py",
    "Kali Bay": "kali-bay/ui/kali_bay.py",
    "Kali manager": "kali-bay/bin/kali-bay",
    "Kali evidence chain": "kali-bay/runtime/evidence_ledger.py",
    "Kali report engine": "kali-bay/runtime/lab_reports.py",
    "Kali upgrade audit": "kali-bay/package/audit-upgrade.py",
    "Forage": "forage/forage.py",
    "Deep Forage": "forage/deep-forage/deep_forage.py",
    "Nova": "media/ai-dj/nova_host.py",
}
# New modules may be absent BEFORE the first reviewed daily installation.
# Only these exact paths are allowed the pending-add status. A symlink,
# damaged source, or unexpected missing legacy code still blocks.
PLANNED_NEW = frozenset((
    "Webbie Voice Lab", "Webbie speaker gate", "Webbie speaker provider",
    "Webbie hearing test", "Author Master Canon", "Author canon panel",
    "Studio Production Board", "Studio board panel",
    "Webbie workflow core", "Webbie workflow dialog",
))
SERVICES = ("webbie.service", "spider-ai-dj.service")
MAX_BYTES = 5 * 1024 * 1024
DEFAULT_INSTALL = Path("/usr/local/lib/spider-os")


def digest_safe(root, relative):
    """Hash fixed application code only, refusing links and unsafe ancestors."""
    root = Path(root)
    if not root.is_dir() or root.is_symlink():
        return {"status": "unavailable", "reason": "root missing or untrusted"}
    target = root
    for segment in relative.split("/"):
        if segment in (".", "..", ""):
            return {"status": "unavailable", "reason": "invalid path"}
        target = target / segment
        if target.is_symlink():
            return {"status": "unavailable", "reason": "symlinked source"}
    try:
        if not target.exists():
            return {"status": "unavailable", "reason": "file not installed"}
        st = target.stat()
        if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_BYTES:
            return {"status": "unavailable", "reason": "not a bounded regular file"}
        if st.st_size == 0:
            return {"status": "unavailable", "reason": "empty source"}
        digest = hashlib.sha256()
        with target.open("rb") as source:
            for chunk in iter(lambda: source.read(131072), b""):
                digest.update(chunk)
        if target.stat().st_mtime_ns != st.st_mtime_ns or target.stat().st_size != st.st_size:
            return {"status": "unavailable", "reason": "source changed during check"}
        return {"status": "ok", "sha256": digest.hexdigest()}
    except OSError:
        return {"status": "unavailable", "reason": "cannot read fixed application file"}


def inspect_files(source_root, install_root):
    result = {}
    for label, relative in FILES.items():
        source = digest_safe(source_root, relative)
        installed = digest_safe(install_root, relative)
        if source["status"] != "ok":
            state = "source_unavailable"
        elif (installed["status"] != "ok" and label in PLANNED_NEW
              and installed.get("reason") == "file not installed"):
            state = "pending_add"
        elif installed["status"] != "ok":
            state = "installed_unavailable"
        elif source["sha256"] == installed["sha256"]:
            state = "matching"
        else:
            state = "different"
        # Do not publish bytes, paths to private files, or user data.
        result[label] = {"file": relative, "state": state,
                         "candidate_sha256": source.get("sha256"),
                         "installed_sha256": installed.get("sha256"),
                         "reason": installed.get("reason") if installed["status"] != "ok" else None}
    return result


def inspect_services(runner=subprocess.run):
    states = {}
    for unit in SERVICES:
        try:
            output = runner(
                ["systemctl", "--user", "is-active", unit],
                capture_output=True, text=True, timeout=4, check=False
            )
            value = output.stdout.strip()
            states[unit] = value if value in ("active", "inactive", "failed", "activating", "deactivating") else "unverified"
        except (OSError, ValueError, subprocess.TimeoutExpired):
            states[unit] = "unverified"
    return states


def inspect_nova_health(opener=urlopen):
    """Loopback only; does not start broadcasting or send requests remotely."""
    try:
        with opener("http://127.0.0.1:9876/health", timeout=2) as reply:
            if reply.status != 200:
                return "unverified"
            payload = reply.read(4096)
            data = json.loads(payload)
            return "healthy" if data.get("ok") is True and data.get("service") == "Spider AI DJ" else "unverified"
    except (OSError, ValueError, TypeError, URLError, json.JSONDecodeError):
        return "unverified"


def inspect(source_root, install_root, *, phase="before", check_services=True):
    if phase not in ("before", "after"):
        raise ValueError("Choose before or after")
    files = inspect_files(source_root, install_root)
    services = inspect_services() if check_services else {}
    nova = inspect_nova_health() if check_services else "not_checked"
    blocking = []
    for name, entry in files.items():
        if entry["state"] in ("source_unavailable", "installed_unavailable"):
            blocking.append(f"{name}: code unavailable or unsafe")
        elif entry["state"] == "pending_add":
            if phase == "after":
                blocking.append(f"{name}: planned new module not installed")
        elif phase == "after" and entry["state"] != "matching":
            blocking.append(f"{name}: candidate and installed code differ")
    if check_services and phase == "after":
        for unit, state in services.items():
            if state != "active":
                blocking.append(unit + ": expected active, observed " + state)
        if nova != "healthy":
            blocking.append("Nova: loopback health not confirmed")
    return {
        "phase": phase,
        "status": "BLOCKED" if blocking else ("SOURCE MATCHING" if phase == "after" else "REVIEW REQUIRED"),
        "files": files,
        "services": services,
        "nova_health": nova,
        "blockers": blocking,
        "limitations": [
            "Source hashes cannot prove functional PC hardware, UI, audio, microphone, GPU or camera behavior.",
            "A different installed file must be reconciled with the owner's real local customizations; do not overwrite it blindly.",
            "No personal documents, credentials, models, manuscripts or school folders were examined.",
            "This tool does not reserve the daily install slot, run the installer or validate recovery.",
            "Kali source match does not establish a running Distrobox container, sensor health or authorized speaker control; verify these manually.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--installed-root", type=Path, default=DEFAULT_INSTALL)
    parser.add_argument("--phase", choices=("before", "after"), default="before")
    parser.add_argument("--skip-services", action="store_true",
                        help="Check application source only (for isolated staging/CI)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = inspect(args.source_root, args.installed_root,
                     phase=args.phase, check_services=not args.skip_services)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("SPIDER OS PC ACCEPTANCE: " + report["status"])
        for name, entry in report["files"].items():
            print(name + ": " + entry["state"])
        for unit, status in report["services"].items():
            print(unit + ": " + status)
        print("Nova loopback: " + report["nova_health"])
        for issue in report["blockers"]:
            print("BLOCKED: " + issue)
        print("Read-only check. No installation or service action performed.")
    return 3 if report["blockers"] else 0


if __name__ == "__main__":
    sys.exit(main())
