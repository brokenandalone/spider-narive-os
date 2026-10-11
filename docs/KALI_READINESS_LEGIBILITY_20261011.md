# Kali Bay readability + readiness upgrade (October 11, 2026)

## Purpose
This is a **source-only, draft** upgrade for Spider OS Kali Bay. It is stacked on the native Kali application-catalog work in PR #46. It does **not** create a VM, replace the existing Kali Distrobox, alter Kali packages, or start Webbie.

## Changes
- Explicit light text/dark backgrounds on Kali's search field, application dropdown and popup, plus visible keyboard focus, brighter tooltips and narrower security tabs. Menus should be readable in the purple workspace even when the host KDE theme changes.
- Add **READINESS REPORT** and an inline summary in the existing Desktop Hub. This displays whether Podman and Distrobox exist, whether the current Kali container is missing/stopped/running, whether the `kali-linux-everything` metapackage is verified, whether a GUI session is available, and a bounded next-step explanation.
- Add `kali-bay readiness-json` to the existing manager. This is a fixed, local JSON status query: no Distrobox entry, new container, package operations, scans, root access, model-generated commands or service changes. Unlike the older manager subcommands, it does not create state directories as a side effect.
- New regression tests use mocked Podman/Distrobox and cover ready, stopped, missing, unknown and unverified states; GUI styling checks ensure the contrasting selector/menu styles are retained.

## Review and local checks
Source syntax/test checks:
```bash
bash -n kali-bay/bin/kali-bay
python3 -m py_compile kali-bay/ui/kali_bay.py
python3 -m unittest discover -s tests -p test_kali_readiness.py -v
```

On an intentionally selected release, the owner can review differences first:
```bash
bash kali-bay/package/install-kali-bay.sh --check
```

Do **not** run the selective install until current customized PC files have been compared and backed up and the combined Spider OS release is qualified. This branch changes the existing Kali Bay manager and UI files. It does **not** change the installer manifest and needs no additional installed runtime file. If the integrated release is used instead, resolve this branch against the currently staged release branch first.

After a reviewed deployment, the desktop control shows its output; alternatively:
```bash
/usr/local/lib/spider-os/kali-bay/bin/kali-bay readiness-json | python3 -m json.tool
```

The readiness result reflects the current PC, not GitHub CI. Kali Bay uses the real Kali userspace and tools from the existing Distrobox, sharing Spider OS's kernel. It does not pretend to be an independently booted Kali system. Webbie retains existing owner/speaker controls, and this change does not add voice-triggered scanning or privileged actions.

## Acceptance gates
1. GitHub source syntax/tests green.
2. Review against the **current** six customized on-PC scripts, especially Kali UI and Webbie agent.
3. Review rollback and full one-batch release manifest. **Do not** force this branch over production.
4. On-PC verification: menu contrast, keyboard navigation, stopped-container safety, KDE/X11 app popups, actual Kali installed-app opening, existing Webbie dock and voice identity gate.

**Deployment state: not installed, not merged.**
