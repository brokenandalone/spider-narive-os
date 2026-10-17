# PC repair reconciliation

Comparison: October 9 late evening Indiana time (October 10 UTC). Evidence: supplied installed-agent snapshot and installed-to-download diffs. These are historical snapshots, not live PC access. Repository base: PR #29 `d41e4b731a1c4340e6033053cd4146e2707575bc`, based on frozen combined release `7f2de4c`.

**Owner is actively fixing Webbie on the PC. Final working files from that repair supersede these snapshots. Do not implement a competing voice replacement.**

| Area | Observed mismatch | Action/status |
| --- | --- | --- |
| Memory | Downloaded brain removes history, SQLite memory, saved research lookup and bounded non-thinking model requests present in PC diff. | Restored code paths with new configured model/bay names; focused tests pass. Current PC data/permissions unverified. |
| Multi-turn | Installed snapshot has follow-up/end handling absent from repository; snapshot references CONVERSATION_WINDOW_SECONDS without defining it. | Use final PC repair outcome. Snapshot alone does not prove the current runtime cause. |
| Interruption | Installed agent imports stop_speaking and passes on_interrupt; repository TTS/listener expose neither, and listener skips capture during speech. | Reconcile all companions together. Copying the agent alone would introduce dependency failures. |
| Echo/proactive speech | PC snapshot contains recent-TTS rejection and restricted proactive reply handling missing in repository. | Preserve during final voice port; authorization is separate. |
| Browser/media/research | PC snapshot has verified launches, Firefox focus/environment repair, live Forage and persistent research queue missing in repository agent. | Port final working versions with behavior tests. |
| Sleep | Older PC snapshot wakes at 10 AM; newer requirement is visible quiet sleep until explicit wake, with jobs running. | Do not restore old timed wake wholesale; preserve desired end phrases. |
| Camera | PR #29 contains capture/model repairs; user subsequently confirms Webbie camera works. | Preserve changes, compare final hashes/settings. |
| Author | Owner confirms import and opening entries work. | Import accepted at that scope; backup/count/restore separate. |
| Deep Forage | User report has placeholder references and empty Sources; source synthesizes even with no evidence. | Added no-evidence guard, numeric-citation/placeholder checks, snippet labeling. Mocked tests pass; real provider pending. |
| Installer | Blocks unknown local changes; combined manifest currently excludes forage/engine.py. | Preserve blocking; compare installed engine before adding it to next transaction. |

No private history, memory DB, voice samples or manuscripts are included. Reconstruction uses code only. Mocked tests do not prove on-device voice, authorization, latency or camera behavior.

After the PC repair completes, compare its current agent, TTS, whisper listener, applicable voice-gate modules, non-secret configuration and service errors. Do not replace customized files with generic source just to pass installation.
