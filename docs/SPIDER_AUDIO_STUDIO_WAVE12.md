# Spider Audio Studio Wave 12: Multiple real WAV regions per recorded track

## Native performance timeline, not another launcher

Spider Audio Studio's existing verified multitrack mixer now has the
**Arrange Multiple Regions · Performance Timeline** tool. It can choose up to
twelve source passages from a SINGLE owner recording and place them at
independent times on the song timeline, including overlap. This bridges the
old one-source-region editor and a practical multi-phrase arrangement.

The modal native QWidget dialog shows a read-only, bounded waveform thumbnail
from actual WAV PCM, a separate editor row for each region, actions to add,
duplicate, remove or reorder regions and a highlighted selected source
interval. Each row has source start/end, destination song position and
fade-in/out values. Nothing is committed until the user accepts the validated
edit.

The same original WAV provides all passages. FFmpeg loads each source only
once and uses `asplit` for up to 12 branches, with sample-exact source
`atrim`, reset timestamps, branch fades and song-position `adelay`.
The branches rejoin with `amix`, then flow through the **existing** validated
channel EQ/compression/room/gain/pan, mute/solo, and the final stereo limiter.
A one-region legacy clip continues through the original path. Song regions
can overlap, but this is additive playback, not a waveform crossfade system.

## Non-destructive editing, provenance and compatibility

- Only integer bounded source and destination millisecond edits are accepted.
  Clip source edges are converted to integer WAV source-frame indices before
  rendering, and are always checked against verified track length.
- Region count is 1–12, fades 0–30 seconds each with no more than the retained
  region duration, destination positions 0–2 hours, and no render exceeding 2h.
- Each new edit is stored in the existing hash-bound private mix preset and
  documented in the output receipt. Older saved single-clip or dry presets
  continue to load without regions.
- Switching between one-region and multi-region modes is explicit; the
  multi-region editor accepts the previous single trim/delay as the initial
  region. A confirmation precedes replacing an existing multi-region
  arrangement through the legacy single-clip editor.
- The existing source WAVs, prior WAV exports, SoundFont banks, music catalog,
  Webbie services, Nova radio and existing Spider OS installation are not
  touched by this GitHub source build.

## What is / is not complete

This is source code and a GitHub developer preview, not a tested professional
commercial DAW or a verified low-latency live audio device configuration.
An actual multi-track mouse-drag arrangement grid, live automation, elastic
time, full LV2/VST hosting, record-arm routing and high-quality licensed
guitar/bass/drum sound assets remain outside this wave.

`tests/test_spider_session_regions.py` covers precise multi-region filter
graphs, input safety, bounded max 12 regions, overlapping regions,
full sample-generated FFmpeg exported WAV with expected silence and two
passages, unchanged original recordings, backward-compatible mix presets,
and native Qt controls. These run with the normal Spider OS / Studio CI
together with the independent developer archive packaging workflow.

See existing Studio Waves 1–11 documents for instrument, score/MIDI, real
capture, overdub, SoundFont, per-track mix FX, clip editor and standalone
developer preview. Wave 12 is not installed in the owner's PC, and any
installation needs protected reconciliation of previous customized paths.
