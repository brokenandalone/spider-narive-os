# WEBBIE JARVIS CORE · MAJOR UNIFIED RELEASE
October 12, 2026 | Source-only draft | Not installed on any owner's PC

## One release, not isolated feature waves

This source branch starts from the permanently authorized Webbie work in
PR #96 (itself incorporating the staged single-click grant, trusted voice,
Cognitive Control Center, JARVIS Brain/Eyes/Hands, Native Operator, and
Spider OS release checks). The intention is a **single coordinated,
reversible installation** *after PC-specific source reconciliation*.

**These source components are not evidence that an end-to-end JARVIS
assistant, cloud service connections, privileged system repair or browser
administration are already working on the owner's physical computer.**

## What was built in this major integration

### JARVIS Mission Center in The Web
New native UI entrypoints:
- **JARVIS Mission Center · projects, websites, system** in resident Webbie.
- **JARVIS missions** in the Cognitive Control Center.

A single owner-selected folder and bounded action, with an asynchronous
worker and explicitly separate **STOP this mission** versus
**STOP all Webbie control**. Startup never runs a mission. A model
response, malicious document, website, image or terminal output can
never authorize or enqueue a mission by calling this UI.

### Local file/project evidence search
Owner chooses a local folder beneath their home. Search is read-only,
limited to 1,500 ordinary files and 25 text matches, with a size cap,
file-extension allowlist, credential-like file exclusions, symlink and
hardlink exclusion and no full-home indexing. Text results are
excerpts labeled **untrusted evidence**, never commands.

Suitable for source, HTML/JS, README, project manifests, song lyrics
in plain text, and written notes. PDF/DOCX/SQLite/hidden project data
are NOT indexed by this new adapter. Connected Drive/Gmail/OneDrive
content is NOT included by default.

### Website project audit
The owner chooses a local website folder such as their BCN site.
The audit checks bounded HTML pages for missing referenced local
scripts, images and stylesheet assets. It identifies root index
presence and gives a reviewable report. This is not a deployed-host
audit or proof that the radio stream works, and it does NOT run
untrusted build scripts or publish anything.

### Actual local website hosting (development preview only)
The owner can select a website folder and click **Host local website
preview (127.0.0.1)**. Webbie's bundled static-only HTTP service
serves HTML, CSS, scripts, images and other safe public asset types
on an automatically assigned loopback port. The preview URL
can be opened by an explicit click. It does not bind to a public IP
or deploy to GitHub Pages or a hosting provider. It rejects path
traversal, symlinks, hidden files, credential-like names,
directory listings and POST/PUT/DELETE. Closing the mission
or pressing STOP shuts it down. No site build scripts execute.

### Integrated Forage public web research
The owner can choose **Research the public web with Forage** and enter a
short research topic. This calls the existing Spider Forage public DDGS search
engine, returns bounded results with public HTTPS source links and short
snippets, and explicitly labels content untrusted. It does not run model
commands, log into accounts, open pages automatically, download tools or
retain the content. Requires Forage's optional DDGS dependency on the PC.

### Integrated system diagnostics
JARVIS Core integrates Webbie's existing console diagnostic adapter
to read uptime, kernel, memory, disk space and the local service
status of Webbie, Nova and Ollama without executing arbitrary shell
strings or privileged commands. Read-only results are shown in
Webbie's native mission interface, with canceled output discarded.

### Shared permanent authorization and STOP
The release inherits the owner-private standing safe-access record,
pause/resume/revoke distinctions, verified voice/Kali rules, ordinary
application and website requests, existing Qt desktop control, and
the guarded single-batch release pipeline.

Before and after a mission, the core validates that owner authorization
is still active. Concurrent missions are rejected and STOP discards
pending output. The UI also stops work on sleep or parent close.

### Existing capabilities retained
- The Web native shell, owner desktop commands, installed-app launches
- Approved public HTTPS site opening
- Existing Webbie audio, face UI and camera consent flows
- Kali Bay inventory-confirmed app opening on direct owner request
- Focus Task / guided workflow stage and truthful receipts
- Nova, OneDrive and Webbie local status integrations
- Proactive health checks, Forage project subsystem and other workspaces

## What is intentionally NOT claimed as complete

These need working, separately scoped operator adapters and live checks:
- **Website hosting and deployments**: actual hosting-provider auth,
  site build preview, deployment, rollback and observed site behavior.
- **Unrestricted GUI editing**: understanding the true meaning of arbitrary
  buttons and preventing accidental destructive action in any application.
- **General shell execution**: safe maintenance recipes, backups, privilege
  escalation approval, safe restart/rollback and verified results.
- **Full Kali tool execution**: runtime flags, permitted target definition,
  meaningful consent, execution limits, safe command receipts and reports.
- **Connected accounts**: authenticated individual integrations for Google,
  GitHub, Microsoft, website hosting, messaging and other services.
- **Full proactive research**: scheduled knowledge processing beyond current
  read-only health checks; user-scoped source indexing with opt-in retention.
- **Live trusted voice**: the stacked strict Cory/Shayna-only segment
  verifier still requires an enrolled, validated local biometric backend.

A permanent policy record does not confer superuser rights, remote OAuth
consent, or authority to perform actions the owner previously excluded.

## Local PC source reconciliation command (read-only)

On the **actual Spider OS PC**, after checking out this exact release branch,
run:

```bash
cd ~/spider-narive-os
git fetch origin
git switch release/webbie-jarvis-unified-major-20261012
git pull --ff-only origin release/webbie-jarvis-unified-major-20261012
python3 tools/jarvis_install_preflight.py
```

This command has **no installation mode**. It reads the source manifest,
compares known checksums against the current installed
`/usr/local/lib/spider-os` tree, runs the strict source wiring audit,
checks backup headroom and reports whether a pinned offline speaker provider
is installed. Output intentionally contains source-relative names but no
private file contents, access tokens, passwords, personal documents, microphone
recordings or terminal history. The tool returns exit status 3 on blockers,
or 2 if still held for manual acceptance. It does not return an
"install approved" status.

It is normal to see blockers before the source has been reconciled with
the significantly customized PC. **Never work around a BLOCKED result
with a blind sudo apply.** First inspect owner-source conflicts and
preserve existing working desktop/voice/Nova/Studio/Media changes.

For machine-readable redacted output, run
`python3 tools/jarvis_install_preflight.py --json`.
The existing `tools/combined_release_audit.py` and
`tools/webbie_readiness_cli.py` remain available as complementary
read-only diagnostics.

### Owner-source reconciliation, all conflicting files in one private review

When the read-only PC preflight reports multiple BLOCKED customized files
(the October 12 local report found 21), do **not** force the installer.
First run this second, read-only tool from the **same, separate release
clone** after `git pull --ff-only` on the already checked-out branch:

```bash
REVIEW="$HOME/Downloads/Spider_JARVIS_Reconcile_$(date +%Y%m%d_%H%M%S)"
python3 tools/jarvis_reconcile_preview.py --output "$REVIEW"
```

The tool checks every proposed release target once, reviews the files
that the existing strict installer marked BLOCKED, and queries **local Git
history only** for content-identical versions of those same relative paths.
It prints only relative module names and counts. Output goes to one
NEW, user-only directory (mode 0700) containing bounded private source
diffs (mode 0600), `summary.json` and a cautionary README.

Results have clear meanings:

- `recognized_git_blob_manual_review`: the installed file matches a
  historical blob on some local Git ref **at that path**. It is not a
  license to overwrite the installation. Identify the original branch
  and confirm behavior before extending recognized baselines.
- `custom_code_manual_merge`: the installed code is not the exact content
  of a historically recorded source at that path. Preserve features and
  reconcile edits before building a combined release.
- `unsafe_path_manual_review` and `unreadable_or_large_manual_review`:
  do not merge automatically; the file cannot be safely inspected.

**Never upload the complete private diff folder**, as it may include
owner source comments, paths or sensitive local configuration text. The
safe-to-share console summary and `summary.json` contain only module
metadata. GitHub does not receive files from this tool, and the installed
Spider OS is not changed. Voice enrollment is a separate gate.

### Voice STOP critical correction

A direct spoken STOP reaches the live audio interruption callback
*before* the normal Webbie command handler. The new release now persists
`paused=true` from **both** paths. Otherwise the owner's permanent
authorization could resume on the next GUI login despite the actual
spoken STOP. The test suite isolates and exercises the real nested
interruption callback without opening audio hardware.

The source currently includes only the **hash-pinned speaker verifier
loading framework**, not a validated Cory/Shayna identity model on the PC.
Even a hash-valid provider requires physical enrollment and live liveness
and rejected-speaker tests. Speaker identity must not be inferred from
Whisper text, faces, names or wake words.

## Acceptance gates before a single PC installation

1. Record the hashes of the customized local Spider OS and reconcile
   owner-source drift. Preserve Webbie's currently working voice/Matilda,
   microphone, models, the full KDE desktop and every application.
2. Resolve existing strict speaker gate provider and verify actual
   Cory/Shayna recognition on the workstation. STOP must remain universal.
3. Run the entire GitHub source test suite and audit the combined-release
   manifest. Verify test names/outcomes, not only CI's overall indicator.
4. Run the current batch release dry-run; block unknown source mismatches.
5. Create backups and an independently tested rollback plan. Install ONCE
   system-wide only after the owner approves the reconciled batch.
6. On hardware, verify Konsole, named Kali tool launcher, XDG apps, public
   websites, file research, website asset audit, STOP/pause/revoke, GPU,
   Ollama, camera consent, Nova audio, Studio, Author, Study, Forage, Kali
   Bay, Media Center and The Web. Record observed versus requested actions.
7. The Ubuntu Studio 26.04 LTS underlying OS upgrade is a separate
   carefully managed boot/partition/system migration, NOT part of this
   user-space JARVIS source drop.

The on-PC installation was not run by this PR. One safe combined source
release remains the owner workflow; no separate module-by-module
installation is authorized here.

## Regression tests
- tests/test_webbie_jarvis_local_evidence.py
- tests/test_webbie_jarvis_site_audit.py
- tests/test_webbie_jarvis_orchestrator.py
- tests/test_webbie_jarvis_mission_gui.py
- tests/test_webbie_jarvis_forage_research.py
- tests/test_webbie_jarvis_local_site_preview.py
- tests/test_webbie_jarvis_install_preflight.py
- tests/test_webbie_jarvis_reconcile_preview.py
- Existing Webbie, voice, trust, browser, desktop, workspace, release,
  Studio, Author, Study, Kali Bay and media checks.

The source files are entered in:
- system/release_batch.py
- tools/combined_release_audit.py
