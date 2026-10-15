# Spider Audio Studio: self-playing professional instrument system

## Product contract
A user can import a score, choose instruments and feel, press **Play**, and hear
the virtual ensemble perform the written music in native Spider Audio Studio.
Editing the performance must not change the source score. User-owned/locally
licensed samples remain private and are never included in published GitHub
builds. Original Ubuntu Studio tools, Spider bays, Webbie and Nova remain intact.

## Implemented in the current development branch (not hardware qualified)
- **Sources**: MusicXML score-partwise files, compressed MXL, standard guitar/
  bass ASCII TAB with honest approximated-column timing, and text-only chord
  charts with generated ORIGINAL generic backing parts.
- **MusicXML reading**: multiple parts, polyphony, voices, written notes/rests,
  ties, first notated tempo, instrumentation, basic transposition, and selected
  dynamics (ppp to fff) and staccato/accent articulation. Advanced tempo maps,
  ornaments, and repeat expansion still require further development.
- **Interpretation**: deterministic reproducible human feel, energy scaling,
  60% eighth swing, laid-back or driving rock timing, and separate note attacks
  on guitar chords. No pitch is invented, lost or transposed by expression.
- **Instrument choice**: per-part GM program and user-selected SF2/SF3 sample
  bank; single-bank fast rendering or independent part passes, selected 44.1/48
  kHz sample rate, and independent part gain, pan, mute and solo.
- **Sound**: offline FluidSynth rendering where available, atomic WAV output,
  bounded memory streaming during multi-bank stereo mixing and no shell
  invocation. Optional playback in the Qt audio stack.
- **Interchange**: standard MIDI format-1 per-part export for external DAWs;
  source notation is not overwritten. Separate native song arrangement,
  waveform editor, virtual instrument workbench and offline DJ deck panels
  remain integrated within Spider Studio.
- **Discovery**: check a bounded set of conventional local SoundFont folders
  for validated RIFF SoundFonts. No automatic download, install or external
  audio-device access. Largest installed bank is only a heuristic audition
  default, NEVER a guarantee of its audio quality, license or supported patches.
- **Verification**: headless source, UI, XML dynamics, SoundFont-selection,
  expression, MIDI and stereo-mix tests. Real sound-card, PipeWire, plugin,
  instrument fidelity and mixing listening tests are not implied by CI.

## Unfinished prerequisites before claiming top-tier sound
- Actually install and audition legally licensed **multisampled** instruments
  for grand piano, drums, electric/acoustic guitar, bass and orchestral parts,
  matching instrument layers, keyswitches, pedal techniques, release samples,
  round robins, velocity layers, mic positions and articulations.
- Complete human performance nuance: true rhythmic TAB formats, bends,
  vibrato, slides, hammer-ons, harmonics, drum rudiments, expressive automation,
  tempo maps, nested repeats and score-level timbre switches.
- Real-time low-latency PipeWire/JACK integration, live MIDI recording,
  non-destructive multitrack timeline, undo, resampling, metering,
  professional plugin hosting and mastering to commercial export standards.
- Sheet photo and PDF recognition with human correction, optional Guitar Pro
  support under compatible license and deployment rules.
- Stability testing with the user's CPU/HDD, audio interface, webcam/mics and
  MIDI devices; performance scaling, crash-recovery, accessibility, sound
  rights and distribution/license review. Currently depends on Qt/PyQt5,
  FluidSynth and user-supplied SoundFonts. **No claims of a market-ready DAW.**
- Reconcile the previous 31 blocked customized owner-system files BEFORE any
  deployment. CI-only changes remain on a draft pull request.

## Intended flow
`Import score or TAB → Validate parts → Select sound per musician → Choose
performance groove and dynamics → Play → Adjust channel mix → Export WAV/MIDI`

A single “Auto Performer · Scores & TAB” tab now hosts the full workflow.
Previous parallel score engine files remain for compatibility but are not
launched as duplicate UI pages.

## Audio quality policy
Neither filename, samplebank size nor the SoundFont format establishes
studio-quality sound. Stereo 16-bit source processing is an intermediate
prototype, not the final release/recording/mastering standard. Do not promise
24-bit deliverables, SFZ/VST integration, acoustic articulations or automatic
high-fidelity instrument downloads until they actually work and pass listening
and licensing tests.
