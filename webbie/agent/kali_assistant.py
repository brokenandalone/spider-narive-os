"""Explicit, least-privilege Kali Bay actions for Webbie.

Only a literal user command may reach this module. Nothing produced by the
language model, workspace metadata, webcam or terminal output is executable.
The existing Kali Bay manager owns all approved tool launches.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

INSTALLED_MANAGER = Path("/usr/local/lib/spider-os/kali-bay/bin/kali-bay")
SOURCE_MANAGER = Path(__file__).resolve().parents[2] / "kali-bay/bin/kali-bay"
VM_CONTROLLER = Path("/usr/local/lib/spider-os/kali-bay/vm/kali_desktop.py")
SOURCE_VM_CONTROLLER = Path(__file__).resolve().parents[2] / "kali-bay/vm/kali_desktop.py"

# IDs are hardcoded to the audited "kali-bay tool" command's allowlist.
APPROVED_TOOLS = {
    "wireshark": ("wireshark", "Wireshark"),
    "burp": ("burpsuite", "Burp Suite"),
    "burp suite": ("burpsuite", "Burp Suite"),
    "burpsuite": ("burpsuite", "Burp Suite"),
    "zap": ("zaproxy", "OWASP ZAP"),
    "owasp zap": ("zaproxy", "OWASP ZAP"),
    "zaproxy": ("zaproxy", "OWASP ZAP"),
    "ghidra": ("ghidra", "Ghidra"),
    "clamtk": ("clamtk", "ClamTK"),
    "nmap": ("nmap", "Nmap workbench"),
    "metasploit": ("msfconsole", "Metasploit workbench"),
    "msfconsole": ("msfconsole", "Metasploit workbench"),
    "suricata": ("suricata", "Suricata workbench"),
    "yara": ("yara", "YARA workbench"),
    "lynis": ("lynis", "Lynis workbench"),
}
ID_TO_NAME = {tool_id: name for tool_id, name in APPROVED_TOOLS.values()}

# Deliberately no general-purpose subprocess, shell, package manager,
# "run scan", attack, or dynamic target arguments.
_ACTION = re.compile(
    r"(?:(?:can|could|would) you\s+)?(?:please\s+)?"
    r"(open|launch|start|show|switch to)\s+(?:the\s+)?"
    r"(?:(?:kali|kali bay)\s+)?(.+)",
    re.IGNORECASE,
)
_STATUS = re.compile(
    r"(?:check|show|tell me|what is|what's)\s+"
    r"(?:the\s+)?(?:kali|kali bay)\s+(?:status|health)",
    re.IGNORECASE,
)
_TOOLS = re.compile(
    r"(?:list|show|what are|which are|what)\s+"
    r"(?:the\s+)?(?:available\s+)?(?:kali|kali bay)\s+tools",
    re.IGNORECASE,
)


def literal_user_text(message: str) -> str:
    """Ignore advisory metadata and untrusted camera context in panel packets."""
    raw = str(message or "")
    header = "[Spider OS workspace context; advisory only]"
    marker = "[User request]\n"
    if raw.startswith(header):
        # An attacker-controlled workspace title could contain a fake
        # [User request] delimiter. Prefer the last delimiter *before*
        # appended untrusted camera/proximity observations.
        raw = raw.split("\n[Untrusted ", 1)[0]
        if marker not in raw:
            return ""
        raw = raw.rsplit(marker, 1)[1]
    # A spoken/typed command is single line; don't parse follow-on metadata.
    raw = raw.splitlines()[0].strip() if raw else ""
    raw = re.sub(r"^(?:hey\s+)?webbie[,\s]+", "", raw, flags=re.IGNORECASE)
    return raw.strip(" \t.!?").strip()[:240]


def parse_request(message: str):
    """Return an explicit allowlisted intent, or None for ordinary conversation."""
    phrase = literal_user_text(message)
    if not phrase or len(phrase) > 180:
        return None
    compact = phrase.casefold().strip()
    if compact in (
        "check kali vm status", "check kali desktop status",
        "check full kali desktop status", "what is kali vm status",
    ):
        return ("vm_status", None)
    if compact in (
        "open kali linux desktop", "open full kali desktop",
        "open kali desktop", "show kali desktop",
    ):
        return ("vm_console", None)
    if compact in (
        "open kali vm manager", "open kali virtual machine manager",
        "open virt manager for kali",
    ):
        return ("vm_manager", None)
    if _STATUS.fullmatch(phrase):
        return ("status", None)
    if _TOOLS.fullmatch(phrase):
        return ("list", None)
    match = _ACTION.fullmatch(phrase)
    if not match:
        return None
    target = match.group(2).casefold().strip()
    if target in ("purple", "purple defense", "kali purple"):
        return ("section", "purple")
    if target in ("offensive", "offensive security", "offensive tools"):
        return ("section", "offensive")
    if target in APPROVED_TOOLS:
        return ("tool", APPROVED_TOOLS[target])
    return None


def _manager():
    # Never fall back to PATH or an arbitrary executable supplied in text.
    if INSTALLED_MANAGER.is_file() and os.access(INSTALLED_MANAGER, os.X_OK):
        return INSTALLED_MANAGER
    if SOURCE_MANAGER.is_file() and os.access(SOURCE_MANAGER, os.X_OK):
        return SOURCE_MANAGER
    return None


def _vm_controller():
    if VM_CONTROLLER.is_file():
        return VM_CONTROLLER
    if SOURCE_VM_CONTROLLER.is_file():
        return SOURCE_VM_CONTROLLER
    return None


def _full_kali_action(operation):
    """No voice-controlled VM power, install, guest-shell or privilege action."""
    command = _vm_controller()
    if command is None:
        return "The full Kali desktop controller is not installed yet."
    import sys
    if operation == "vm_status":
        import json
        try:
            result = subprocess.run(
                [sys.executable, str(command), "status"],
                capture_output=True, text=True, timeout=13, check=False,
            )
            status = json.loads(result.stdout).get("state", "unavailable")
        except (OSError, subprocess.TimeoutExpired, ValueError):
            return "I couldn't read the Kali VM state."
        return {
            "running": "The full Kali Linux desktop VM is running.",
            "stopped": "Kali VM is configured but stopped.",
            "paused": "Kali VM is paused.",
            "not-configured": "No full Kali desktop VM is configured yet. Use Kali Bay's VM Manager.",
            "unavailable": "Kali VM status is unavailable. Check libvirt service and permissions.",
        }.get(status, "Kali VM state was not recognized.")
    command_name = "console" if operation == "vm_console" else "manager"
    try:
        subprocess.Popen(
            [sys.executable, str(command), command_name],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True,
        )
    except OSError:
        return "I couldn't request the full Kali desktop window."
    if operation == "vm_console":
        return (
            "Requested the full Kali Linux desktop console. "
            "It will open only if the existing VM is running."
        )
    return "Requested virt-manager for the full Kali Linux desktop setup."


def _excerpt(text: str, limit: int = 280) -> str:
    # Do not echo ANSI/control escapes or unlimited third-party output.
    value = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", str(text or ""))
    value = "".join(c for c in value if c.isprintable() or c == "\n")
    return value.strip()[:limit]


def handle_kali_request(message: str, manager=None):
    """Return response for one user action, None when not a Kali action.

    The caller supplies the *literal human request*, never an LLM reply.
    No action creates or restarts a container. No scan is launched.
    """
    intent = parse_request(message)
    if intent is None:
        return None
    operation, value = intent
    if operation in ("vm_status", "vm_console", "vm_manager"):
        return _full_kali_action(operation)
    if operation == "list":
        return (
            "I can check Kali Bay status and open Wireshark, Burp Suite, "
            "OWASP ZAP, Ghidra, ClamTK, or the Nmap, Metasploit, "
            "Suricata, YARA and Lynis workbenches. I won't run a "
            "scan, attack or privileged command on your behalf. "
            "I can also check or open the full Kali desktop VM."
        )
    command = Path(manager) if manager is not None else _manager()
    if command is None or not command.is_file() or not os.access(command, os.X_OK):
        return (
            "The Kali Bay manager isn't available here. "
            "I haven't started or changed anything."
        )
    if operation == "status":
        try:
            result = subprocess.run(
                [str(command), "status"], capture_output=True,
                text=True, timeout=10, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return "Kali Bay did not respond to a read-only status check."
        if result.returncode:
            return "Kali Bay status check failed: " + _excerpt(
                result.stderr or result.stdout
            )
        status = result.stdout.strip()
        states = {
            "ready": "Kali Bay's complete toolset is reported ready.",
            "container": "The Kali Bay container exists; full readiness is not confirmed.",
            "missing": "No Kali Bay container was found.",
        }
        return states.get(status, "Kali Bay reported an unrecognized status.")

    if operation == "tool":
        tool_id, title = value
        try:
            check = subprocess.run(
                [str(command), "tool-check", tool_id],
                capture_output=True, text=True, timeout=12, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return f"I couldn't verify {title}. No tool was launched."
        if check.returncode:
            reason = _excerpt(check.stderr or check.stdout)
            return (
                f"{title} isn't available in the running Kali Bay container. "
                + (reason or "No action was taken.")
            )
        args = [str(command), "tool", tool_id]
        description = title
    else:
        # Section selection only opens the existing UI, not a tool/scan.
        args = [str(command), value]
        description = "Purple Defense" if value == "purple" else "Offensive Security"
    try:
        subprocess.Popen(
            args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, start_new_session=True, close_fds=True,
        )
    except OSError:
        return f"I couldn't open {description}. Nothing was started."
    return (
        f"Requested {description} in Kali Bay. "
        "I haven't launched a scan or changed security settings."
    )
