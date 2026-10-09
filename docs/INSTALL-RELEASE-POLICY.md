# Spider OS installation and integration policy
Updated 2026-10-09, at owner's explicit direction.

## Owner's deployment rule
**Install by request, NOT by day.** Continue implementation, reconciliation and CI work in GitHub as frequently as helpful, but do not ask the owner to install multiple tiny updates during a single owner-requested installation session.

When the owner explicitly asks to install:
1. Freeze an exact audited integration commit containing all mutually compatible, source-tested changes the owner wants **in that installation batch**. Do not force unfinished, risky work into the batch.
2. Present one command or clear single entry-point preflight and one unified installer/transaction. Do not run separate overlapping component installers on the same source files; detect or block conflicts.
3. Preserve the working X11/The Web desktop, Author manuscripts, existing customized Webbie voice/mic listener and models, originals, boot/encryption, Kali Bay, Studio, Media, and owner-specific settings.
4. Generate one timestamped complete backup/manifest and tested, explicit rollback steps for precisely the files that will be changed. Test rollback in disposable CI fixtures before release. Stop safely on unrecognized local modifications; do not overwrite them silently.
5. Install only after explicit owner installation instruction and successful installed-PC preflight. Webbie OneDrive OAuth remains optional and independently user initiated.
6. Perform one deliberate application activation/log-out sequence and one comprehensive acceptance checklist. Source CI never substitutes for installed PC verification.
7. If a feature is not release-ready, clearly mark it deferred rather than silently swapping in an old or contradictory build.

**There is no daily install quota or scheduled daily installation.** A user-requested session is the batching boundary. Multiple separately requested installation sessions, including on the same day, are allowed.

## Current integration status (not ready to install)
Branch: `integration/webbie-author-camera-sleep-20261009`.
Initial commit: `1fd759bab3aa95054664323fea4a3a9ab6cd98c9`.
Stage contains PR #25 quiet sleep + inherited #21 OneDrive and face and #22 names, plus selected Author/camera support from #23 and independent local vision files from #24. The Webbie agent, shared panel and shell imports are NOT yet reconciled. This staging branch has NOT been demonstrated to pass integration CI. **Do not install it.**
PR #23 was updated by another chat during staging (observed `83d692b4c3115a2f4edeed2730a77774c2b49364`), after the initial staging source was selected. Reconcile latest source before declaring finished.

## Unified release source (still awaiting owner-PC preflight)

The integration branch now includes `system/release_batch.py`, the intended
**one-command, one-transaction** release entry point. It has read-only `--check`,
a guarded `--apply`, and explicit `--rollback-check` / `--rollback` for its
own manifest-backed batch backup. Its published regression tests exercise
unknown-customization blocking, additive installs, backup restore, symlink
protection and CLI parsing. Release CI also performs a non-mutating source
preflight. None of these tests supplies the Dell's actual hashes or proves
the installed Webbie voice agent is safe to replace.

**During a future explicitly requested installation session**, work from a
pinned, full local checkout of the final integration commit and first run:

```bash
python3 system/release_batch.py --check
```

If this says `BLOCKED`, do **not** try a different installer, bypass
safeguards or install individual PRs. Review the existing local files and
reconcile them into a tailored release first.

When the installed-PC checks and source freeze both pass, the single install
entry point is:

```bash
sudo python3 system/release_batch.py --apply
```

The installer prints a backup directory and rollback receipt. **These are
documented future commands, not instructions to run before approval.**

There is deliberately no automatic user-service restart during installation.
An intentional The Web session relogin activates the X11 portrait. OneDrive
continues local-only until the user manually chooses Connect OneDrive; it
enables the independent user-level sync timer only after sign-in. Webcam
access remains off until the user enables it.

## Single-chat ownership
The user requested ONE active Spider OS build chat as the source of direction. Other chats should not write to Spider OS branches concurrently. GitHub handoff and master checklist record status. If a competing branch changes, fetch and compare its latest commit before continuing. Do not claim other chats can be automatically stopped or merged by editing this file.
