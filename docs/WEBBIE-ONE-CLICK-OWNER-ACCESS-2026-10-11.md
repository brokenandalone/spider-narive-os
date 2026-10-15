# Webbie Owner Authorization Center | One-Click Safe Access
October 11, 2026 | Draft source only, NOT installed

The owner requested ONE CLICK to authorize Webbie to operate ordinary installed apps and eligible connected services without repeated routine-action permission dialogs, while preserving all established prohibitions.

## Preserved access boundaries

Open capabilities are routine; contextual operations must still target the intended app/window; confirm actions (deletions, installations, high-impact edits, publishing, live broadcasts, system/service changes, Git pushes) cannot silently execute. Elevated/root, firewall/disks/security changes require exceptional privilege and are not supported by this one-click mode. Restricted offensive Kali/destructive operations and security bypass are never granted. Voice authorization remains Cory/Shayna only after true local enrollment, not transcript or face guesses. Offline-first operation remains. OneDrive stays optional for selected backups/memories, not offloading Spider OS. STOP works universally.

## Owner click and expiry

The Web exposes "One click: Allow Webbie safe access" and "Revoke access now". One owner click creates a process-local, nonpersistent 30-minute grant with a maximum of 240 routine actions. A snapshot of existing XDG desktop IDs is limited to ordinary eligible apps. Excluded by conservative category checks: terminals, root/admin utilities, password managers, disk tools, system settings, firewall tools, offensive Kali tools and remote shells. It does not mean all executable commands are trusted.

While the session is active, Webbie can open different eligible installed apps from a direct typed command or verified owner voice through its existing restricted local OPEN socket command. App opening does not require repeated consent. Existing selected-window observation/focus and benign navigation operations reuse the same grant. STOP, sleep, shutdown, expiration, budget exhaustion, and manual revoke end the session. App launches are REQUESTED, never reported as proof the GUI successfully loaded.

The one-click session DENIES raw shell, sudo, installs, unrestricted clicks or typing, delete/cut/save, window closing, browser external navigation, user account changes, sending email/messages, payments, new uploads, Nova broadcasts, Git pushes, security modifications and offensive Kali operations. A broad permission is never interpreted as model permission to invent new tools.

**Why arbitrary clicks cannot be blindly authorized:** The same click could select text, transfer money, send an email or delete a file depending on the app state. The one-click mode cannot guarantee prevention of forbidden acts if it also permits unrestricted mouse/keyboard actions. Dedicated audited task adapters are needed for safe deeper control.

## Service integration scope

The initial audited one-click service adapters offer repeated read-only LOCAL status for Webbie, Nova on fixed loopback health endpoint 127.0.0.1:9876/health, and OneDrive local configuration. No radio commands, account sign-in, remote cloud data read, sync, uploads, or stored secrets. No new account/token is connected. Future external providers need their own preexisting account authentication, explicit adapter implementation and action classifications. Connecting to everything is not achieved by this code alone.

## Main source changes

- webbie/actions/owner_safe_access.py: short-lived one-click grants and deny rules.
- webbie/actions/task_grants.py: integration with legacy task grants; original manual approvals unaffected.
- webbie/actions/safe_service_status.py: local read-only service status.
- the-web/shell/webbie_computer_panel.py: enable, stop, safer app selection, local service status and routine command handling.
- the-web/shell/webbie_operator_bridge.py: broad mode accepts only filtered local app OPEN requests.
- the-web/shell/webbie_panel.py: one-click button and direct typed routine app launch.
- tests/test_webbie_owner_safe_access.py, tests/test_webbie_one_click_grants.py, tests/test_webbie_safe_service_status.py and tests/test_webbie_one_click_access_gui.py.
- guarded combined source manifest and source audit.

## PC release hold

Run the full source test suite, reconcile all installed customized Spider OS code/hash differences and preserve current working Webbie TTS, microphones, models, Studio, Author, Study, Forage, Kali Bay, Nova and Media Center. Stacked earlier PR #76 onward currently includes a strict speaker-verification gate with no validated Cory/Shayna offline provider; installing as-is would block normal speech. Perform ONE owner-approved reversible combined installation only after PC-specific preflight and rollback drills. Source CI cannot establish live hardware/control success.

No actual PC app, service, personal files or account permissions were changed by this GitHub source development.
