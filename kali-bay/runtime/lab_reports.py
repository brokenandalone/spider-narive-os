#!/usr/bin/env python3
"""Offline defensive lab guides and explicit private report export."""
from __future__ import annotations
from datetime import datetime, timezone
import os
import workspace_store as store

GUIDES = (
    ("asset-baseline", "Authorized asset inventory", "Identify",
     "Document permitted assets and owners.",
     ("Record written scope and authorization.",
      "Review existing approved asset inventories.",
      "Document discrepancies and evidence sources.",
      "Identify an owner for each follow-up action.")),
    ("traffic-triage", "Packet capture triage", "Detect",
     "Interpret a stored capture without new network traffic.",
     ("Confirm the capture's origin and permission.",
      "Record a hash and retain an unchanged original.",
      "Review the stored capture in Wireshark.",
      "Separate observed facts from suspected behavior.")),
    ("web-review", "Web application review", "Protect",
     "Plan a safe assessment of a permitted application.",
     ("Record application owner, scope and excluded endpoints.",
      "Confirm test accounts and authorized time window.",
      "Review existing logs and request evidence.",
      "Recommend mitigations without modifying production.")),
    ("file-triage", "Suspicious file evidence", "Detect",
     "Review an existing suspicious file without executing it.",
     ("Confirm permission to handle the sample.",
      "Preserve the original and its cryptographic hash.",
      "Review trusted metadata and existing detection results.",
      "Document uncertainty, custody and safe escalation.")),
    ("hardening", "Linux hardening", "Protect",
     "Plan owner-approved, reversible configuration improvements.",
     ("Document system ownership and backups.",
      "Review existing configuration and audit evidence.",
      "Prioritize relevant risks and reversible mitigations.",
      "Record approval and a verification procedure.")),
    ("purple-alert", "Kali Purple alert investigation", "Respond",
     "Triage existing alerts without starting sensors.",
     ("Record alert origin, timestamp and sensor coverage.",
      "Verify whether the sensor was actually active.",
      "Correlate existing evidence with alternative explanations.",
      "Record escalation and rule-tuning recommendations.")),
    ("incident-log", "Incident evidence record", "Respond",
     "Track a permitted investigation and its chain of custody.",
     ("Identify incident owner and response authority.",
      "Build a timeline of verified observations.",
      "Record evidence identifiers and custodians.",
      "Separate proposed from approved containment steps.")),
    ("retest", "Remediation verification", "Recover",
     "Document safe closure of an authorized finding.",
     ("Restate the original issue and owner.",
      "Get approval for a non-destructive retest.",
      "Record actual evidence for each closure claim.",
      "List unresolved risks and final sign-off.")),
)


def list_guides(query=""):
    needle = str(query or "").strip().casefold()[:100]
    matches = []
    for ident, title, category, purpose, steps in GUIDES:
        combined = " ".join((title, category, purpose, *steps)).casefold()
        if not needle or needle in combined:
            matches.append({
                "id": ident, "title": title, "category": category,
                "purpose": purpose, "steps": steps,
            })
    return matches


def guide_by_id(identifier):
    matches = [guide for guide in list_guides() if guide["id"] == identifier]
    if not matches:
        raise store.StorageError("Unknown defensive guide.")
    return matches[0]


def guide_template(identifier):
    guide = guide_by_id(identifier)
    checklist = "\n".join(
        f"[ ] {number}. {step}"
        for number, step in enumerate(guide["steps"], 1)
    )
    return (
        f"WORKFLOW: {guide['title']}\nPURPOSE: {guide['purpose']}\n\n"
        "AUTHORIZATION AND SCOPE:\nOwner:\nApproved lab:\nExclusions:\n\n"
        f"CHECKLIST:\n{checklist}\n\n"
        "EVIDENCE REFERENCES:\n\nCONFIRMED OBSERVATIONS:\n\n"
        "UNKNOWN OR UNVERIFIED:\n\nNEXT STEPS AND OWNER:\n"
    )


def render_report(lab):
    checked = store._project(lab)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    # Indented text preserves user notes without treating them as report headings.
    note_lines = checked["notes"].splitlines() or [""]
    indented = "\n".join("    " + line for line in note_lines)
    return (
        "# Kali Bay: Authorized Security Lab Report\n\n"
        f"Lab title: {checked['title']}\n\n"
        f"Lab ID: {checked['id']}\n\n"
        f"Saved revision: {checked['revision']}\n\n"
        f"Generated (UTC): {now}\n\n"
        "Evidence disclaimer: User-authored notes, not independently verified.\n\n"
        "## Saved investigation notes\n\n" + indented + "\n\n"
        "## Reviewer checklist\n\n"
        "- [ ] Confirm written authorization and scope\n"
        "- [ ] Verify evidence provenance and timestamps\n"
        "- [ ] Separate observations from assumptions\n"
        "- [ ] Record remediation owner and sign-off\n\n"
        "Generated locally. No scan, network request or upload was performed.\n"
    )


def export_saved_report(identifier):
    lab = store.get_lab(identifier)
    report = render_report(lab)
    base = store._private_base(create=True)
    destination = base / "reports"
    if destination.is_symlink():
        raise store.StorageError("Refusing linked reports directory.")
    if destination.exists() and not destination.is_dir():
        raise store.StorageError("Reports destination is not a folder.")
    destination.mkdir(mode=0o700, exist_ok=True)
    if destination.is_symlink():
        raise store.StorageError("Refusing linked reports directory.")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = f"{lab['id']}-r{lab['revision']}-{timestamp}"
    for serial in range(100):
        name = stem + (f"-{serial}" if serial else "") + ".md"
        path = destination / name
        try:
            fd = os.open(
                path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                getattr(os, "O_NOFOLLOW", 0), 0o600,
            )
            with os.fdopen(fd, "w", encoding="utf-8") as output:
                output.write(report)
                output.flush()
                os.fsync(output.fileno())
            return path
        except FileExistsError:
            continue
        except OSError as error:
            raise store.StorageError("Private report export failed.") from error
    raise store.StorageError("Too many report filename conflicts.")
