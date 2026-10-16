# Spider Audio Studio Wave 6: Duplex backing-track overdubs

## Source-stage feature implemented in native Studio

The existing **Record Audio · Multitrack** Qt tab now has a recording mode
labelled **Record Along With Backing**. The owner must explicitly choose:
(1) a regular uncompressed 16-bit PCM backing WAV at 44.1 or 48 kHz;
(2) a recording input from the manually refreshed device list; and
(3) a stereo output device (preferably headphones). Nothing opens a
microphone, speaker, or monitoring port during startup or score import.

The optional `sounddevice` / PortAudio `RawStream` uses a **single full-duplex
callback** for two-channel cue playback and mono/stereo 16-bit input capture.
Each callback queues numbered input frames while it supplies the exact same
frame interval of the cue to the selected output. The queued PCM is written
by a separate worker, never by the PortAudio callback, and its frame offsets
are checked before a finished take can be published. Captured data are kept
separate from the reference cue. The stream does not play microphone input
back into the monitoring output, avoiding feedback by default.

**Cue time zero:** the resulting take starts at the backing file's sample
frame zero and is padded with digital silence to the full backing length,
including if the user stops early. This makes the result directly suitable
for a multitrack timeline with zero-offset alignment. Only the first
five minutes of the cue are permitted; a cue must also fit the user-selected
maximum duration. A separate latency adjustment (-250 to +250 ms) can
advance input (+ms) or delay input (-ms) through integer-sample
drop/pad operations during export. This is an owner-provided estimate, not
an auto-measured interface calibration. The original input samples and
backing cue are never replaced.

The recorded take is written privately (0600) through a bounded temporary
PCM spool and a finished WAV temporary file. Only after successful capture
and format validation is it published to a *new* destination via a
create-new-only same-filesystem hard link. XRUN/overflow, missing frames,
unsupported PCM format, mismatched sample rate, invalid destination,
missing cue, or failure to open an actual duplex audio stream cause a
visible error without publishing a corrupted final recording.

**Backing and mixing:** The owner may opt in to include the backing WAV
as an `instrumental_bed` role in existing Spider Studio multitrack exports.
This option starts unchecked to avoid duplicates. Recorded takes remain
separate individual tracks; an existing session can be mixed inside the
native Session Mix Dialog. The source cue and all previously recorded
takes are protected against overwrite.

## Limits and real-hardware validation gates

A single callback gives an aligned **stream sample-frame reference**,
**not** guaranteed physical acoustic alignment. Output DAC latency,
input ADC latency, buffer delay, audio-interface driver, hardware clocks,
and headphone cue spill affect real recorded timing. The owner must test
and calibrate the chosen hardware for synchronized overdub use. No
automated round-trip latency measurement or count-in guide is built yet.

This mode currently uses **16-bit duplex audio** to support a bounded common
PCM layout. The independent vocal/instrument take mode in Wave 5 supports
real device 24-bit as an option when hardware supports it. The backing
must be 16-bit PCM at the chosen sample rate; resampling, multichannel
cue playback, punch in/out, looping, non-destructive take lanes, plugin
effects and low-latency live input monitoring are not available in this
duplex engine. Use headphones rather than speakers when recording with a
microphone.

The optional PortAudio backend must already be installed and both
selected input/output devices must support a shared full-duplex stream.
Nothing here changes PipeWire, JACK or ALSA defaults, restarts services,
automatically captures private audio, uploads recordings, or controls
Nova/BCN radio or Webbie.

## Automated gates

- `tests/test_spider_audio_overdub.py` exercises fake full-duplex input/
  output at exact sample positions, true cue playback, mono duplication
  to stereo, both manual latency directions, early-stop silence, mismatched
  cue parameters, owner-file overwrite prevention and XRUN cleanup.
- `tests/test_spider_audio_gui.py` checks native Qt startup with no
  device query, inactive overdub buttons and opt-in backing inclusion.
- Existing Wave 5 source and audio capture regression tests remain active.

This is feature-branch source, not an installed or commercially validated
DAW. Previous Spider OS owner-file customizations require safe merge review,
backup and rollback before any deployment. Physical microphone/audio
hardware and listening tests are still required.
