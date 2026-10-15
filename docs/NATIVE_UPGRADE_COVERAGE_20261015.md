# Spider OS native upgrade audit

**Audited:** 2026-10-15  
**Branch:** `reconciliation/ubuntu-studio-26.04-lts-20261015`  
**Production foundation:** Ubuntu Studio 26.04 LTS, reported by the owner  
**New-build test ISO target:** official Ubuntu Studio 26.04.1 LTS  
**Authoritative code:** `brokenandalone/spider-narive-os`  
**Purpose:** ensure previously developed upgrades remain visible, protected and verifiable without pretending they have already been installed.

## Checked in source and package staging

The `tools/audit_upgrade_coverage.py` gate checks actual source files and both the *installed* and *live* ISO staging paths. It is run by `Spider OS source checks`.

| Upgrade | Source location | Source/package assessment |
|---|---|---|
| The Web native shell | `the-web/shell/` | Present; both layer payloads stage The Web |
| Immersive bays | `the-web/shell/immersive_bays.py` | Eight confirmed visual surfaces, inside real tabs |
| Native Workspace MAX | `spider_max_source/spider_monster/`, `workspace_max_native.py` | Reviewed engine included; 137 operations covered by source tests |
| Webbie resident assistant | `webbie/`, `the-web/shell/webbie_*.py` | Source staged; live mic, speaker permissions and hardware not verified |
| Spider Studio | `studio/` | Native Studio app, multitrack, production board, QC and release tools included |
| Author / Broken World | `author/` | Native manuscript editor, canon, timeline and continuity tools included |
| School / Study | `study/` | Native course, APA and dashboard source included; portal login not part of image |
| Forage and Deep Forage | `forage/` | Search/index/research engine source staged |
| Kali Bay | `kali-bay/` | Native Bay, evidence and safe tool controls staged; actual installed Kali environment unverified |
| Media Center / Nova bridge | `media/`, `system/apps.py` | Launcher/controller source staged; see critical binary packaging gap below |
| System, Recovery, Guardian and Vault | `system/` | Program source included and required service files staged |
| Wallpaper catalog | `branding/wallpapers/`, `branding/workspaces/` | Packaged files and integrity verification included |

**Separate bays are native application interfaces.** The immersive scenes are part of these workspaces. They are not a replacement launcher. `main.py` retains `create_native(...)`, the actual media/Webbie panels, and MAX operations in their own QTabWidget sections. Four native apps (Studio, Author, Study, Kali) also contain their own integrated tool panels.

## Destination workspace audit

The existing shell registry contains fifteen top-level entries, but they are not the final planned fifteen. **Productivity** and **Devices** are not yet in the native registry; **Recovery** and **Games** still appear top-level. Preserve the existing tabs and their state until the new bays work. Recovery must eventually sit inside System.

This shortfall is deliberately reported by `tools/audit_upgrade_coverage.py` as a **destination-workspace gap**, without mislabeling source-level CI failures as lost legacy functionality. See issue #114 for the completion gate.

## Explicit blockers before declaring the repositories identical to the PC

1. **Installed machine comparison missing.** The owner reports Ubuntu 26.04, but GitHub cannot inspect the current live filesystem, installed/local-only changes, or the LUKS/boot configuration. Run the separate read-only audit from `docs/INSTALLED_26_04_RECONCILIATION.md` on the PC. Never replace local changes automatically.
2. **Main is an older snapshot.** The 26.04 candidate remains isolated. Do not merge over the boot-tested host baseline until conflicts, source checks, VM install, encrypted unlock and recovery pass.
3. **Media Center executable package not included by default.** The native ISO's `distro/install-spm.sh` supports optional ZIP inputs, and its personal compatibility candidates still reference old Spider Media Player 7.5.0 bundles. The public build may omit that app entirely. The separate `Spider-Media-Center` repository has the current V6 baseline and a V7 preview ASAR, but an ASAR update requires an already verified Linux Electron application runtime. Do not substitute the old ZIP or claim that the V7 renderer/BCN stream is physically validated.
4. **Ubuntu Studio 26.04.1 ISO layout not yet qualified as a completed Spider ISO.** The builder and installer catalog contain historical `standard.squashfs`, `standard.live.squashfs` and Subiquity assumptions. The upstream signature preflight passing does not establish that the new image has the same layer names.
5. **Hardware/voice/3D tests missing.** CI's offscreen Qt tests are not proof of production audio, camera, voice authorization, local GPU visualizer performance, real radio output, Bluetooth, TV or physical boot.
6. **Additional topic branches differ.** Some older feature branches diverge from the newest source history. They may include differences worth reconciling; the mere fact their files exist in the latest snapshot is not proof every older change is safely combined. Review differences before cherry-picking.
7. **Secrets and private projects must stay out of public Git.** The public source should never acquire credentials, personal manuscripts, student submissions, media libraries, encryption material or local AI memory.

## CI acceptance sequence

**Completed for the 26.04 candidate:** signed upstream release metadata validation; Python/shell regression checks; an offscreen native workspace check; vendored MAX source checks; installed/live source-file staging inventory.

**Still required:** authoritative installed-versus-Git hash comparison; compare/review diverged feature branches; verified Media Center runtime packaging; full 26.04 ISO build; disposable VM install/boot and second reboot; LUKS unlock rehearsal; actual desktop, Webbie, Kali, GPU and audio hardware tests.

The experimental 26.10 branch remains isolated and does not replace 26.04 LTS.

This is a *coverage and release-readiness report*, not a claim that all native upgrades are already installed.
