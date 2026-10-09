# Installed Spider OS audit (read-only)

Use this only on the owner's **existing working Spider OS machine**, from
Konsole in The Web. It does not upgrade, rebuild, reinstall or restart anything.

The scanner asks only whether expected components are present, whether user
services are running, what state the existing Kali container is in, and how
many entries the two known SQLite libraries contain. It scans no arbitrary
user folders, prints no private book titles, lyrics, manuscript text, model
prompts, usernames, hostnames, or account credentials.

It does not query the internet, change Plymouth, edit GRUB, unlock encryption,
run apt, start Kali, install packages, change a database or make backups.

## Run directly from the GitHub source branch

```bash
cd ~/spider-narive-os
git fetch origin upgrades/installed-system-audit
git show FETCH_HEAD:the-web/package/audit-installed.py > /tmp/spider-audit-installed.py
python3 /tmp/spider-audit-installed.py
```

No `sudo`. The report prints presence/absence and safe counts directly into
Konsole. JSON output is available with `--json`; do not share unreviewed JSON
reports publicly as they can include system configuration metadata. The report
is intentionally **not saved by default**.

For a completely offline, file-only check without contacting systemd/Podman:

```bash
python3 /tmp/spider-audit-installed.py --files-only
```

Author's database is opened with SQLite immutable, read-only URI mode. This
cannot create its database or any WAL/SHM sidecars. Counts could lag pending
uncheckpointed edits, so **do not use this report to decide whether to overwrite
a manuscript**. The known import package and owner-original DOCX directory
are only checked for presence/count, never imported.

The report checks configuration hints for the requested Spider OS boot branding
but does not assert that the actual GRUB/Plymouth/SDDM screen looks correct.
The prior power outage and transient failed boot still require a cautious
owner-machine check.

## Follow-up

1. Review the summary. Mark components installed or unconfirmed accordingly.
2. Investigate only genuine failures; don't reinstall things merely because a
   known folder is absent or a stopped container says `exited`.
3. Keep the Kali Bay-only upgrade separate. Its already-applied PR #13 installer
   should not be rerun.
4. Once the combined PR #17 desktop work is qualified, its separate selective
   installer can apply face, window controls, audio and diagnostics **once**,
   with backups and one log out/in.

Source and CI tests do not replace owner-PC testing.
