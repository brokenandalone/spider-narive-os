# Spider Audio Studio | Commercialization and beta release plan

**Status: owner-testing beta 0.15, NOT CLEARED FOR PUBLIC SALE.**
The program is to turn a proven native Linux music-making workflow into a
credible product without risking users' recordings or violating third-party
licenses. The app already runs on the owner's Ubuntu Studio workstation; that
single successful launch is valuable, but not multi-device qualification.

## Product positioning

**Category:** Linux desktop music creation / songwriting and WAV production.

**Proposed promise:** "Bring a guitar riff, vocal or instrumental idea into a
single native workspace, arrange real recorded phrases and deliver a stereo
mix, while retaining all original audio."

**Initial ideal users:** Independent guitarists, singer-songwriters, rock
bands and home recording musicians with local files who want a guided,
non-destructive arrangement/mixing workflow on Ubuntu Studio.

**Do not market as:** a full plugin-compatible professional DAW replacement;
an Ableton, Cubase, REAPER, Bitwig, or Ardour feature match; guaranteed
low-latency live recording across every USB interface; realistic licensed
guitar instruments bundled; AI voice models that recreate individuals.

## Two rights-compliant routes, requiring an owner decision

1. **GPL-compatible/open-source program with paid services/support:**
   have qualified counsel review GPL compatibility across this MIT repo,
   PyQt5, bundled or installed Qt libraries, optional FFmpeg versions,
   redistribution, source delivery and notices. Selling GPL-licensed
   software is possible, but recipients have GPL redistribution rights.
2. **Proprietary/commercially licensed product:**
   secure and document appropriate commercial PyQt rights before closed-source
   distribution. Review Qt LGPL obligations or obtain the appropriate Qt
   commercial rights. Still clear FFmpeg and all other dependencies. Avoid
   assumptions that a copied MIT notice covers a Qt/PyQt binary.

Official licensing background:
https://en.riverbankcomputing.com/commercial/license-faq
https://www.qt.io/development/open-source-lgpl-obligations
https://ffmpeg.org/legal.html

**No change to the repository LICENSE or any sale launch is authorized by
this plan.** Legal advice and owner sign-off remain required.

## Practical product acceptance standards

**Installation:** A user with a supported Linux desktop can open a package,
inspect third-party notices, run one simple per-user installer without sudo,
see a versioned launcher, open the original Studio, and diagnose missing
dependencies. Upgrade must not delete or overwrite older beta builds.

**Core workflow:** Select 4 independent guitar WAV tracks, choose roles,
create a private verified session, adjust controls, export 48 kHz 24-bit
stereo WAV, play from the in-app transport, and reopen its edit decisions.
Test mono/stereo, 16/24-bit source, invalid files, long durations and
import cancellation. Verify all original source file hashes untouched.

**Recording quality:** Test capture, instrument monitoring, overdub,
multi-region editing, count-in and output timing on actual named
USB/ALSA/PipeWire interfaces. Record device, sample rate, buffer, latency,
clock drift, dropout rate and OS for every acceptance test. Without this,
do not claim "low-latency pro recording."

**Safety:** No automatic mic activation, no silent cloud transfer, no
model downloads without consent, no replacing prior song exports, symlink
bypass or executable filter injection. Versioned private installer and
uninstall behavior must preserve all user media.

**Documentation:** Accurate installation, first project, troubleshooting,
support expectations, limitations, privacy/voice rights, crash diagnostics,
accessibility and upgrade instructions. Provide an actual human support
channel before charging customers.

**Licenses/assets:** An audited inventory of exact version and rights for
every distributed dependency, artwork, icon, font, soundbank, plugin,
generated/model asset and bundled media, including patent/codec questions.

**Distribution:** Reproducible packaged archives, immutable checksums,
independently verified builds, signed hashes/releases, release notes, a
working update path, and a human owner public-launch approval.

## Initial acquisition plan (no advertising or payment activated)

Pilot with 10-20 opt-in Ubuntu Studio musicians using their own recordings.
Measure successful installs, time to import 4 tracks, successful WAV render,
session recovery, playback backend failures, crash rate, support burden and
real audio-interface failures. Prioritize blockers from recordings rather
than cosmetic request lists.

After pilot, owner chooses open-source-paid-support versus licensed-proprietary
business model and price. We can test willingness to pay only after software
and compliance are ready. Do not advertise specific prices, dates, performance
figures, supported OS versions or commercial plugin compatibility prematurely.

## Engineering changes in 0.15 beta

- Original native Studio packaged with a distinct 0.15 beta identifier.
- `install_for_user.py --check` / `--install`: no-sudo versioned local
  desktop installation, refusing existing installation or desktop entry.
- `run_spider_audio_studio.py --doctor`: readonly dependency report.
- Exact product disclosures: `BETA_README.md`,
  `THIRD_PARTY_NOTICE.md`, repository MIT `LICENSE`.
- `studio/package/commercial_release_gate.py --assert-blocked`:
  explicit commercial-release blockers with owner/legal/hardware checks,
  automatically exercised by beta CI. No automated public payment or
  distribution occurs.
- `studio/product/site/index.html`: responsive, accessible and truthful
  product-page **preview only**, not a deployed or published website.
- `tests/test_spider_audio_beta_market.py`: package, installer,
  no-overwrite, tamper, license warning, doctor and gate tests.

### Go / No-go
**NO-GO for charging users or announcing a commercial release** until:
human-reviewed licenses and content rights, real hardware/device acceptance,
support/privacy/refund policies, safety verification, legal review and
explicit owner sign-off are all documented.

The software is moving toward marketability; current status is a useful
beta candidate rather than a certified commercial product.

## Wave 15 reliability improvements (October 16, 2026)

- New actionable first-run **Start a Song** screen inside the original Studio.
- Installer now stages an entire version under a private temporary folder,
  verifies the copied runtime, then publishes the versioned desktop entry.
  On a copy failure, its own staging folder and shortcut are cleaned so the
  same beta can be retried without touching existing versions or songs.
- Beta archive cryptographically verifies top-level setup scripts and its
  third-party licensing notices alongside actual Studio source modules.
- Offline **Test music engine** runs in a nonblocking GUI process and is
  available as `run_spider_audio_studio.py --self-test`. It generates temporary
  guitars and bass, uses the real importer, per-track EQ and compression,
  two-region timeline, actual installed FFmpeg renderer, PCM WAV output and
  original-file hash checks. No live audio device is opened.
- Previously, unverified FFmpeg graph syntax could pass unit tests because
  the runner had no FFmpeg. The real test exposed and corrected a leading
  comma after source-pad labels. The beta workflow now installs FFmpeg on
  its disposable runner and **requires** a successful real stereo render.
- Wave 15 is still a private beta, not a sealed public commercial product.
  PyQt/Qt/FFmpeg licensing, instrument rights, live hardware acceptance,
  business terms, support and explicit owner approval remain pending.
