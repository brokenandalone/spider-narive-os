# Spider Guardian and OneDrive Vault

Source batch: 2026-10-08 UTC. These tools are implemented in GitHub, not evidence of installation on the owner's PC. The encrypted boot path, Webbie voice code, existing media package and desktop shell are preserved.

## Guardian

After installation, run:

```bash
/usr/local/lib/spider-os/system/bin/spider-guardian
/usr/local/lib/spider-os/system/bin/spider-guardian --json
/usr/local/lib/spider-os/system/bin/spider-guardian --bundle guardian-report.json
```

The read-only report includes the actual OS/kernel/Plasma versions, bounded service probes, free storage, network state, capture-device presence and installed-tool availability. It omits journal contents, microphone recordings, private configuration, network addresses and credentials. Reports are created with mode 0600 and an existing file is never overwritten. Service activity does not establish radio playback, authorized voice recognition or successful conversation. Repair actions and a graphical dashboard remain separate work.

## Select local backup sources

Copy `system/config/vault.example.json` to `~/.config/spider-os/vault.json`, with permissions 0600, and explicitly select directories. The shipped example selects nothing and disables cloud upload. Example selection, to adapt to the actual local paths:

```json
{
  "cloud_enabled": false,
  "crypt_remote": "",
  "sources": {
    "school": "~/Documents/Spider OS/Study",
    "author": "~/Documents/Spider OS/Author"
  },
  "exclude": ["*.log", "models/*", "*.gguf", "*.bin"],
  "max_file_bytes": 67108864
}
```

Only select projects whose contents you want backed up. Each selected source must exist. Missing sources, unreadable files, changed files or size limits fail the snapshot rather than silently declaring a complete backup. Symlinks, common credential paths/files and SQLite sidecars are excluded. This exclusion list is defense in depth; review selected projects for embedded secrets. The tool refuses whole-home and whole-filesystem selection.

Run `spider-vault` using the full path `/usr/local/lib/spider-os/system/bin/spider-vault` (or `system/bin/spider-vault` in a checkout):

```bash
spider-vault snapshot
spider-vault verify /path/to/snapshot
spider-vault restore /path/to/snapshot /path/to/new-recovery-directory
```

Snapshot output supplies the actual versioned folder path. It contains a h…3694 tokens truncated…[ ] Add rubric storage, papers, notes, discussion support, completed-work archive and source organizer.
- [ ] Add APA formatting assistance and document templates.
- [ ] Add Webbie Tutor with active-course context and instructor preferences.
- [ ] Provide supported SNHU portal links/integrations without insecure credential handling.
- [ ] Add optional selective encrypted OneDrive document backups.
- **Gate:** All active school material can be found and organized from School.

## Phase 8: Author workspace and Broken World tools

- [ ] Create a truly local-first manuscript editor with book library, chapter navigation and autosave.
- [ ] Add snapshots, version history, compare/revisions and recovery from interrupted saves.
- [ ] Add character profiles, location map, plot timeline, canon rules, clues and relationship graphs.
- [ ] Build a continuity checker for Broken World and an approval-before-edit workflow.
- [ ] Add chapter read-aloud, notes, writing goals and scene tracking.
- [ ] Add export to manuscript/ebook/print formats and backup bundles.
- [ ] Import existing manuscripts and companion materials without duplicate or overwritten chapters.
- [ ] Add encrypted selective OneDrive backups.
- **Gate:** Author can edit, save, search and recover a complete manuscript offline.

## Phase 9: Spider Studio and creative production

- [ ] Integrate installed Ubuntu Studio DAWs, audio interfaces, PipeWire/JACK, MIDI and plugins.
- [ ] Build songwriting/lyrics library, projects, arrangements, session notes and reusable templates.
- [ ] Add guitar effects, live monitoring, recording, mixing and mastering workflow shortcuts.
- [ ] Add Webbie producer controls for approved edits, research, brainstorming and project management.
- [ ] Integrate artwork, photo/video production and export presets (including album artwork).
- [ ] Add production-to-Media Center handoff and encrypted cloud backup of selected project files.
- **Gate:** Studio works as a useful creative workstation, not just a file manager.

## Phase 10: Spider Media Center, BCN and AI DJ

- [ ] Validate music, movies, TV shows, radio, photos, library/queues and saved playlists.
- [ ] Repair the GPU/audio-reactive visualizer without sacrificing existing playback functionality.
- [ ] Fix live radio playback versus "On Air" state; use one authoritative playback/broadcast status.
- [ ] Integrate AI DJ voice generation, breaks, ducking, crossfade, model selection and Webbie control.
- [ ] Add live TV support, network media sources, devices and casting where supported.
- [ ] Integrate BCN programming, station IDs, public relay and listener/broadcast diagnostics.
- [ ] Preserve a known-good media build, versioned rollback and regression tests.
- **Gate:** Playback, broadcast status, AI DJ and visualizer pass a continuous end-to-end session test.

## Phase 11: Forage, Deep Forage, Threads and Timeline

- [ ] Index local authorized files, projects, application entries and saved research.
- [ ] Add fast global search and per-workspace search with source links.
- [ ] Add Deep Forage multi-step research, source collection, synthesis and citation tracking.
- [ ] Create Spider Threads for linking research/materials across workspaces without copying everything.
- [ ] Create a searchable Spider Timeline of files, active projects, completed builds and approved actions.
- [ ] Make local indexes rebuildable from primary storage and protected backups.
- **Gate:** One search finds the right local material and preserves source/provenance.

## Phase 12: Dev Bay, Art & Design, Communications and Productivity

- [ ] Finish Dev Bay editor/terminal/project manager, GitHub, Python/C++ toolchains and development environments.
- [ ] Add build/test dashboards and validated continuous integration workflows.
- [ ] Build a Spider App Manager for modules, dependency checks, versioning, updates and permissions.
- [ ] Integrate drawing, painting, tattoo design, photo editing and graphics/video utilities into Art & Design.
- [ ] Add communications entry points for supported email, calendar and contacts integrations.
- [ ] Add productivity tasks, notes, reminders, schedules and an activity organizer.
- **Gate:** Each workspace has a defined useful workflow and consistent integration contract.

## Phase 13: Devices, remote access and Kali Bay

- [ ] Build Devices dashboard for storage, USB, Bluetooth, display, network and audio peripherals.
- [ ] Verify the usable 64 GB drive and diagnose the questionable "256 GB" drive capacity before allocating data.
- [ ] Provide secure remote desktop/control from phone and laptop with authentication and network access controls.
- [ ] Test up to three desired remote sessions subject to hardware/resource capacity.
- [ ] Finish isolated Kali Bay/Kali Purple environment and safe graphical security tool launchers.
- [ ] Keep Kali package changes inside its isolated environment rather than polluting the host.
- [ ] Add Webbie Security Assistant through an explicitly permissioned boundary.
- **Gate:** Remote access is secure, hardware tools are reliable and Kali cannot silently alter the host.

## Phase 14: Portable AI DJ and recovery media

- [ ] Build the portable 64 GB AI DJ edition only after the installed Media Center and Webbie audio paths are stable.
- [ ] Package small offline model/runtime, voice assets, cues, station liners, break cache and configuration within actual tested USB capacity.
- [ ] Make portable storage removable without breaking normal Spider OS operation.
- [ ] Design a bootable Spider Recovery environment with diagnostics and encrypted-disk repair support.
- [ ] Document how to restore the working internal-drive installation and key data from backup.
- **Gate:** The portable build works on its target machine and the recovery path is tested.

## Phase 15: Future OS release migration and final qualification

- [ ] Keep the working install as baseline; confirm the actual supported upgrade path before selecting an Ubuntu Studio release.
- [ ] Prepare a dedicated migration branch; pin GitHub Actions runner images and release dependencies.
- [ ] Port packaging, KDE/Plasma, kernel, systemd, audio and desktop dependencies without discarding working fixes.
- [ ] Build ISO, checksums, reproducible logs and a VM boot/install test.
- [ ] Validate installed-VM first boot, encrypted unlock, launcher/service startup and second reboot after install media removal.
- [ ] Run physical-media and physical-machine qualification only with tested rollback options.
- [ ] Test installed Webbie, The Web, OneDrive offline behavior, School, Author, Studio, Media Center, Forage, Kali Bay and Recovery end to end.
- [ ] Promote the migration to the new baseline only after all qualification gates pass.
- **Gate:** A genuinely bootable, supportable Spider OS release, not merely a successful ISO build.

## Tracking convention

- Keep tasks unchecked until verified on the **installed** machine or in the named test environment.
- For completed tasks, append the test date, version/commit and evidence link or short log reference.
- Add blockers under their phase; do not skip a safety gate because an exciting feature is waiting.
- Revisit priority order after each phase, but preserve the rule: **working installed system -> reliable Webbie -> recovery/OneDrive -> workspaces -> future distribution release**.
- Keep `docs/SPIDER_OS_26_10_MASTER_PLAN.md` as the broader release roadmap; use this document as the ordered installed-system execution checklist.

## GitHub implementation batch: Guardian and Vault

2026-10-08 UTC: Source for the Phase 2 read-only Guardian report and Phase 3 selected-source local snapshots / optional encrypted OneDrive copy is implemented. See `docs/GUARDIAN_AND_VAULT.md` for commands, regression coverage and remaining live gates. The vault user timer is packaged but disabled. A fast pinned-runner CI workflow now validates source on pushes and pull requests without launching the ISO build.

All installed-machine checkboxes above remain unchanged. This batch does not establish installed deployment, live OneDrive authentication, voice enrollment or encrypted boot qualification.
