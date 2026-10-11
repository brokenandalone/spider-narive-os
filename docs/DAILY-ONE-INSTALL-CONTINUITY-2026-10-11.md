# Spider OS | One system-wide installation per day

**Owner's standing operating rule (October 11, 2026):** Develop any number of workspace changes during the day. **Do only one consolidated Spider OS PC installation per Indianapolis local calendar day**, after all intended changes are reconciled and a single combined candidate has passed source and installed-PC tests. Never install individual workspace upgrade branches independently.

## Daily workflow

1. **Build all day, install once.** Stage Webbie, The Web, Studio, Study, Author, Kali Bay, Forage/Deep Forage, Media Center/Nova and System/Recovery upgrades on development branches. Do not automatically install, copy live files, restart resident agents, or change the boot chain while developing.
2. **Produce a single pinned candidate.** Reconcile branch ancestry and overlapping files, particularly `webbie/agent/webbie.py`, `system/release_batch.py`, `study/study.py`, `the-web/shell/main.py`, `author/main.py`, `the-web/shell/webbie_panel.py`, and service/unit activation. Do not count individual passing PR checks as combined passing checks.
3. **Test continuity before approval.** Run one full source test suite on the exact combined commit, guarded installer preflight, UI offscreen smoke tests, identity/sleep/STOP tests, source links, missing files/entrypoint checks and backup/rollback simulations. Compare installed-PC customizations privately in an isolated stage tree; review critical workflows with actual hardware only when safe.
4. **Require explicit final approval and daily slot availability.** Read-only audit: `python3 tools/daily_release_continuity.py --backup-root /usr/local/lib/spider-os/upgrade-backups`. This will report **BLOCKED** until all entries in `system/daily_release_plan_20261011.json` have been reconciled and source, hardware, receipt, backup, rollback, and owner approval gates are satisfied. There is no `--apply` action in the audit.
5. **Make one backup, one install.** The batch installer serializes attempts and conservatively treats an earlier same-day receipt as an already-used (or ambiguous) install slot. It does not intentionally allow a second batch that day, even if a rollback occurred. Necessary **rollback and recovery are exempt** from this install frequency limit.
6. **Run one combined post-install acceptance pass.** Check encrypted boot and KDE, The Web, one resident Webbie process and speaking/STOP/sleep/camera consents, Studio local generation/mixing, Study files/APA/OneDrive opt-in, Author manuscripts/books/narration, Kali Distrobox, Forage citations/local indexing and Nova/Media Center audible broadcast. Record the installation receipt and bugs for the next day's batch.

## Continuity status discovered on October 11

The workspace upgrades are **NOT combined** yet. The source branches are listed in `system/daily_release_plan_20261011.json`, pinned to observed GitHub head SHAs as a review snapshot. They are not proof that those SHAs are in one checkout. At least these collisions exist:

- `webbie/agent/webbie.py`: PRs #54, #55, #58 and #61. Voice STOP, proactive behavior and Forage voice bridging cannot overwrite each other.
- `system/release_batch.py`: PRs #55, #56, #61 and #64. Merge one file manifest, not the last branch's copy.
- `study/study.py`: PRs #53 and #64. Ensure both class/dashboard changes work.
- `study/assignment_workflow.py`: PRs #53 and #64. Preserve existing workflow and versioned assignment behavior.

Other source branches might change after this snapshot. Refresh the manifest whenever new PRs land and re-run continuity tests. **An unlisted change or undocumented merge is a blocker, not a silent exclusion.**

## Safety and limits

- All existing home documents, schoolwork, manuscripts and original artwork, music stems, voice samples, credentials, Ollama models, encrypted boot setup, Kali Distrobox state, and established desktop customizations must remain intact.
- A GitHub source test **does not** establish that the PC has been reconciled. The daily audit intentionally treats an unverified installed PC as BLOCKED.
- The new daily lock is wired into the staged `system/release_batch.py` and is not yet installed on the live PC. Other unrelated manual installers are outside its enforcement scope and must not be run as separate system-upgrade batches.
- Once the local date changes, prepare a **new** pinned daily manifest and re-check all workspaces; do not reuse yesterday's approval.
- Website deployments to BCN Network are a separate external release process, not an automatic Spider OS PC installation.

## Offline checks (source-only, safe)

```bash
python3 -m unittest tests.test_daily_release_continuity tests.test_daily_install_policy
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tools/daily_release_continuity.py --json
python3 tools/combined_release_audit.py
python3 system/release_batch.py --check
```

The continuity audit's current nonzero exit status is **expected** while candidate branches remain separate. Do not remove blockers just to turn it green.
