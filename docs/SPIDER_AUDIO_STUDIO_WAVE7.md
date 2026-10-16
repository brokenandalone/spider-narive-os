# Spider Audio Studio Wave 7: Virtual Band → Backing → Record

## What is now implemented as real source

Both actual music-making workspaces can now create a backing track for the
**same native Record Audio · Multitrack** bay, without exporting and reimporting
WAV files manually.

**Auto Performer → Record Along With Spider:** Import MusicXML/MXL, MIDI,
chords or text TAB. Adjust note events and instrument patches in the existing
Performance Note Editor, and set individual instrument SoundFont banks,
mixer gain/pan/mute/solo, expressive groove, energy and guitar strum spread.
Click **Render Virtual Band Backing → Record Along With Spider**. A background
Qt worker takes a stable snapshot of the expressive symbolic notes and their
existing mixer settings, renders the real per-part local SoundFonts using
the existing FluidSynth multi-bank mixer to a **16-bit PCM, 44.1 or 48 kHz
stereo backing WAV**, and atomically publishes a new private cue.

**Song Arranger → Record Along With Spider:** Capture a drum/guitar/bass/keys
pattern from the existing native virtual instruments. Arrange bars and set
track levels and panning. Click **Backing to Audio Recorder**. A worker takes
a validated song snapshot and calls the real existing synthesizer/song-mix
engine. The output is a fresh private stereo 16-bit 44.1 kHz cue.

**Shared recorder handoff:** Both workflows emit the finished cue path and
sample rate to a new internal Studio handler. The recording console verifies
the file is a local, valid, uncompressed 16-bit mono/stereo WAV, sample rate
44.1/48 kHz, within five minutes and not truncated; it selects the correct
recording sample rate and ensures the max-duration setting covers the cue.
The Studio tab changes to the existing recording console. **No microphone,
headphone/output device, MIDI port or network service is activated** by
rendering or cue selection. The user still presses Refresh Inputs,
selects input/output, uses headphones and explicitly clicks Record Along
With Backing to start full-duplex playback and microphone/instrument capture.

**Private cue storage:** Each render receives a new non-overwriting random
filename inside Documents/Spider Studio/Music/Backing Cues. Rendered content
is held in a protected temporary folder and the finished WAV is published
only after strict validation, with 0600 file permissions. A bad synth output
or a missing/malformed source creates no completed cue. Older recordings,
source scores, licensed SoundFont samples and previous arrangements remain
unchanged. The user may optionally check Include Backing Track in the
recorded multitrack export; this is not done by default to avoid doubling.

If a live recording/export is already running, a newly finished backing is
**not** swapped into that recording. The owner can select the already
rendered backing after finishing the current job.

## Regression coverage
- tests/test_spider_virtual_band_backing.py: true synthesized one-bar
  arranged song, score render with per-part samplebank/volume/pan, private
  multiple cues, malicious/invalid output, missing SoundFont rejection,
  source-content preservation, no-overwrite and symlink directory rejection.
- tests/test_spider_audio_gui.py: internal signal wiring in both directions;
  virtual band selection with no implicit device activity, sample-rate
  configuration and a block on swapping a cue during an active take.
- Existing tests/test_spider_audio_overdub.py: duplex input/output sample
  frame alignment, input preservation and manual latency compensation.

## What still needs validation / implementation

A generated 16-bit backing is not proof of commercially competitive sound.
The owner must choose quality licensed SoundFonts; exported quality and
instrument realism depend on bank quality and the underlying FluidSynth
articulation. The older hand-built Song Arranger oscillator sounds are
**not** pro multisamples. Real hardware playback, round-trip ADC/DAC
latency, input gain, cue spill and recorded singer/guitar quality have NOT
been checked. Wave 7 produces an offline virtual-band WAV first; it does
**not** run autonomous LLM musicians while recording and is not a
real-time VST/LV2 host. No mic permissions or radio routing change.

Remaining: precise count-in and physical latency measurement, timed MIDI
controller recording with acoustic audio playback, punch/loop/take comping,
automation, audio effects and plugin hosting, sampled guitar articulations,
multitrack editing and robust session restore/reopen. Continued development
must remain a draft PR until the owner's locally customized installed source
files are reconciled and protected with backup/rollback.
