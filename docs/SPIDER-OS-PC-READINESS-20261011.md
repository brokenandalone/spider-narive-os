# Spider OS: read-only owner-PC hardware and installed-file reconciliation

**Development branch only. No physical PC testing, install, service restart, camera, microphone recording, model enrollment, user file reads, or rollback performed.**

This is a preparation step for the **one consolidated Spider OS install per Indianapolis-local day**. Source CI is necessary but not sufficient. No current source branch may set \`installed_pc_reconciled\`, \`voice_pipeline_verified\`, \`owner_approved_install\`, or \`rollback_validated\` to true in place of actual owner-PC evidence.

## Exactly one harmless preflight report

Use an ordinary terminal on the **actual Spider OS PC** as your normal user. This creates a **separate temporary Git checkout**, leaving your installed \`/usr/local/lib/spider-os\` and personalized source tree untouched:

~~~bash
AUDIT_DIR="$(mktemp -d /tmp/spider-os-audit.XXXXXX)"
git clone --depth 1 --single-branch --branch release/pc-readiness-reconciliation-20261011 \
  https://github.com/brokenandalone/spider-narive-os.git "$AUDIT_DIR"
python3 "$AUDIT_DIR/tools/spider_pc_readiness.py" --checkout "$AUDIT_DIR" --json
~~~

- **Do not use sudo. Do not run install, apply, setup, reboot, or upgrade commands.**
- Read the printed JSON locally before sharing it. Default output deliberately excludes application source bytes, source hashes, microphone serials/names, network details, local account names and private file content.
- The temporary checkout can be left in place during review. Do not delete or alter a customized project to make a report look clean.
- To pin a source review to an exact candidate, append \`--expected-sha <40-character PR commit SHA>\`. A mismatch is an audit blocker. Use the latest reviewed pull request head rather than a short hash.
- \`--include-hashes\` is **only for local private reconciliation**, never for copy/paste of a public report.
- If the computer has no Git login, inspect/clone the branch through your normal authenticated workflow. Do not put credentials in a URL or shell command.
- Even if the report says \`REVIEW REQUIRED\` with no blockers, that is **NOT** install approval.

## What is checked, and what is not

The report compares only a fixed allowlist of Spider OS application-source hashes against the combined checkout. It reports \`matching\`, \`different\`, \`pending_add\`, or \`installed_unavailable\`. Known *new* wave modules may be absent before install; missing legacy applications or symlinked source do **not** count as normal additions. The actual combined installer still refuses unrecognized owner-customized code.

The hardware pass checks Ubuntu distribution/version, CPU architecture and logical count, memory, disk free space, KDE graphical session indicators, GPU render-node presence, whether essential tools are installed, and available non-monitor PipeWire input sources. It does **not** record audio, touch video capture, list USB serial numbers, inspect private device settings or claim to authenticate speakers. Existing \`webbie.service\`, \`spider-ai-dj.service\` and local Nova's loopback-only \`/health\` status are checked without starting or changing them. The local backup receipt inventory checks filenames under the fixed Spider OS backup location only, without exporting file contents.

## Decision process after the owner runs the report

1. Review \`files_summary\`, each \`different\` or unavailable module, and whether a same-day Spider OS batch receipt exists. Reconcile owner code **without overwriting local edits**. Capture a private backup only during an approved transaction.
2. Review CPU/RAM/disk/desktop/microphone/GPU indicators. Anything marked \`unverified\` still needs a real hardware test.
3. With explicit owner action, test live microphone/hearing, Cory and Shayna authorization, other speakers/TV rejection, STOP, wake/sleep, and Webbie's speaking/listening loop. A matching source hash and 0.88 model threshold do not prove speaker security. The offline biometric provider is not included.
4. Verify Kali Bay's actual local runtime and only authorized tool operation, Studio audio and export workflow, Author/Study data continuity, Forage indexes, and actual Nova/BCN broadcast operation without disruption.
5. Demonstrate full combined backup and rollback on a separate test fixture, then reconcile genuine live-PC state, review daily install slot, and request **explicit owner approval** for the one supported installation. Don't use synthetic GitHub test receipts as physical PC proof.

## Read-only automated tests

~~~bash
python3 -m unittest discover -s tests -p 'test_spider_pc_readiness.py' -v
python3 -m unittest discover -s tests -p 'test_daily_pc_acceptance.py' -v
python3 -m unittest discover -s tests -p 'test_*.py'
~~~

Run these on the candidate checkout or GitHub CI, not by modifying the installed application directory. This branch provides the source and safe audit instruments; **real installed-file reconciliation cannot be asserted until its output from the owner's actual machine is reviewed.**
