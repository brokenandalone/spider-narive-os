# Kali Bay Command Center major source upgrade
Date: 2026-10-11
Branch: upgrades/kali-bay-command-center-20261011
Parent: PR #50 (Kali Bay readability/readiness) -> PR #46 (real installed Kali apps)

## What is built
- Full native Kali Bay graphical launch hub with Offensive Security and Kali Purple tabs remains in place. New **LAB NOTES** tab supports named authorized-lab notebooks, handwritten investigation notes and next steps.
- Local notes are stored separately in the logged-in user's ~/.local/share/spider-os/kali-bay/projects using restrictive permissions (0700 directory, 0600 files) and atomic replace. No automatic cloud upload or LLM submission, no scan execution, and no Kali container changes.
- Favorite installed desktop tools and approved featured tool IDs can be explicitly saved and filtered in Kali Bay. Favorites survive app restarts and reject non-allowlisted builtin IDs / malformed dynamic IDs.
- Improved tool descriptions, Ctrl+F to jump to application search, dark/purple contrast, and a read-only environment readiness widget.
- Webbie's Kali-specific explicit command bridge gains read-only **check Kali Bay readiness** and explanations for the original ten approved tools. Never executes synthesized commands.
- Kali's category workbench now rejects unknown metapackages and suspicious labels *before* opening Podman, Distrobox, Konsole or the Kali container. Approved category labels are positional arguments to a static shell script, not interpolated into program text. The existing stopped-container guard is enforced here too.
- Updates the selective Kali installer to recognize and syntax-check the new local storage module; module installation on a reviewed release requires writing its new runtime file.
- Offscreen Qt, mocked-container and persistence/security regression tests included.

## Privacy and reliability
An explicit **SAVE LOCAL NOTES** button is required. Switching away from unsaved notes asks to discard changes. Revision checks reject overwriting a previously updated notebook. **PREPARE NOTES FOR WEBBIE** shows a confirmation and only fills Webbie's chat input. The user must review and explicitly click **SEND TO WEBBIE**, because the configured assistant may use a remote model. Never send secrets, real target information, or private identifiers without deciding to share them.

The existing resident Webbie socket is reused. No second AI service, camera, listener, or new speaker authentication method is introduced. Existing voice authorization checks stay in place. **Do not claim owner/partner speaker verification works on the installed PC until tested.**

Distrobox is the real Kali userspace on the Spider OS host kernel, not a hard-isolated Kali VM or separate Linux boot. Kali Purple services are not automatically deployed by this change.

## Source validation
~~~
bash -n kali-bay/bin/kali-bay
bash -n kali-bay/package/install-kali-bay.sh
python3 -m py_compile kali-bay/ui/kali_bay.py kali-bay/runtime/workspace_store.py webbie/agent/kali_assistant.py
python3 -m unittest discover -s tests -p 'test_kali*.py' -v
python3 -m unittest discover -s tests -p 'test_webbie_kali_assistant.py' -v
bash kali-bay/package/install-kali-bay.sh --check
~~~

## Deployment restrictions
**SOURCE ONLY. NOT INSTALLED OR MERGED.**
- Do not overwrite the customized Kali UI or any of the other PC-updated scripts without inspecting the current copy and preserving backups.
- PR #51 is stacked on PR #50, which is stacked on PR #46, not on main. Full release integration and install manifests in the evolving combined release PR #49 must be reconciled first, including the new workspace_store.py source path.
- Run the GitHub source checks and the full owner-PC source audit and tests, not only an isolated targeted installer.
- Only after verified backups and release gating should the owner consider installing.
- On PC test: menu visibility, app category filtering, real Kali app launching, saved favorites after relaunch, multiple lab notes, revision conflict and missing-file behavior, desktop screen sizes, QShortcut focus, stopped-container safety, Webbie socket privacy and voice gates.
- No apt install, Kali image pull, VM provisioning, root host changes or security scans happen from this upgrade.

## Intended next steps
After deployment gates: async Kali app catalog refresh without freezing UI, locally sourced security tool documentation and sanitized evidence import, desktop/window inspection with explicit Webbie permissions, read-only Kali Purple sensor dashboard (no autostart), device-by-device testing and rollback.


## Kali Purple defensive inventory expansion
The same source branch now adds `kali-bay purple-json`, a non-mutating inventory of **nine** familiar Kali Purple/security command binaries: Suricata, Zeek, YARA, Lynis, ClamAV's clamscan, Wireshark, tcpdump, tshark and auditctl. It returns bounded JSON reflecting the existing running Kali container. Missing or stopped containers return a status without a start attempt. The JSON command does not even initialize the user state directory.

The native **PURPLE DEFENSE** tab has a **CHECK PURPLE DEFENSE TOOLS (READ ONLY)** control with installed/not-detected display. Webbie also understands **check Kali Purple tools** as a fixed read-only request. **Binary presence is not equivalent to a configured, active detection service**, and no SOC sensor or service is automatically started.

Extra tests:
~~~
python3 -m unittest discover -s tests -p 'test_kali_purple_inventory.py' -v
~~~
