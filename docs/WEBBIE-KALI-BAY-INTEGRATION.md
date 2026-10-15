# Webbie × Kali Bay control bridge (October 10, 2026)

## Scope

Webbie's existing `Security Assistant` workspace context is now backed by
**deterministic** actions. When the owner opens **The Web → Kali Bay → Ask
Webbie about Kali tools**, the existing dock opens and drafts a tool-list
request; nothing executes until the user presses Send. Voice phrases use the
same explicit allowlist, subject to Webbie's existing wake/sleep controls.

Examples:
- "Webbie, list Kali Bay tools"
- "Webbie, check Kali Bay status"
- "Webbie, open Purple Defense"
- "Webbie, open Wireshark"
- "Webbie, open Burp Suite"
- "Webbie, open Nmap" (opens a workbench, **does not scan**)

Tool choices: Wireshark, Burp Suite, OWASP ZAP, Ghidra, ClamTK; read-only
workbench launch for Nmap, Metasploit, Suricata, YARA and Lynis. The bridge
only sends fixed arguments to **the already-installed Kali Bay manager** and
does not accept arbitrary commands, shell fragments, targets, remote
connections, privilege escalation, package install/update or background
security daemons.

## Required dependency and integration

The combined development branch now includes the approved Kali manager from PR #13, the Kali-style Desktop Hub from PR #40, and Webbie's fixed-allowlist bridge from PR #39. These source versions are consistent. The user's installed Kali files, Webbie customization and rootless Distrobox state still require backup-first inspection and local testing before deployment.

The user's real installed Webbie may contain local customizations that are
not identical to either branch. Compare and back up `webbie.py`, the Kali
manager, the Kali native UI and the desktop main file before deployment.
The first release batch should carry both PR #13 and this bridge. Keep
the owner's existing encrypted boot, rootless container, KDE session,
Webbie voice models, GUI customizations and tool/package set.

## Security invariants

1. Only a **literal single-line human request** can trigger a bridge action.
   Workspace titles, camera metadata, LLM responses and external results
   cannot supply tool arguments.
2. Every tool ID is fixed and checked by `kali-bay tool-check` first.
   A missing/stopped container does **not** trigger implicit startup or
   installation. No scan begins on launch.
3. Kali launches have no `shell=True`, no user-supplied command flags and
   no target strings. Host privileges and package state remain unchanged.
4. Distrobox shares the Linux host kernel and is **not** a high-isolation VM.
   Further penetration-testing automation or sensitive scans must be
   deliberately scoped to authorized targets, with a separate confirmation
   and auditable operation record.
5. Voice enrollment/profile recognition must be validated on the owner's
   machine before allowing unattended sensitive actions. The new bridge
   does not itself authenticate a speaker or turn Webbie into a root agent.

## Acceptance tests before calling this installed

- `python3 -m unittest tests/test_webbie_kali_assistant.py` (or discovery)
- `python3 -m py_compile webbie/agent/kali_assistant.py webbie/agent/webbie.py`
- Confirm Kali Bay sidebar opens the existing Webbie dock and leaves the
  prefilled request unsent.
- "list Kali Bay tools" works with container stopped.
- "check Kali Bay status" reports container vs ready correctly.
- "open Wireshark" checks first; if stopped/missing, Webbie explains and
  does not start the container.
- With an intentionally started, healthy Kali Bay, launch one GUI tool
  and one workbench, with no scan occurring.
- Verify webcam instructions or workspace titles cannot launch tools.
- Verify Webbie sleep blocks voice commands, non-owner voices do not
  operate tools, and "Webbie stop" remains responsive.
- Ensure fallbacks work with native The Web workspace and standalone Kali.
- Keep backups, smoke-test rollback, and record the installed commit and
  qualified versions.

## Follow-on work

Add defensive case notes, editable allowlisted lab profiles, reports with
redaction, read-only interpretation of authorized tool output, and explicit
per-target consent/audit logs before any active scanning automation.
