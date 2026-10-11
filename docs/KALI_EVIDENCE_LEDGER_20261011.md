# Kali Bay: Evidence Ledger and Chain Integrity
Date: October 11, 2026
Branch: `upgrades/kali-bay-evidence-ledger-20261011`
Depends on the Kali Bay source-only workflow upgrade in PR #65, which itself depends on PR #60.

## Delivered in source
- **EVIDENCE LEDGER**, the sixth native Kali Bay tab, lets the owner register a previously user-selected SHA-256 fingerprint to the active lab, then explicitly record review, transfer, verification or note events.
- Each event includes a UTC timestamp, event kind, filename (not original absolute path), size, digest, original fingerprint time, an owner-authored description, event sequence and chained SHA-256 integrity checksum. The latest checksum links back through the saved record history.
- The ledger is saved only on the host under the logged-in user's private `~/.local/share/spider-os/kali-bay/projects/` folder. The user must confirm each event. No Webbie submission, automatic scanner, file execution, package install, new service, network request, container change or cloud sync is introduced.
- Writes are serialized with a Linux advisory file lock and a separate stable lockfile; ledger updates are private atomic replacements. Files use 0600 permissions. Linked destinations and lock files are rejected; records and notes are bounded.
- **VERIFY LOCAL CHAIN** checks every stored event against the local hash chain and reports missing/corrupt entries. Report export now includes the verified local chain summary. Corrupted ledger state blocks export rather than falsely implying trustworthy records.
- The guarded Kali-only installer source manifest includes `kali-bay/runtime/evidence_ledger.py`. Existing tab/regression checks now include six tabs.

## Meaning of chain verification
This is **tamper-evident locally**, not tamper-proof. Someone with full control of the PC can recalculate hashes or replace the entire file. A validated hash chain does not prove that the evidence was legitimately acquired, that the named custodian handled it, that a clock was correct, or that a sample is safe. For evidentiary use outside your own lab, follow organizational custody policies and independent signing/storage requirements.

## Regression and release checks
```bash
python3 -m py_compile kali-bay/runtime/evidence_ledger.py kali-bay/ui/kali_bay.py kali-bay/runtime/lab_reports.py
bash -n kali-bay/package/install-kali-bay.sh
python3 -m unittest discover -s tests -p 'test_kali_evidence_ledger.py' -v
python3 -m unittest discover -s tests -p 'test_*.py'
bash kali-bay/package/install-kali-bay.sh --check
```

**Draft source only. Do not install on the owner's Spider OS machine yet.** The actual on-PC Kali UI is customized and differs from GitHub; perform the guarded source audit, avoid overwriting unfamiliar changes, and integrate the entire branch chain with the combined daily installer and rollback plan. GitHub source checks cannot prove PC desktop/KDE, Distrobox container or audio/Webbie behavior.

## One-batch installation continuity audit
The upgrade also adds `kali-bay/package/audit-upgrade.py`, an entirely read-only on-PC source audit. It checks the Kali manager, Kali UI, five bundled runtime modules and Webbie's dedicated Kali assistant bridge against the GitHub source, reporting the SHA-256 of existing matching/diverging source files. Existing owner-modified files are **blocked**, not replaced, and missing core Kali files are blocked. Missing new runtime components are identified as additive candidates, but no installation takes place.

Preview on the PC **only when the full source is downloaded**:
```bash
python3 kali-bay/package/audit-upgrade.py
python3 kali-bay/package/audit-upgrade.py --json
```
The selective `--install` path now runs this same continuity gate before any backups or writes. If any existing Kali/Webbie source differs, it refuses changes and requires human reconciliation through the daily combined-release workflow. Passing this comparison does not itself authorize installation or guarantee hardware compatibility. The full combined installer still needs to be updated and tested separately to include this branch.

Test: `python3 -m unittest discover -s tests -p 'test_kali_upgrade_audit.py' -v`.
