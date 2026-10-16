# Spider native app family: commercial-grade engineering plan
Status 2026-10-15: phase-one prototypes and art assets are source-stage, not tested commercial releases.

## Contract
All existing Ubuntu Studio applications stay installed and working. A Spider app is a real embedded or standalone native workflow, not a renamed launch button. Product icons open existing working bays or programs. Unbuilt products get artwork but **no fake launcher**. No owner data or models enter public source.

| Product | Key capabilities | Design |
|---|---|---|
| Spider Audio Studio | live drums, guitar, bass, piano, sequencer, recording, mixing, mastering, DJ | Violet/magenta |
| Spider Art Lab | graphite, blendable colored pencils, markers, painting, blending, photo-to-outlines | Amber/lilac |
| Spider Video Studio | video timeline, compositing, screen capture, visual effects | Coral/indigo |
| Spider 3D World | modeling, 3D animation, interactive world building | Teal/indigo |
| Spider Author | novels, canon, timeline, writing, publishing | Rose/sand |
| Spider Study | courses, APA, research, citations, assignments | Blue/lavender |
| Spider Media Center | music, video, radio, Nova | Orange/violet |
| Spider Connect | browsing, mail, calendars, device connections | Green/blue |
| Spider Security Center | authorized Kali labs and auditing | Green/blue |
| Spider Control Center | settings, backups, system and devices | Gold/violet |
| Webbie Intelligence | local AI, knowledge, tools and owner permissions | Lavender/pink |

Also designed icons and backgrounds: Spider Forage, Deep Forage, Nova, Recovery and Dev Bay.

## Audio Studio phase one, implemented in this development branch
Native instrument workbench embedded in existing studio/main.py: four original procedural percussion sounds (kick/snare/hat/clap), seven-channel 16-step pattern grid, three drum presets, tempo 40-240 BPM, six-string guitar fretboard, four-string bass fretboard, playable two-octave piano and keyboard shortcuts, per-event pitch, safe JSON pattern save/load, offline 44.1 kHz mono WAV export. The audio engine does not use copied commercial sample packs. Real-time preview is available only when Qt Multimedia works on the host. The rest of the original Studio remains intact.

## Score-driven Auto Performer (new source-stage feature)

The original native Studio now includes an Auto Performer tab: MusicXML, zipped
MXL sheet music, standard guitar/bass ASCII TAB, and chord charts. Timed
polyphonic notes, score tempo/meter, chords/ties, MIDI program selection,
MusicXML drum-kit mappings, standalone MIDI export, and optional FluidSynth
SoundFont WAV playback/render are implemented in source. **This is not OCR**
of photographed or scanned sheet music and not a professional multisampled
instrument library. See docs/SPIDER_AUDIO_AUTO_PERFORMER.md.

## Audio Studio missing commercial features
Low-latency PipeWire/JACK architecture, full multitrack timeline, tempo-accurate audio recording, robust MIDI device handling, LV2/VST3 support as licensed, polyphonic DSP and real guitar/bass articulations, sample libraries with provable rights, session recoverability, user-defined scales/presets, multi-output mixing, hardware tests and accessible controls. The current engine is a **prototype** and cannot honestly be marketed yet.

## Commercial licensing gate
PyQt5 is GPLv3 or separately commercial licensed and not LGPL. Selling GPL-compliant open-source apps is possible, but proprietary distribution requires reviewing/obtaining appropriate licenses or moving the GUI to an appropriate alternative. PySide6's community distribution has LGPLv3/GPLv3 licensing requirements. JUCE 9 has separate commercial licensing and revenue tiers. Ardour/Mixxx/Audacity source code, samples, plugins, assets and codecs must each be checked; no assumption that bundling permits proprietary relicensing. A licensing and software bill of materials review is mandatory before any release.

## Safety and distribution
The source branch is based on reconciliation/ubuntu-studio-26.04-lts-20261015. Previous owner-PC preflight found 31 BLOCKED customized files. No forced copy, installation, OS migration, deletion, replacing Webbie/Nova, or package removal. Source tests and disposable VM/real audio hardware qualification precede any release. This branch alone does not prove installation.