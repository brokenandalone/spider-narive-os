# Spider OS Kali Bay: Hybrid desktop design

Kali Bay's `DESKTOP HUB` is a **native Spider OS Qt workspace**, not a second
Kali XFCE session. It deliberately combines a Kali-style searchable app menu
and workbench shortcuts with Spider's purple wallpaper, workspace shell,
notifications and one shared Webbie assistant. All security applications are
launched through the existing rootless Kali Distrobox manager.

## What the initial UI provides

- Three prominent native tabs: `DESKTOP HUB`, `OFFENSIVE` and `PURPLE DEFENSE`.
- Kali-style categorized tool menu: search by tool/category, filter category,
  double-click or select and press `OPEN SELECTED TOOL`.
- Approved GUI apps: Wireshark, Burp Suite, OWASP ZAP, Ghidra, ClamTK.
- Approved CLI *workbenches*: Nmap, Metasploit, Suricata, YARA, Lynis. A
  workbench opens a terminal; it **does not** start a scan, service, attack or
  monitoring action.
- `KALI TERMINAL` uses the existing manager's terminal command.
- `KALI FILES` opens the fixed, existing persistent Distrobox home
  `~/.local/share/spider-os/kali-bay/home` in Dolphin (or xdg-open fallback).
  It is **not** a separate container GUI file manager.
- `ASK WEBBIE · SECURITY ASSISTANT` opens the single dock owned by The Web,
  never a duplicate voice service. A standalone Kali window explains how to
  get to Webbie through The Web.
- Quick navigation to `OFFENSIVE SECURITY` and `PURPLE DEFENSE`.

This UI changes only the Kali Qt application and its tests. It neither
reinstalls the operating system nor changes Kali packages or running
container state. The targeted installer in PR #13 already covers the changed
Kali Qt source file and preserves the existing local backed-up installation.

## Dependency and compatibility

Stacked on PR #13 (`upgrades/kali-bay-security-tool-launchers`). The recent
Webbie controls in PR #39 are on a separate stacked desktop/Webbie branch.
Before a coordinated owner-PC install, reconcile **both** branches and their
distinct inherited base histories. Do not blindly merge the older desktop's
Kali UI over the newer locally installed PR #13 Kali implementation.

PR #39 provides Webbie's deterministic, fixed-allowlist tool commands;
this UI supplies discoverability, searchable menus and a button into that
same assistant. Neither branch grants Webbie a general shell, root commands,
or permission to execute arbitrary target-based scans.

## Acceptance steps

1. Run Python syntax and Qt offscreen regressions from the source checks.
2. Confirm that Desktop Hub lists ten fixed tools, supports search/category
   filters and links to each security tab.
3. Verify `kali-bay --purple` and `--offensive` select indices 2 and 1.
4. Test missing/stopped container and unavailable tools, verifying that
   neither search nor status triggers installation or container startup.
5. On the installed Spider OS, confirm file manager opens the dedicated
   Kali home, Webbie dock is not duplicated, desktop resize fits the screen
   and theme/wallpaper remain intact.
6. Verify one GUI launcher and CLI workbench with the existing Kali container.
   Test rollback of the targeted Kali UI installation using its timestamped
   backup. Preserve disk, encryption, Webbie, Studio and media customizations.

## Next-phase upgrades

- Per-tool help and owner-approved lab profiles, with saved authorized scope.
- Read-only interpretation of user-selected local logs and authorized results,
  with source-aware reports and redaction.
- Optional curated defensive SOC views and evidence/case-workflow history.
- A true independent **Kali XFCE desktop** only if specifically requested,
  packaged separately as a qualified VM or remote desktop; Distrobox is not a
  hard security boundary or a full separate Linux boot environment.
