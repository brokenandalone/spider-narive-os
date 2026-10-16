# Spider Audio Studio: Wave 5 / Owner-Controlled Audio Capture

## Implemented as real native Studio code

A **Record Audio · Multitrack** tab is embedded inside the actual Spider
Audio Studio Qt window. It is not an external launcher and does not replace
the existing Studio instrument, songwriting, MIDI and mixing bays.

- **No automatic microphone use:** the tab does not enumerate or open inputs
  during construction. The owner clicks **Refresh Inputs** to query available
  recording hardware, explicitly chooses the specific input and clicks
  **Record New WAV Take** to open an input stream. Recording is stopped
  with **Stop and Save Take** or the bounded time limit.
- **Actual raw input:** the capture worker uses the optional Python
  `sounddevice`/PortAudio `RawInputStream`, with an explicit input index,
  mono or stereo, 44.1 or 48 kHz, and native **16-bit or 24-bit signed PCM**.
  At 24-bit, bytes are obtained directly from the device using PortAudio
  `int24`, rather than artificially increasing 16-bit WAV bit depth.
- **Latency and monitoring:** callback uses a bounded 96-buffer queue, and
  the worker drains chunks to disk. The UI displays measured peak and RMS
  sample levels without connecting audio output or creating microphone
  monitor feedback. Actual low-latency performance is not claimed; device
  driver, sound server, sample mode and buffering determine capture latency.
- **Safe files:** private 0600 output, within the local
  `~/Documents/Spider Studio/Music/Recorded Takes` folder by default,
  distinct WAV files for successive takes; atomic create-new-only hard link
  prevents overwriting a pre-existing take. Temporary partial recordings
  are discarded on failures, input overruns and queue overflow.
- **Multitrack workflow:** record vocals, backing vocals, guitar, bass,
  drums, keyboards and miscellaneous independent instruments on separate
  passes. The take list groups their local WAV files. The owner can hand
  takes to the **existing Spider Studio Multitrack Editor**, or trigger a
  non-destructive export using the existing `studio/multitrack.py` engine
  to assemble an inspectable DAW-style session folder with recorded WAVs.
- **Safety bounds:** no more than five minutes per take, with bounded
  callback queue and 44.1/48 kHz only. A new record press cannot
  interrupt or overwrite an active recording. Studio attempts to stop an
  active recording safely before allowing the main window to close.
- **Dependencies are optional:** no pip installs, downloads, model runs,
  service restarts or audio-device activation during GitHub development.
  `sounddevice` and PortAudio plus a compatible hardware input must be
  available on the owner PC before this can capture sound.

## Explicit limitations

- **This is not yet a low-latency overdub engine.** Consecutive takes are
  separate real recordings, not time-locked overdubs; opening a new stream
  can have variable startup latency. Existing Spider multitrack handoff
  places files at time zero and must be manually aligned/listened to.
  It currently has no automatic headphone cue/click playback synchronized
  with capture; pass-to-pass phase/tempo synchronization is not proven.
- Dedicated PipeWire/JACK/ALSA low-latency routing with clock-synchronized
  backing playback, punch-in, loop recording, comping, latency calibration,
  and MIDI/audio recording on the same timeline are future work.
- No direct input waveform editing, hardware device switching during
  active capture, VST/LV2 host effects or commercial release validation.
  The earlier score-driven SoundFont virtual musicians and score editor
  remain source-stage prototypes dependent on licensed banks.
- Real microphone/device fidelity cannot be inferred from mock tests;
  on the user's actual machine, available driver modes, xrun counts,
  input gain/noise floor, disk throughput and CPU load must be measured.
- On the owner PC, previous owner-modified source files blocked a release
  install. The GitHub **draft** pull request is not installed, merged as
  stable, or allowed to overwrite owner-created changes, Webbie or Nova.

## Regression tests

`tests/test_spider_audio_capture.py` drives a simulated PortAudio stream
to test 16- and 24-bit PCM sample integrity, output header/frames/permissions,
manual input-device enumeration, cancellation, unsupported modes, input
overruns, queue overflow, unique filenames and create-new-only safety.

`tests/test_spider_audio_gui.py` confirms the native console does not open
or enumerate a microphone when the application constructs its recording tab,
and checks meter updates. A real hardware qualification and listening
session is still required before deployment/marketability claims.
