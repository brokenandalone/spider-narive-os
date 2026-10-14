"""Authorized, non-executing Kali Purple training and readiness plan."""
from __future__ import annotations
from operations_services import kali_status

LESSONS = (
    ("network_capture", "Network traffic", ("wireshark", "tcpdump", "tshark"),
     "Use a sample PCAP you own. Identify DNS and TLS traffic without capturing "
     "or inspecting anyone else's communications."),
    ("file_triage", "Suspicious file triage", ("yara", "clamscan"),
     "Use a harmless instructor-provided sample in an isolated lab. Review scan "
     "output manually. Never open unknown executables on the host."),
    ("host_review", "Host baseline review", ("lynis",),
     "Review a purposely configured training VM against a written checklist. "
     "No root-level host changes are part of this lesson."),
    ("intrusion_detection", "Intrusion detection", ("suricata", "zeek"),
     "Use an authorized offline training PCAP. Compare alert explanations with "
     "ground-truth lesson notes; do not start live sensors."),
    ("audit_basics", "Audit event fundamentals", ("auditctl",),
     "Inspect sample audit logs from a lab. The audit daemon may be installed "
     "but unable to control the host kernel inside a container."),
)


def purple_training_plan(snapshot=None):
    """Lessons are advisory text only; never issue an executable scan command."""
    status = snapshot if snapshot is not None else kali_status()
    purple = status.get("purple_tools", {})
    entries = purple.get("tools", {}) if isinstance(purple, dict) else {}
    if not isinstance(entries, dict):
        entries = {}
    lessons = []
    for identifier, label, requirements, instruction in LESSONS:
        ready = [tool for tool in requirements if entries.get(tool) is True]
        missing = [tool for tool in requirements if entries.get(tool) is not True]
        lessons.append({
            "lesson": identifier, "title": label, "tools_detected": ready,
            "tools_not_detected": missing, "training_instructions": instruction,
            "prerequisite_note": "Only in systems, networks and lab files you own "
                                 "or have explicit authorization to assess.",
        })
    return {
        "workspace": "Kali Bay",
        "mode": "read_only",
        "operation": "purple_training_plan",
        "container_state": status.get("readiness", {}).get("container_state", "unavailable"),
        "tool_inventory_state": purple.get("state", "unavailable"),
        "lessons": lessons,
        "note": "Read-only lesson guidance. No tools launched, traffic captured, "
                "containers provisioned or services configured.",
    }
