# Ubuntu Studio 26.10 final with current native bays

Prepared 2026-10-15. Pending CI results; not approved for installation.

Source integration:
- migration foundation: 8fb4030b0591c3496529ebfade0021eb60e92b0e
- native bay feature snapshot: 7b9ba3851300db8739bc677c30b2423721431501
- main boot/Nova snapshot: d1bd73ccff3abc6a8f810d74bc2f0ca13b28f3f5

The feature source adds the current native bays, expanded Webbie, Author, Studio, School, Forage, Kali evidence/lab tools and the reviewed in-bay MAX operations. This integration retains main's newer Nova voice module, production controls, tests and service wiring. Nova also retains the feature branch's direct-module import and malformed-JSON handling fixes. Kali retains its newer native UI/Purple sections and the launcher path fix. The builder now packages the vendored MAX source into installed and live images instead of relying on a Downloads ZIP.

The base config selects the official final Ubuntu Studio 26.10 amd64 ISO. Only this migration branch carries the base transition; main is unchanged. All source tests and offscreen native-bay checks run before ISO download/build. The dedicated workflow has read-only repository permissions, verifies signed upstream checksums, checks Casper layers/catalog, builds the image and invokes the existing disposable UEFI install/boot test. It uploads diagnostics and does not publish a release.

Passing this workflow does not validate local/private updates absent from these source commits, real microphone/TTS performance, authorized speaker filtering, interactive Wayland/SDDM, encrypted installation/unlock, Secure Boot or physical hardware. Preserve the working PC and verify rollback before promotion. The existing custom The Web session uses X11; Wayland qualification remains open.
