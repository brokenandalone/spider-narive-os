"""Text-level band arrangement for local song generation.

Labels are creative roles, not learned voice models or biometric identities.
ACE-Step text-to-music may ignore singer swaps, guitar separation, or panning.
"""
VOICE_PRESETS = {
    "Justin Therapy (original baritone)": "Original deep masculine baritone with weathered Southern gothic rock delivery; not a verified recreation of any actual voice",
    "Original feminine alto": "Distinct original feminine alto singer, warm lower register and expressive clear phrasing",
    "Original feminine soprano": "Distinct original feminine soprano singer, airy but powerful sustained upper-register phrasing",
    "Original masculine tenor": "Distinct original masculine tenor singer, expressive upper-mid register",
    "Jason (original character voice)": "Original guest singer identified as Jason in the arrangement; timbre must be invented rather than cloned from an individual",
    "J-Cold (original character voice)": "Original guest singer identified as J-Cold in the arrangement; timbre must be invented rather than cloned from an individual",
    "Custom original singer": "An additional original vocalist defined by the user's arrangement instructions",
}
VOICE_OPTIONS = ("None", *VOICE_PRESETS)


def arrangement_text(voices=(), voice_notes="", guitar_one="", guitar_two="", other_instruments=""):
    """Compose bounded creative instructions; do not promise separated tracks."""
    if not isinstance(voices, (tuple, list)) or len(voices) > 3:
        raise ValueError("Choose at most three vocal roles.")
    for role in voices:
        if role not in VOICE_PRESETS:
            raise ValueError("Unknown vocal role.")
    for name, value, limit in (
        ("Vocal instructions", voice_notes, 1600),
        ("Guitar one", guitar_one, 400),
        ("Guitar two", guitar_two, 400),
        ("Other instruments", other_instruments, 700),
    ):
        if not isinstance(value, str) or len(value) > limit:
            raise ValueError(f"{name} must be text under {limit} characters.")
    lines = []
    if voices:
        lines.append("VOCAL ARRANGEMENT (multiple distinct original singers):")
        for index, singer in enumerate(voices, 1):
            lines.append(f"Singer {index}: {VOICE_PRESETS[singer]}.")
        if len(voices) > 1:
            lines.append("Trade lead phrases between singers as marked in the lyrics; layer distinct harmonies on shared choruses. Do not collapse all voices into one singer.")
    if voice_notes.strip():
        lines.append("Vocal parts and lyric assignments: " + voice_notes.strip())
    if guitar_one.strip():
        lines.append("Guitarist 1, separate rhythm performance: " + guitar_one.strip())
    if guitar_two.strip():
        lines.append("Guitarist 2, independent lead or harmony performance: " + guitar_two.strip())
        lines.append("Two clearly distinguishable guitars, playing complementary parts rather than unison doubling.")
    if other_instruments.strip():
        lines.append("Other band instruments: " + other_instruments.strip())
    return "\n".join(lines)
