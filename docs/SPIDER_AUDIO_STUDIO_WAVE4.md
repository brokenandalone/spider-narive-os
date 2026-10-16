# Spider Audio Studio wave 4: Performance Editor, sessions and stems

## What is implemented

**Native workflow:** Load sheet music, standard MIDI, four/six-string text TAB,
or a chord chart in **Auto Performer**. Open **Performance Note Editor** to
inspect a custom purple piano roll and a synchronized, paginated note-event
table. Click a piano-roll event or select a table row. Change pitch, onset,
duration and velocity; apply quantization at quarter, eighth, sixteenth,
triplet or 64th grids with variable strength; transpose one melodic part
without reassigning drum-kit pitches; delete a note; undo or redo changes.

**Non-destructive state:** Every score-edit operation makes a validated deep
copy; failed edits do not replace the current score or advance history.
Undo/redo stores at most 24 revisions, preventing unbounded memory growth.
The original imported score/MIDI/TAB file remains untouched. The modified
notes flow immediately back to Auto Performer for MIDI export, SoundFont
rendering and the existing humanization controls.

**Local session save/open:** A versioned `.spiderscore` JSON file stores exact
rational note times (including triplets), titles, track/instrument programs,
tempo map, 4/4 or imported meter, mixer gain/pan/mute/solo, performance
groove, energy, guitar strum spread, and output preferences. File size is
capped at 4 MB and save is atomic. No microphone audio, imported file paths,
SoundFont samples or library data are embedded. Local sample banks must be
selected again when a session is opened. A read-only older score will never
be overwritten when its path matches the destination.

**Isolated audio stems:** User selects a parent folder. Each score part uses
its chosen legal local SF2/SF3 bank and installed FluidSynth CLI, independently
rendering dry stereo 16-bit WAV. Files are aligned to sample zero and padded
with digital silence to a common ending, with optional 24-bit output
containers (precision NOT conjured from 16-bit source samples).
Muted/soloed tracks are included as independent dry stems. `stems.json`
identifies each part and bank filename without embedding full system paths.
Export creates an entirely NEW folder, atomically when all tracks pass
validation. Existing stem folders and source instrument files are protected.
An estimated 1.2 GB output bound and five-minute score limit prevent runaway
memory/disk use. Stems can be imported into full DAWs to continue work.

**Native UI:** The Auto Performer panel is scrollable and hosts buttons for
editing, saving/opening sessions and dry stem export. The performance editor
is a functional separate **native tab**, not an external launcher. Up to 300
notes per display page keep large performances responsive.

## Tests added
- `tests/test_spider_score_edit_session.py`: atomic edits, undo/redo,
  quantize/transpose, exact rational session roundtrip and hostile inputs.
- `tests/test_spider_score_stem_export.py`: aligned silent/active 16/24-bit
  parts, manifest metadata, per-part licensed sample routing and failure
  cleanup without half-exported directories.
- `tests/test_spider_audio_gui.py` extended: real piano-roll rasterization,
  interactive editor controls and edited notes reaching Auto Performer.

## Remaining before a marketed, top-tier DAW
- Real-time PipeWire/JACK capture with efficient latency, live instrument
  selection and recording, LV2/VST-compatible effect and instrument hosting,
  waveform/piano-roll drag editing, looped takes and comping, controller
  automation, extensive musical articulation and rhythmic TAB support.
- Purchase/verify distributable multisample libraries and physically audition
  guitar, bass, piano, drum, orchestral performance on target audio hardware.
- Studio session format currently does not embed a complete audio-take
  workspace or licensed samples. It is a symbolic score and mixer session,
  not a claim to replace a mature Ardour session.
- CI source validation is not installation, real-hardware MIDI tests,
  audio-interface testing, or market-quality listening approval.
- Respect 31 locally drifted/blocked owner files found in prior Spider OS
  reconciliation. PR stays draft. Native Spider Studio, Webbie and Nova
  installed audio/radio services remain untouched during GitHub work.
