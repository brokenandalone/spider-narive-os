# Ubuntu Studio 26.10 final with current native bays

Prepared 2026-10-15. Pending CI results; not approved for installation.

## Evening integration and confirmed blocker

The migration snapshot now includes `feature/native-monster-bays-20261015`
at `1441ca934a2270d86e714007493ff6b662846f18`, preserving its native bay
integration and source-test fixes while keeping the migration base at 26.10.
This does not reconcile or replace the installed PC's 33 locally customized files.

Run 38756210018 passed source tests and the offscreen desktop checks, and
authenticated the final upstream ISO using Ubuntu's signed checksum list.
Its recorded Casper listing contains `minimal.squashfs`,
`minimal.standard.squashfs`, and `minimal.standard.live.squashfs`.
The builder's previous two-layer `standard.*` assumption was incompatible.
The migration fix mounts the base and standard delta as a read-only overlay,
materializes the combined installed filesystem with metadata intact, then
customizes and repacks a standalone `standard.squashfs`. The separate live
delta becomes `standard.live.squashfs`. Installer metadata and GRUB leaf-layer
arguments change together; the default full Studio source keeps its ID and
kernel metadata. Only that customized full source is offered, preserving Studio
applications rather than offering an unmodified upstream minimal installation.
Unrecognized default paths, language layers or source types fail closed.

The captured final catalog selects `ubuntustudio-desktop` at
`minimal.standard.squashfs` (15,256,940,544 installed bytes). The final GRUB
normal and safe-graphics entries omit `layerfs-path`; normalization adds the
explicit `standard.live.squashfs` leaf before the `---` separator. Both actual
upstream menus and the catalog were tested against the normalization helper.
Authenticated upstream ISO SHA256:
`00d1fb881501101b9f7e9fe5b22c5473f6c96fa4bb2b69f9c00e9ee69f537fe7`.

The probe saves the original catalog, normalized catalog, GRUB configuration
and all squashfs superblocks. A synthetic mounted-image test checks base files,
overrides, deletions, hardlinks and symlinks before the real build begins.
No successful 26.10 image build, installation, or boot is claimed yet.

The integrated feature snapshot passed 1,056 unit tests. The new coverage
auditor initially rejected the migration because it required the 26.04 pin;
its explicit `--target 26.10` mode now checks the release, codename, final image
and release channel without weakening the default LTS gate. Source-check run
38825420371 passed, including native UI checks and payload coverage.

Upstream implementation references:
- https://github.com/canonical/curtin/blob/main/curtin/commands/extract.py
  (`_get_image_stack` and `get_handler_for_source` resolve dotted layer names;
  a single-component `standard.squashfs` is a one-image installed stack).
- https://github.com/canonical/subiquity/blob/main/subiquity/models/source.py
  (source ID, variation path and source type determine the install URI).

Source integration:
- migration foundation: 8fb4030b0591c3496529ebfade0021eb60e92b0e
- native bay feature snapshot: 7b9ba3851300db8739bc677c30b2423721431501
- main boot/Nova snapshot: d1bd73ccff3abc6a8f810d74bc2f0ca13b28f3f5

The feature source adds the current native bays, expanded Webbie, Author, Studio, School, Forage, Kali evidence/lab tools and the reviewed in-bay MAX operations. This integration retains main's newer Nova voice module, production controls, tests and service wiring. Nova also retains the feature branch's direct-module import and malformed-JSON handling fixes. Kali retains its newer native UI/Purple sections and the launcher path fix. The builder now packages the vendored MAX source into installed and live images instead of relying on a Downloads ZIP.

The base config selects the official final Ubuntu Studio 26.10 amd64 ISO. Only this migration branch carries the base transition; main is unchanged. All source tests and offscreen native-bay checks run before ISO download/build. The dedicated workflow has read-only repository permissions, verifies signed upstream checksums, checks Casper layers/catalog, builds the image and invokes the existing disposable UEFI install/boot test. It uploads diagnostics and does not publish a release.

Passing this workflow does not validate local/private updates absent from these source commits, real microphone/TTS performance, authorized speaker filtering, interactive Wayland/SDDM, encrypted installation/unlock, Secure Boot or physical hardware. Preserve the working PC and verify rollback before promotion. The existing custom The Web session uses X11; Wayland qualification remains open.
