# Spider Audio Studio Wave 9: Recording Calibration, Take Comping, Offline Effects

## GitHub source implementation, inside the existing native Studio

The owner-approved **Record Audio · Multitrack** workspace now includes
three additional production tools, not a separate launcher:

### 1. Explicit physical loopback latency measurement
**Measure Physical Cable Loopback (Experimental)** uses a controlled, low-level
coded test signal sent to the explicitly selected stereo audio output and
recorded from the explicitly selected audio input over a single full-duplex
PortAudio stream. It can measure sample-accurate **combined output→input
round-trip delay** when the owner has connected a proper line-output to
line-input cable. The owner receives a warning and an explicit confirmation
dialog. Speaker-power output connections, phantom-powered mic inputs, or
unsupported interfaces are unsafe; the user must choose compatible line
connections and low output level. No audio device is opened automatically.

Signal correlation checks three separate known code bursts, requires
agreement within three frames and a confidence threshold, rejects absent or
too-quiet signals, and bounds the measured range to 250 milliseconds.
**CRITICAL:** combined round-trip delay does NOT isolate physical ADC input
latency from DAC/output latency; consequently the result is **not**
automatically applied to Spider's manually adjusted input compensation.
The measurement is presented for hardware diagnosis. A truly automatic
input-only setting requires a driver-specific or separate DAC measurement.

### 2. Non-destructive WAV take comping
The in-bay **Comp Two Recorded Takes** dialog chooses two already recorded
takes, a transition point, and optional crossfade of 0–50 ms. Behind this
UI, a reusable edit-decision-list backend can choose from 2–16 recordings
with 1–128 contiguous timeline segments. It validates that all takes have
identical duration, channel count, bit depth and 44.1/48 kHz sample rate.
Crossfades smoothly blend two take recordings at the **same absolute frame
positions**; the song timeline and backing alignment are retained.

Only NEW private 16- or 24-bit WAV files are created. The inputs are
read-only, the output is generated in bounded blocks and atomically
linked into place without overwriting existing files. A cancelled,
overlapping, inconsistent, malformed or truncated set is rejected and
never publishes a finished comp. The new comp can be opened in existing
Spider multitrack editing and mixing. The UI is intentionally a simple
two-take/one-transition editor, not a full Ardour-style take-lane editor.

### 3. User-controlled offline take effects
**Shape Selected Take · EQ / Compression / Room** offers whitelisted
bass/mid/treble EQ adjustments (-12 to +12 dB each), optional 3:1 compression,
subtle reflected-room delay (0–40%), and an output limiter.
Processing uses an installed FFmpeg command-line backend WITHOUT shell
execution or untrusted custom filter text, and saves a new 24-bit PCM WAV.
The original take is never edited. Bounded process time, stop/cancel,
clip duration, stream layout validation and non-overwrite output checks
are included. Processed takes are appended to the existing native
recording take list, ready to comp or mix.

This built-in DSP is not **VST/LV2 plugin hosting**. It is not convolution
reverb, pitch correction, surgical EQ, multiband mastering or commercial
third-party plugin compatibility. Advanced plug-ins, GUIs, latency
compensation and live effects processing require a separately engineered
and licensed host.

## Automated regression tests

- `tests/test_spider_audio_latency_calibration.py`: three-burst real sample
  delay estimation at zero, 137 and 1024 frames, fake full-duplex device
  capturing the physical loopback pattern, no-signal rejection, and
  preflight safety before hardware opens.
- `tests/test_spider_take_comp.py`: 16-bit crossfaded two-take transitions,
  genuine 24-bit multichannel multi-region comp output, zero crossfade,
  exact timeline length, invalid and overlapping segments, duplicate WAV,
  cancellation, source byte preservation and existing file protection.
- `tests/test_spider_take_effects.py`: validated fixed filter chain,
  untrusted input rejection, optional installed FFmpeg test producing a
  genuinely processed and verified 24-bit WAV.
- `tests/test_spider_audio_gui.py`: native controls, privacy and
  permission-preserving UI behavior with no automatic device access.
- Previous count-in, punch, virtual band, score, MIDI, real WAV and session
  tests remain active.

## Boundaries that must not be hidden

This entire round is **GitHub development source**, not an installed,
real-hardware-tested release. The microphone, interface hardware, speakers
and cables on the owner's PC were NOT used or calibrated through GitHub
CI; synthetic test fixtures do not certify physical fidelity or safety.
Actual device qualification requires a deliberate owner-initiated local
loopback and real monitored recording. Neither an audio-interface selection
nor an existing music library or SoundFont bank licenses high-end commercial
content for bundling. Real guitar plucks, bass articulations, drum round-robin,
cabinet/mic sampling, and access to proper licensed libraries still need
professional acoustic/sound-design work.

The PR remains in **draft**. Roughly 31 previously observed locally
modified Spider OS source paths still require drift reconciliation before
any owner-approved installer can apply updates with backup and rollback.
Nova/BCN, Webbie, other bays and all user music files remain untouched by
branch-only development.
