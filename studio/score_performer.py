"""Spider Auto Performer: symbolic score and text tablature to timed MIDI notes.

Safe, offline MusicXML partwise / ASCII guitar+bass tabs. No OCR or claims of
support for complex engraving/repeats/expressive effects. Nothing opens audio
hardware or executes commands during parsing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile, BadZipFile

MAX_BYTES = 2_000_000
MAX_PARTS = 15
MAX_NOTES = 12000
MAX_BEATS = 2048
STEPS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
GUITAR_TUNING = (64, 59, 55, 50, 45, 40)  # high E to low E
BASS_TUNING = (43, 38, 33, 28)  # G D A E
TAB_RE = re.compile(r"^\s*([A-Ga-g](?:[#b])?[0-8]?)\s*\|([-|0-9xX\s]+)\s*$")

def local(tag):
    return tag.rsplit("}", 1)[-1]

def child(node, tag):
    return next((entry for entry in node if local(entry.tag) == tag), None)

def children(node, tag):
    return [entry for entry in node if local(entry.tag) == tag]

def val(node, tag, default=None):
    element = child(node, tag)
    if element is None or element.text is None:
        return default
    return element.text.strip()

def as_integer(value, what):
    try:
        return int(value)
    except (ValueError, TypeError, OverflowError):
        raise ValueError(f"Invalid {what}: {value!r}") from None

@dataclass(frozen=True)
class Part:
    name: str
    program: int
    channel: int

@dataclass(frozen=True)
class Note:
    part: int
    pitch: int
    start: Fraction
    duration: Fraction
    velocity: int = 95

@dataclass
class Performance:
    title: str
    bpm: int
    parts: list[Part]
    notes: list[Note]
    beats: Fraction
    warnings: list[str] = field(default_factory=list)
    meter: tuple[int, int] = (4, 4)
    origin: Path | None = None
    tempo_changes: list[tuple[Fraction, int]] = field(default_factory=list)

    @property
    def duration_seconds(self):
        """Exact duration with written tempo changes, in quarter-note beats."""
        elapsed = 0.0
        previous = Fraction(0)
        tempo = self.bpm
        for beat, next_tempo in self.tempo_changes:
            elapsed += float(beat - previous) * 60 / tempo
            previous, tempo = beat, next_tempo
        return elapsed + float(self.beats - previous) * 60 / tempo

    def validated(self):
        if not isinstance(self.title, str) or not self.title.strip() or len(self.title) > 150:
            raise ValueError("Performance title is invalid")
        if type(self.bpm) is not int or not 30 <= self.bpm <= 280:
            raise ValueError("Performance tempo is outside 30-280 BPM")
        if not isinstance(self.parts, list) or not 1 <= len(self.parts) <= MAX_PARTS:
            raise ValueError("Invalid number of parts")
        if not isinstance(self.notes, list) or not 1 <= len(self.notes) <= MAX_NOTES:
            raise ValueError("No supported notes found or score is too large")
        if not isinstance(self.beats, Fraction) or not 0 < self.beats <= MAX_BEATS:
            raise ValueError("Score duration too long")
        for n in self.notes:
            if (not isinstance(n, Note) or not 0 <= n.part < len(self.parts)
                or not 0 <= n.pitch <= 127 or not 1 <= n.velocity <= 127
                or n.start < 0 or n.duration <= 0 or n.start + n.duration > self.beats):
                raise ValueError("Invalid performance note")
        if (not isinstance(self.meter, tuple) or len(self.meter) != 2
            or not 1 <= self.meter[0] <= 16 or self.meter[1] not in (1, 2, 4, 8, 16)):
            raise ValueError("Unsupported time signature")
        if not isinstance(self.tempo_changes, list) or len(self.tempo_changes) > 512:
            raise ValueError("Too many tempo changes")
        previous = Fraction(0)
        for change in self.tempo_changes:
            if (not isinstance(change, tuple) or len(change) != 2 or
                not isinstance(change[0], Fraction) or not previous < change[0] < self.beats or
                type(change[1]) is not int or not 30 <= change[1] <= 280):
                raise ValueError("Tempo map must have ordered valid mid-score changes")
            previous = change[0]
        return self


def _part_program(name):
    lower = name.casefold()
    if "drum" in lower or "percussion" in lower:
        return 0, True
    if "bass" in lower:
        return 33, False
    if "electric guitar" in lower:
        return 27, False
    if "guitar" in lower:
        return 24, False
    if "violin" in lower:
        return 40, False
    if "cello" in lower:
        return 42, False
    if "organ" in lower:
        return 19, False
    if "piano" in lower or "keyboard" in lower or "keys" in lower:
        return 0, False
    return 0, False


def _midi_pitch(pitch_node, transpose=0):
    step = val(pitch_node, "step")
    if step not in STEPS:
        raise ValueError("MusicXML pitch missing a valid note step")
    octave = as_integer(val(pitch_node, "octave"), "octave")
    alter = as_integer(val(pitch_node, "alter", "0"), "pitch alteration")
    midi = 12 * (octave + 1) + STEPS[step] + alter + transpose
    if not 0 <= midi <= 127:
        raise ValueError("MusicXML pitch falls outside standard MIDI notes")
    return midi


def parse_musicxml(source, title="Imported MusicXML"):
    """Parse a bounded MusicXML score-partwise subset with chords/voices/ties.

    Unsupported repeat instructions and tempo changes are diagnosed rather
    than silently pretending a complex score was reproduced perfectly.
    """
    if isinstance(source, str):
        data = source.encode("utf-8")
    elif isinstance(source, bytes):
        data = source
    else:
        raise TypeError("MusicXML input must be bytes or text")
    if not 0 < len(data) <= MAX_BYTES:
        raise ValueError("MusicXML file is empty or exceeds 2 MB")
    if re.search(br"<!\s*(?:DOCTYPE|ENTITY)\b", data, re.IGNORECASE):
        raise ValueError("MusicXML DTD/external entities are not accepted")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValueError("Invalid MusicXML document") from exc
    if local(root.tag) != "score-partwise":
        raise ValueError("Please export a score-partwise MusicXML file")
    part_list = child(root, "part-list")
    if part_list is None:
        raise ValueError("MusicXML score-part list missing")
    definitions = {}
    # MusicXML enumerates sounds and MIDI programs from 1; MIDI file values
    # start at 0. Honour instrument mappings instead of assuming the staff's
    # printed vertical position is a percussion note pitch.
    sound_definitions = {}
    for descriptor in children(part_list, "score-part"):
        ident = descriptor.attrib.get("id")
        if not ident or ident in definitions:
            raise ValueError("Duplicate or missing MusicXML score-part ID")
        definitions[ident] = val(descriptor, "part-name", "Instrument")
        for sound in children(descriptor, "midi-instrument"):
            sound_id = sound.attrib.get("id")
            if not sound_id:
                continue
            patch = val(sound, "midi-program")
            unpitched = val(sound, "midi-unpitched")
            midi_channel = val(sound, "midi-channel")
            program = None if patch is None else as_integer(patch, "MIDI program")
            drum_note = None if unpitched is None else as_integer(unpitched, "drum note")
            channel = None if midi_channel is None else as_integer(midi_channel, "MIDI channel")
            if program is not None and not 1 <= program <= 128:
                raise ValueError("Invalid MusicXML MIDI program")
            if drum_note is not None and not 1 <= drum_note <= 128:
                raise ValueError("Invalid MusicXML drum note")
            if channel is not None and not 1 <= channel <= 16:
                raise ValueError("Invalid MusicXML channel")
            sound_definitions[(ident, sound_id)] = (
                program - 1 if program is not None else None,
                drum_note - 1 if drum_note is not None else None,
                channel - 1 if channel is not None else None)
    part_nodes = children(root, "part")
    if not 1 <= len(part_nodes) <= MAX_PARTS:
        raise ValueError("MusicXML supports 1 to 15 parts in this prototype")
    parts = []
    for index, node in enumerate(part_nodes):
        ident = node.attrib.get("id")
        if ident not in definitions:
            raise ValueError("MusicXML part not listed in part-list")
        name = definitions[ident][:80]
        program, percussion = _part_program(name)
        sounds = [sound for (owner, _id), sound in sound_definitions.items() if owner == ident]
        if sounds and sounds[0][0] is not None:
            program = sounds[0][0]
        percussion = percussion or any(snd[1] is not None or snd[2] == 9 for snd in sounds)
        used_channels = [p.channel for p in parts]
        if percussion and 9 not in used_channels:
            channel = 9
        else:
            channel = next((i for i in range(16) if i != 9 and i not in used_channels), None)
            if channel is None:
                raise ValueError("No MIDI channels left")
        parts.append(Part(name=name, program=program, channel=channel))
    bpm = 110
    meter = (4, 4)
    warnings = []
    notes = []
    tempo_changes = []
    part_ends = []
    for part_index, node in enumerate(part_nodes):
        division = 1
        part_base = Fraction(0)
        transpose = 0
        current_velocity = 95
        pending_ties = {}
        for measure in children(node, "measure"):
            position = Fraction(0)
            max_cursor = Fraction(0)
            last_start = Fraction(0)
            measure_quarters = Fraction(meter[0] * 4, meter[1])
            for item in measure:
                kind = local(item.tag)
                if kind == "attributes":
                    div = val(item, "divisions")
                    if div is not None:
                        division = as_integer(div, "divisions")
                        if not 1 <= division <= 16383:
                            raise ValueError("MusicXML divisions out of range")
                    trans = child(item, "transpose")
                    if trans is not None:
                        chromatic = as_integer(val(trans, "chromatic", "0"), "transposition")
                        octaves = as_integer(val(trans, "octave-change", "0"), "octave transposition")
                        transpose = chromatic + octaves * 12
                    sig = child(item, "time")
                    if sig is not None:
                        numerator = as_integer(val(sig, "beats", "4"), "meter numerator")
                        denominator = as_integer(val(sig, "beat-type", "4"), "meter denominator")
                        if not 1 <= numerator <= 16 or denominator not in (1, 2, 4, 8, 16):
                            raise ValueError("Unsupported score time signature")
                        proposed = (numerator, denominator)
                        if part_index == 0 and (part_base == 0 or not notes):
                            meter = proposed
                        elif proposed != meter and "Changing time signatures require a dedicated review" not in warnings:
                            warnings.append("Changing time signatures require a dedicated review")
                        measure_quarters = Fraction(numerator * 4, denominator)
                elif kind == "direction":
                    # Dynamics annotations set the performance velocity for
                    # subsequent notes, so scores play with written expression.
                    dynamic_values = {
                        "ppp": 32, "pp": 44, "p": 56, "mp": 69,
                        "mf": 87, "f": 102, "ff": 116, "fff": 124,
                        "sfz": 120, "fp": 82,
                    }
                    for direction_type in children(item, "direction-type"):
                        dynamic = child(direction_type, "dynamics")
                        if dynamic is not None:
                            marks = [local(node.tag) for node in dynamic]
                            for mark in marks:
                                if mark in dynamic_values:
                                    current_velocity = dynamic_values[mark]
                    sound = child(item, "sound")
                    if sound is not None and "dynamics" in sound.attrib:
                        try:
                            current_velocity = max(1, min(127, round(float(sound.attrib["dynamics"]))))
                        except (ValueError, OverflowError):
                            raise ValueError("Invalid MusicXML dynamic level") from None
                    if sound is not None and "tempo" in sound.attrib:
                        try:
                            tempo = round(float(sound.attrib["tempo"]))
                        except (ValueError, OverflowError):
                            raise ValueError("Invalid MusicXML tempo") from None
                        if not 30 <= tempo <= 280:
                            raise ValueError("Tempo outside supported 30-280 BPM")
                        if part_index == 0:
                            beat = part_base + position
                            if beat == 0:
                                bpm = tempo
                            elif tempo_changes and tempo_changes[-1][0] == beat:
                                tempo_changes[-1] = (beat, tempo)
                            elif not tempo_changes or tempo_changes[-1][1] != tempo:
                                tempo_changes.append((beat, tempo))
                elif kind in ("backup", "forward"):
                    duration = as_integer(val(item, "duration"), kind + " duration")
                    if duration <= 0:
                        raise ValueError(kind + " duration must be positive")
                    step = Fraction(duration, division)
                    position += -step if kind == "backup" else step
                    if position < 0:
                        raise ValueError("MusicXML voice backup passes measure start")
                    max_cursor = max(max_cursor, position)
                elif kind == "note":
                    if child(item, "grace") is not None:
                        warnings.append("Grace notes omitted in this player")
                        continue
                    raw_duration = as_integer(val(item, "duration"), "note duration")
                    if raw_duration <= 0:
                        raise ValueError("MusicXML note duration must be positive")
                    duration = Fraction(raw_duration, division)
                    is_chord = child(item, "chord") is not None
                    start = last_start if is_chord else position
                    absolute = part_base + start
                    last_start = start
                    if child(item, "rest") is None:
                        pitch_node = child(item, "pitch")
                        if pitch_node is not None:
                            pitch = _midi_pitch(pitch_node, transpose)
                        elif child(item, "unpitched") is not None:
                            instrument = child(item, "instrument")
                            sound_id = instrument.attrib.get("id") if instrument is not None else None
                            sound = sound_definitions.get((node.attrib.get("id"), sound_id))
                            if sound is None or sound[1] is None:
                                raise ValueError("Unpitched drum note has no MIDI sound mapping")
                            pitch = sound[1]
                        else:
                            raise ValueError("Unsupported MusicXML note without pitch")
                        active_key = (pitch, int(part_index))
                        ties = {tie.attrib.get("type") for tie in children(item, "tie")}
                        note_velocity = current_velocity
                        played_duration = duration
                        for notation in children(item, "notations"):
                            for articulations in children(notation, "articulations"):
                                for articulation in articulations:
                                    marking = local(articulation.tag)
                                    if marking in ("accent", "strong-accent"):
                                        note_velocity = min(127, note_velocity + (
                                            23 if marking == "strong-accent" else 12))
                                    elif marking == "staccato" and not ties:
                                        played_duration = max(Fraction(1, 64), duration * Fraction(1, 2))
                                    elif marking == "staccatissimo" and not ties:
                                        played_duration = max(Fraction(1, 64), duration * Fraction(1, 4))
                        # Stop/continue tie merges duration into one sustained
                        # note; a stop+start is an intermediate continuation.
                        if "stop" in ties and active_key in pending_ties:
                            nindex = pending_ties[active_key]
                            previous = notes[nindex]
                            notes[nindex] = Note(previous.part, previous.pitch,
                                                 previous.start, absolute + duration - previous.start,
                                                 previous.velocity)
                            if "start" not in ties:
                                del pending_ties[active_key]
                        elif "stop" not in ties:
                            note = Note(part_index, pitch, absolute, played_duration,
                                        note_velocity)
                            notes.append(note)
                            if "start" in ties:
                                pending_ties[active_key] = len(notes) - 1
                        else:
                            warnings.append("Encountered a tie without its starting note")
                    if not is_chord:
                        position += duration
                        max_cursor = max(max_cursor, position)
                elif kind in ("barline", "direction"):
                    pass
                elif kind not in ("print", "harmony", "sound", "figured-bass", "grouping"):
                    # We prefer explicit limitations to claiming every MusicXML
                    # marking is supported.
                    if kind not in ("direction",):
                        pass
            # Fixed beat-position for conventional measures; allow pickups.
            part_base += max(measure_quarters, max_cursor)
            if part_base > MAX_BEATS:
                raise ValueError("Score duration exceeds 2,048 quarter-note beats")
        if pending_ties:
            warnings.append("Some ties were not closed in the score")
        part_ends.append(part_base)
    if not notes:
        raise ValueError("No playable pitched notes found")
    end = max([*part_ends, *(n.start + n.duration for n in notes)])
    unique_warnings = list(dict.fromkeys(warnings))
    if any(child(m, "barline") is not None and
           any(child(b, "repeat") is not None for b in children(m, "barline"))
           for p in part_nodes for m in children(p, "measure")):
        unique_warnings.append("Repeat barlines are not expanded; written measures play once")
    actual_title = val(root, "movement-title") or title
    # Late/identical score-end tempo directions do not affect the performed
    # audio and should not break a perfectly valid score.
    tempo_changes = [(beat, value) for beat, value in tempo_changes if beat < end]
    return Performance(str(actual_title)[:150], bpm, parts, notes, end,
                       unique_warnings, meter, tempo_changes=tempo_changes).validated()


def parse_ascii_tab(text, bpm=110, slots_per_beat=2):
    """Read standard 6-string guitar or 4-string bass text tab.

    Each character column carries equal time; tabs rarely encode rhythm.
    Use 2 or 4 slots/beat to choose how quickly the columns advance. Ignore
    fret technique only after explicit error rather than silently losing bends.
    """
    if not isinstance(text, str) or not 1 <= len(text.encode("utf-8")) <= 40_000:
        raise ValueError("Tab must be text under 40 KB")
    if type(bpm) is not int or not 30 <= bpm <= 280:
        raise ValueError("Tempo must be 30–280 BPM")
    if slots_per_beat not in (1, 2, 4):
        raise ValueError("Tab timing must use 1, 2 or 4 columns per beat")
    entries = []
    for line in text.splitlines():
        if not line.strip():
            continue
        match = TAB_RE.match(line)
        if not match:
            raise ValueError("Only E/B/G/D/A guitar or bass tab lines with |, -, numbers and x are supported")
        label, body = match.groups()
        entries.append((label, body.replace("|", "").rstrip()))
    if len(entries) not in (4, 6):
        raise ValueError("Provide all six guitar strings or all four bass strings")
    tuning = GUITAR_TUNING if len(entries) == 6 else BASS_TUNING
    expected = ("E", "B", "G", "D", "A", "E") if len(entries) == 6 else ("G", "D", "A", "E")
    for (label, body), name in zip(entries, expected):
        if label[0].upper() != name:
            raise ValueError("Use standard top-to-bottom string order: " + " ".join(expected))
        if any(ch not in "-0123456789xX " for ch in body):
            raise ValueError("Unsupported tab notation; use fret numbers, '-' and 'x' only")
    length = max(len(body) for _, body in entries)
    if length > 4096:
        raise ValueError("Tab transcription too long")
    kind = "Guitar" if len(entries) == 6 else "Bass"
    notes = []
    for string_index, (_, body) in enumerate(entries):
        for match in re.finditer(r"\d+|x|X", body):
            number = match.group()
            if number.lower() == "x":
                continue
            if len(number) > 2:
                raise ValueError("Fret notation exceeds two digits")
            fret = int(number)
            if not 0 <= fret <= 24:
                raise ValueError("Fret numbers must be between 0 and 24")
            pitch = tuning[string_index] + fret
            start = Fraction(match.start(), slots_per_beat)
            duration = Fraction(1, slots_per_beat)
            notes.append(Note(0, pitch, start, duration))
            if len(notes) > MAX_NOTES:
                raise ValueError("Tab has too many notes")
    if not notes:
        raise ValueError("No playable fret numbers were found")
    beats = Fraction(length, slots_per_beat)
    return Performance(kind + " TAB", bpm,
                       [Part(kind, 24 if kind == "Guitar" else 33, 0)],
                       sorted(notes, key=lambda n: (n.start, n.pitch)),
                       beats,
                       ["Text tabs do not specify exact note lengths; equal column timing is an approximation.",
                        "Bends, slides, palm mute, hammer-ons and guitar articulation are not interpreted."]).validated()


def load_compressed_musicxml(path):
    """Load .mxl MusicXML with bounded in-memory ZIP inspection, never extraction."""
    target = Path(path)
    if target.stat().st_size > MAX_BYTES:
        raise ValueError("MXL archive exceeds 2 MB")
    try:
        with ZipFile(target, "r") as bundle:
            members = bundle.infolist()
            if len(members) > 48:
                raise ValueError("MXL contains too many files")
            if any(member.flag_bits & 1 for member in members):
                raise ValueError("Encrypted MXL entries are not supported")
            if sum(member.file_size for member in members) > 4 * MAX_BYTES:
                raise ValueError("MXL decompressed content exceeds safe limits")
            if any(member.file_size > MAX_BYTES for member in members):
                raise ValueError("MXL entry exceeds 2 MB")
            if "META-INF/container.xml" not in bundle.namelist():
                raise ValueError("MXL score manifest is missing")
            container_data = bundle.read("META-INF/container.xml")
            if re.search(br"<!\s*(?:DOCTYPE|ENTITY)\b", container_data, re.IGNORECASE):
                raise ValueError("MXL XML entities are not accepted")
            manifest = ET.fromstring(container_data)
            if local(manifest.tag) != "container":
                raise ValueError("Invalid MXL manifest")
            rootfiles = next((node for node in manifest.iter()
                              if local(node.tag) == "rootfiles"), None)
            candidates = children(rootfiles, "rootfile") if rootfiles is not None else []
            if not candidates:
                raise ValueError("MXL root score is missing")
            member_path = candidates[0].attrib.get("full-path", "")
            # Never trust ZIP entry names as filesystem paths. Read chosen
            # bytes from memory only; ignore non-score image/media attachments.
            if (not member_path or member_path.startswith("/")
                or "\\" in member_path or ".." in Path(member_path).parts
                or Path(member_path).suffix.lower() not in (".musicxml", ".xml")
                or member_path not in bundle.namelist()):
                raise ValueError("MXL points to an invalid score entry")
            score_data = bundle.read(member_path)
            return parse_musicxml(score_data, target.stem)
    except (BadZipFile, ET.ParseError) as exc:
        raise ValueError("Invalid compressed MusicXML archive") from exc


def load_notation(path, bpm=110, slots_per_beat=2):
    """Read supported files; plain TXT TAB and uncompressed MusicXML only."""
    filename = Path(path)
    if filename.suffix.lower() in (".mid", ".midi"):
        try:
            from .midi_score_import import import_midi_file
        except ImportError:
            from midi_score_import import import_midi_file
        return import_midi_file(filename)
    if filename.suffix.lower() == ".mxl":
        performance = load_compressed_musicxml(filename)
    elif filename.suffix.lower() in (".musicxml", ".xml"):
        if filename.stat().st_size > MAX_BYTES:
            raise ValueError("MusicXML exceeds the 2 MB limit")
        performance = parse_musicxml(filename.read_bytes(), filename.stem)
    elif filename.suffix.lower() in (".txt", ".chords"):
        if filename.stat().st_size > 40_000:
            raise ValueError("Text notation exceeds 40 KB")
        text = filename.read_text(encoding="utf-8")
        if filename.suffix.lower() == ".chords":
            try:
                from .chord_chart_performer import parse_chord_chart
            except ImportError:
                from chord_chart_performer import parse_chord_chart
            performance = parse_chord_chart(text, bpm)
        else:
            performance = parse_ascii_tab(text, bpm=bpm, slots_per_beat=slots_per_beat)
    else:
        raise ValueError("Use .mxl/.musicxml/.xml for notation, .txt for TAB, or .chords for chords")
    performance.origin = filename.resolve()
    return performance
