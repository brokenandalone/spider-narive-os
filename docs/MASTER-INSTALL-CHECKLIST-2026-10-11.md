# SPIDER OS | OCTOBER 11, 2026 MASTER INSTALL CHECKLIST
**Release:** Spider OS October 11 combined daily batch  
**Source branch:** `release/oct11-consolidated-pc-review`  
**Base:** tested but still draft Wave Three `ae48fd46dbdc5ae082247ab4dacf392d87251f6b`  
**Installed baseline:** owner's October 10, 2026 full Spider OS installation, including newer PC-only customizations.  
**Status:** ⛔ REVIEW ONLY. **NOT a completed code merge, approved installer, or PC installation.**

## Scope and status
| Area | Work tracked | Source/release status | PC status |
| --- | --- | --- | --- |
| The Web | navigation, legible menus, tabs, windows, recovery; #52 latest e1d5891b5c | candidate must reconcile latest #52 with combined branch | October 10 PC baseline, Oct 11 not verified |
| Webbie desktop/Jarvis | focus, approved browser and desktop control, missions, STOP/sleep, trustworthy action receipts; #54 #58 #61 #67 #68 #69 #76 | Wave Three has earlier Webbie source, later heads need comparison | not installed today |
| Webbie Voice Lab and resilience | Voice Lab #78; timeout and private counters #88; Hearing/Speech v3 #89 (supersedes #85) | **overlapping** agent, brain, provider, speech and installer files; speaker enrollment absent | real microphone, output, STOP and Cory/Shayna authorization untested |
| Forage + Deep Forage | indexing, multi-engine research, source handling; #55 | included in Wave Three lineage; PC source may differ | not installed today |
| Kali Bay | native tools, command center, guided labs, evidence ledger; #60 #65 #70 | combined Wave Three source, no isolated Kali install | not installed today |
| Studio | v7–10 band mix, releases, board; new v11 PCM WAV quality and DAW handoffs #82 | Wave Three through v10; v11 NOT yet reconciled | not installed today |
| Author | import, Atlas, Master Canon; newer on-demand Canon Intelligence #83 | Wave Three through Master Canon; #83 NOT yet reconciled | not installed today |
| Study | assignments, deadlines, course reading and local coach; expanded passages #84 | Wave Three reading library; #84 NOT yet reconciled | not installed today |
| Nova on PC | existing local Spider AI DJ on 127.0.0.1:9876, Media Center integration | preserve running Nova; only smoke tests; no new credentials | last known health OK; recheck |
| Spider Media Center | v6 pinned installation; v7 3D visualizer scene-bank development | **separate repository/deployment**; newer renderer needs PC GPU test | do not replace V6 or local customized V7 blindly |
| BCN Network website | visitor/owner split, broadcast bridge, separate lore/art pages, v14 newsroom | **separate website repository** main has source; backend/media/gallery/live deploy unverified | not a Spider OS batch-install file |

See also `system/daily_release_plan_20261011.json` for branch head pins and unresolved overlaps.

## Mandatory release gates (all required BEFORE a single apply)
- [x] October 10 owner-installed full PC build designated as baseline; protect additional camera, audio, service and layout repairs.
- [x] Locate GitHub Wave Three source plus later unmerged PRs (#82, #83, #84, #88, #89) and identify changed-file overlaps.
- [x] Preserve the rule: **at most one full system installation per America/Indiana/Indianapolis calendar day**. Failed/partial attempts consume a slot until reviewed. Rollback is separate.
- [x] Leave central `system/release_batch.py` daily guard and **fail-closed** candidate plan intact.
- [ ] Port/merge latest PR heads into **one** reconciled source tree, not just a list of PRs. Resolve conflicts manually in `webbie/agent/webbie.py`, `webbie/brain/brain.py`, `webbie/voice/whisper_listener.py`, `author/main.py`, `studio/main.py`, `study/reading_library.py`, and `system/release_batch.py`.
- [ ] Update `APP_FILES` central installer allowlist and PC acceptance tool for genuinely approved new modules. **Do not add configuration, credentials, local model, voiceprints, backups or user data.**
- [ ] CI/unit/Qt tests, desktop smoke and release continuity pass **on the exact combined HEAD**. Passing isolated feature PR tests is insufficient.
- [ ] Read-only **PC** installed-file hash comparison reviewed, including PC-only customizations, Webbie camera/sleep and installed graphical menu fixes. Different hashes **do not** mean consent to overwrite.
- [ ] Confirm the PC has a valid daily install slot, disk space and safe backup destination; test complete rollback on a disposable/test workspace first.
- [ ] Confirm Webbie voice verification provider is actually installed, explicitly enabled and locally calibrated for only Cory and Shayna. If absent, **do not deploy a strict gate** that silently disables the live assistant. Test unauthorized voice/TV echo and immediate STOP.
- [ ] Preserve Webbie continuous conversation, local Ollama qwen models, offline speech, Webcam consent, Nova port 9876, Study documents, Author manuscripts, Studio projects, Kali Distrobox and wallpapers.
- [ ] Owner reviews completed PC comparison, source test evidence and rollback instructions, then approves the precise combined SHA.
- [ ] **ONE** guarded apply transaction; record backup manifest and exact SHA.
- [ ] Post-install: `--phase after`, service and Nova health, Webbie hearing/speech/cancel, camera, browser/app control grants, The Web readability, Forage research, Kali, Study, Studio, Author, Media, GPU and reboot/boot recovery.
- [ ] Separate BCN site backend/static deploy and Media Center GPU candidate in their own deployment workflows. Do not claim those were installed by the Spider OS batch.

## First owner-PC operation: inspect ONLY
Do **not** use `sudo` or `apply` for this stage. Copy-paste into Spider OS terminal:

```bash
set -e
mkdir -p "$HOME/Downloads/Spider_OS_Oct11_Review"
cd "$HOME/Downloads/Spider_OS_Oct11_Review"
git clone --single-branch --branch release/oct11-consolidated-pc-review \
  https://github.com/brokenandalone/spider-narive-os.git checkout
cd checkout
python3 tools/daily_release_continuity.py --json > ../release-continuity.json || true
python3 tools/daily_pc_acceptance.py --phase before --json > ../installed-pc-acceptance.json || true
python3 system/release_batch.py --check > ../installer-preflight.txt 2>&1 || true
echo "Reports saved to $HOME/Downloads/Spider_OS_Oct11_Review"
```

The `--check` command can emit blockers and must **not** be converted into `--apply` until the release is reconciled and approved. These reports only inspect fixed application files; they do not validate hardware, the owner speech provider or backups.

## Release gate owner
No tool connection here has remote filesystem access to the actual Spider OS desktop. A GitHub commit cannot install software on the PC or validate its microphones, speakers, running services and custom patches. The correct result until those validations finish is **NOT INSTALLED**, never “complete”.


## Rolling-update compatibility addendum (October 11, evening)
Additional source branches appeared **after this initial PR #91 inventory**:
- [PR #93](https://github.com/brokenandalone/spider-narive-os/pull/93): Wave Four Studio PCM audio checks, Author Canon Intelligence, Study passage provenance, and Webbie model resilience.
- [PR #92](https://github.com/brokenandalone/spider-narive-os/pull/92): separate Wave Four JARVIS workflow board. Do not assume it is integrated with #93.
- [PR #90](https://github.com/brokenandalone/spider-narive-os/pull/90): separate Webbie Brain/Eyes/Hands/Autopilot workflows. Overlaps #92/#93 and existing voice branches.
- [PR #89](https://github.com/brokenandalone/spider-narive-os/pull/89): separate Webbie Hearing/Speech v3. Requires explicit speaker boundary and microphone acceptance.
- [PR #94](https://github.com/brokenandalone/spider-narive-os/pull/94): new **installed-model compatibility hold** against the existing PC. It adds `model_compatibility_verified=false` to its own Wave Four release branch. Must be adopted by the ultimate candidate, not manually bypassed.

Do **not** use the older PR #91 audit package as installation approval for any Wave Four source. Refresh the exact candidate HEAD, overlap list, installed-PC checks, and model compatibility results after the *last* feature commit. Re-run the single combined CI and physical smoke tests on that exact commit.

The running October 10 Webbie may have a model newer than `qwen3:1.7b`. Preserve whichever exact model the owner's installed configuration and live service actually select. Never install source solely because the bundled default exists. The diagnostic `python3 tools/webbie_model_compatibility.py --json` (and owner-triggered `--smoke`) on PR #94 will block unknown or missing models. Installed config, Ollama blobs and personal voice enrollment must never be overwritten.

All source branches remain review-only. Unknown user-PC source, future commits, speaker verification, backup and rollback readiness remain independent installation blockers.
