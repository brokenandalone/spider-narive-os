# Webbie JARVIS Standing Owner Authorization
October 11, 2026 · Source-only draft · NOT INSTALLED

## Owner intent

Webbie should be the standing assistant across Spider OS, without a
30-minute limit or constant repeat approvals. When the owner asks her
to work in an app, open a public website, inspect system status,
help through Konsole, or open a Kali Bay GUI program, she should do so
within the capabilities of the actual installed adapters. STOP must work
even when The Web GUI is closed. A language model's statement or
website/terminal text is never sufficient to issue an owner command.

## Permanent access with no action-count expiration

An explicit native-owner GUI click writes a tiny permission preference to
~/.config/spider-os/private/webbie-owner-authorization.json, in an
owner-private 0700 directory with 0600 atomic file creation, valid schema,
symlink prevention, and invalid/corrupt data fail-closed.

The owner approval is not a password or API token. It is a *persisted local
policy*. No secrets, transcripts or model text are saved there.

* AUTHORIZE: permanently enables approved app and on-demand Kali GUI launch.
* RESTORE: The Web recreates the active operator after login when the saved
  preference is authorized and not paused. No program or camera starts simply
  because the preference is restored. Ordinary approved actions have no
  timer and no request budget.
* PAUSE / STOP: immediately cancels the live session and saves paused=true.
  The resident Webbie agent itself writes PAUSE when it hears a strict STOP,
  so this works even without an open Qt panel. Restart cannot undo STOP.
* RESUME: one deliberate owner click restores existing saved consent.
* REMOVE: explicitly revoke permanent authorization and the live grant.
* Closing and later reopening The Web does not erase owner authorization.
* Sleeping cancels active computer control, not the owner's saved policy.

The "permanent" policy is only an owner-approved right to use permitted
capabilities; it is not persistent administrator/root privilege.

## What works in source after this upgrade

1. **Routine desktop apps**: Any already installed, catalog-confirmed
   eligible application may be opened on direct owner request. Risky
   terminal/admin/password/security settings apps aren't silently launched
   through the general app opener; Konsole and Kali have their own adapters.
2. **Websites**: Directly requested public HTTPS addresses and searches
   can open through the existing operating-system browser without a fresh
   approval popup. Private network, local, insecure or malformed addresses
   are disallowed through this particular route. This does not log in,
   submit forms, change websites, host anything, or verify page loading.
3. **Konsole**: A direct owner request can launch Konsole. Exact read-only
   console diagnostic phrases can query kernel, uptime, memory, disk
   capacity, and known user-service status using fixed shell-free argv.
   Webbie can display bounded results in the native chat, asynchronously
   in Qt, and speak the status when genuine trusted voice is available.
   This is NOT arbitrary terminal execution or interactive PTY automation.
4. **Kali Bay**: From owner-verified commands such as "open Kali app Ghidra",
   Webbie can query the running Kali Distrobox's installed desktop entries,
   require an exact unambiguous app name, preflight the installed ID, and
   request the GUI launch using the existing Kali Bay manager. Featured
   Kali workbenches remain. This does not start scans, network attacks,
   exploits, dynamic tool parameters, or privileged commands.
5. **Local services**: Existing read-only Webbie, Nova and OneDrive local
   status remain available. Proactive read-only checks remain separate.
6. **Safety**: User text/verified speaker input, not LLM output, webpages,
   workspace titles, terminal output or camera observations, can request
   app/Kali/console/website operations. Risky functions remain blocked in
   the wide policy.

## Capabilities NOT yet completed

The user's broader JARVIS objective is **not** yet fully implemented:
* Deploy, host, administer, update or publish websites through a connected
  hosting provider;
* Use GitHub/hosting/API service credentials or edit remote sites;
* Search all local documents and private project files by a controlled
  owner-scoped index;
* Edit arbitrary application GUI fields, save files, send messages or
  upload documents without a compatible audited application adapter;
* Run unrestricted shell commands or autonomously install system upgrades;
* Execute every Kali CLI utility/active security operation without target
  scoping and authorization;
* Confirm the true visual result after any command, or run a continuously
  autonomous, general-purpose agent across all OS programs.

These require actual linked adapters, resource boundaries, explicit
authorized-target scopes, action receipts and rollback. Do not claim that
the presence of a permission file implements these tasks.

## Test / deployment gate

New tests cover persisted source policies, no expiry/budget, safe directory
modes, STOP/restart/revoke, ordinary website access, console diagnostics,
Kali installed-app preflight, rejection of arbitrary commands and old
desktop/voice/academic/media release regressions.

The draft stacks on PR #95, #90, #88, #78, #76 and earlier branches.
**Do not install the stack unchanged**: the strict Cory/Shayna voice
verifier isn't actually enrolled and proven on the owner's customized PC.
That earlier gate would otherwise stop normal Webbie speech. Perform
hash-by-hash reconciliation, live hardware tests, source compatibility
verification and a single reversible coordinated release.

This source development does not change the owner's actual computer,
GitHub default branch, personal documents or connected accounts.
