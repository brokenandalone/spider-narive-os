# Spider OS | October 12 owner-first code reconciliation

**Status:** SOURCE STAGING ONLY. No approved install, no model change, no service restart.

This branch extends Wave Five safety PR #99. We inspected the 31 owner-installed
code files submitted October 12. The live files contain custom browser, Webbie
microphone and other changes, while the newer source candidate contains GUI and
workspace features absent from the live versions. Their differing bytes are
NOT evidence either one is safe to overwrite.

## What is actually built

`tools/build_owner_preserving_stage.py` constructs a new, **local-only**
source tree from an EXACT candidate Git commit and the 31-file owner ZIP:

- Copies only Git-tracked source files, not untracked secrets, credentials,
  model binaries, private memories, manuscripts, personal music or documents.
- Validates ZIP names, duplication, type, size, Python syntax and Bash syntax;
  checks every owner ZIP file still equals the actual installed PC file.
- Preserves all 31 owner-installed files **byte-for-byte** in the staged tree
  instead of unreviewedly overwriting Webbie, The Web, Study, Author, Studio,
  Kali Bay, Forage or Nova.
- Keeps remaining new candidate files intact, without pretending their GUI
  hooks or class imports have been successfully activated.
- Reports candidate-only and owner-only top-level Python APIs for each of
  those 31 files. Differences are marked as requiring human semantic merging.
- Writes no files to `/usr/local/lib/spider-os` and no credentials or source
  to GitHub. It does not alter the original checkout or run any Spider OS code.

**IMPORTANT:** This staging tree is NOT ready to install. Preserving installed
entrypoints means new dependent features may remain unconnected. Copying
source files also cannot prove microphones, model selection, GUI widgets, boot,
rollback, audio, performance or the absence of cross-import incompatibilities.

## For the owner PC, after the branch's exact SHA passes GitHub CI

Clone/fetch this branch into an isolated checkout. The previously submitted
archive should be at
`~/Downloads/Spider_OS_Conflict_Source_Review.zip`, and the actual installed
files must still match those copies. Read-only old audit reports are not install
approvals.

```bash
cd ~/Downloads
git clone --single-branch --branch reconciliation/oct12-owner-preserving-stage \
  https://github.com/brokenandalone/spider-narive-os.git Spider_OS_Owner_Reconcile
cd Spider_OS_Owner_Reconcile

# Run the standalone staging process; do not use sudo.
python3 tools/build_owner_preserving_stage.py \
  --source . \
  --owner-archive ~/Downloads/Spider_OS_Conflict_Source_Review.zip \
  --installed-root /usr/local/lib/spider-os \
  --expected-commit "$(git rev-parse HEAD)" \
  --output ~/Downloads/Spider_OS_Owner_Preserved_Review
```

**The SHA used must additionally be verified against the passing CI run's
SHA**, not just the HEAD of any arbitrary downloaded branch. To prevent
silent branch movement, pin to the CI-verified exact SHA supplied in the
completed release notes.

The `reconciliation.json` output contains no code contents or private
configuration. Do not install from `staged-source`. Do not capture a
known-good state if the installed PC is not actually working.

## Remaining engineering steps

1. Resolve symbol and behavioral differences: especially Webbie's live Firefox
   controls, durable research, self-echo filtering, microphone RMS/frame
   capture, speech interruptions and configured `qwen3:8b` model.
2. Integrate new candidate functions into retained owner code with import/
   method-interface and functional tests rather than blindly selecting one
   whole `webbie.py`, `whisper_listener.py`, or GUI file.
3. Test new Studio, Study, Author, Kali Bay and The Web workflows on a separate
   build; verify Nova audible radio playback rather than just HTTP health.
4. Prepare and test a clean pinned candidate with full CI and per-feature
   regression checks; obtain fresh owner-PC review, rollback confirmation and
   owner approval for ONE system installation.
5. After successful real-PC operation, explicitly capture the new known-good
   snapshot. Keep no-install gates closed beforehand.

**Source-only CI is not physical verification.**
