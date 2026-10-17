# Spider OS upgrade priorities

The authoritative grouped checklist is [MASTER-UPGRADE-CHECKLIST.md](MASTER-UPGRADE-CHECKLIST.md).

Build the related desktop changes together and install once, then log out/in once.

Order: boot/data protection; The Web desktop essentials; Webbie; Author; Media; System/Recovery/Guardian/Vault; Kali; Studio; Study; Forage/Deep Forage; Art/Communications; startup branding; platform; release engineering; one coordinated acceptance pass.

The combined source build adds Webbie face/lips/chat, window close/minimize/maximize, a taskbar Audio entry with volume/mute, native MPRIS client controls, dark diagnostic tables/menus, managed build receipts, health findings and JSON report export. Notifications/tray and full system-wide theme switching remain outstanding.

Validation: 103 Python regressions and native Qt integration across 15 tabs passed, including selected-player transport, audio commands, window actions and responsive chat. AF_UNIX, MPRIS and KWin transport are mocked in the test runner; owner-PC qualification remains pending.
