# Spider Audio Studio Wave 10: Native channel strips and protected score exports

The original **Spider Audio Studio**, not Art Lab, is the development priority.

## New: independent track EQ, compression and short room ambience

The real native Session Mixer now has **Edit Selected Track EQ / Compression /
Room** for every verified audio track. It extends existing gain, pan, mute,
solo, and nonnegative delay without creating another launcher.

- Low, middle and high EQ: -12..+12 dB, anchored at 105, 1050 and 6300 Hz.
- Optional 3:1 compressor, and 0..40% short room reflections.
- Channel effects occur before gain and pan in each verified input chain.
- Final 0.95 limiter runs **once after all tracks are summed**.
- Source WAVs stay unchanged. Only a new private WAV is rendered.
- The same mixer stores FX values alongside all existing mix-preset controls.
  Older mix presets still load as dry channels.
- Human-readable channel FX description in the mix table.
- Validated, whitelisted filter syntax means saved presets cannot inject
  arbitrary FFmpeg commands.

## Serious soundbank export safety correction

The actual multibank `render_score_mix` renderer formerly used `os.replace`
to publish WAVs. Wave 10 rejects an existing output, a symlinked output,
or a symlinked parent and uses create-new-only hard linking to publish
an atomic completed file. Concurrent renders cannot silently overwrite
the owner's previous recordings.

A regression suite renders the **real score mixer** using synthetic
per-instrument PCM input and validates the full virtual-band-to-private-cue
handoff rather than mocking Spider's mixer.

## Separate Wave 10 Recording Library Audit

The branch also contains a different
`docs/SPIDER_AUDIO_STUDIO_WAVE10.md` covering the explicit, read-only
recording library inventory. Keep that component intact. This document
records the separate native multitrack channel-strip development, which
builds upon all earlier Waves 1–9.

## Verification

- `tests/test_spider_session_track_fx.py`: real verified multitrack
  session, EQ/compression graph, one final limiter, private saved preset
  round-trip, legacy presets, UI channel controls, parameter safety and
  actual FFmpeg WAV render where installed.
- `tests/test_spider_actual_score_mixer_bridge.py`: multi-bank PCM
  render, new-only output rule, real mixer to recordable cue and symlink
  non-overwrite.

All work remains **GitHub source only**. Passing synthetic CI tests
does not prove physical ADC/DAC latency, actual headphone routing,
licensed sound libraries, real guitar/bass/drum sample quality or
owner-installed native UI compatibility. The feature branch remains
draft and must not overwrite customized installed files without
reconciliation, backup and rollback testing.
