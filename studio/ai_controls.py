"""Backend-neutral Spider Studio AI controls.

These are user *intent* values, not Suno settings or universal model arguments.
Each music/voice backend must advertise and test supported controls; unsupported
controls are reported, not silently pretended to affect generated audio.

No model download, network, filesystem I/O, microphone access or playback.
"""
from dataclasses import asdict, dataclass

SLIDERS = (
    "weirdness", "style_influence", "audio_influence", "variety",
    "vocal_cleanup", "vocal_identity",
)
QUALITY = frozenset({"standard", "max"})
SONG_MODES = frozenset({"creative", "experimental", "quick"})
VOCAL_MODES = frozenset({"my_ai_voice", "actual_recording", "standard_ai_voice", "instrumental"})


@dataclass(frozen=True)
class CreativeControls:
    weirdness: int = 50
    style_influence: int = 75
    audio_influence: int = 80
    variety: int = 0
    vocal_cleanup: int = 35
    vocal_identity: int = 90
    quality: str = "standard"
    song_mode: str = "creative"
    vocal_mode: str = "my_ai_voice"

    def __post_init__(self):
        for name in SLIDERS:
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 100:
                raise ValueError(f"{name} must be an integer from 0 to 100")
        if self.quality not in QUALITY:
            raise ValueError("unknown quality option")
        if self.song_mode not in SONG_MODES:
            raise ValueError("unknown song-generation mode")
        if self.vocal_mode not in VOCAL_MODES:
            raise ValueError("unknown vocal mode")

    def plan(self, *, backend_supported=(), reference_available=False,
             singer_profile_available=False, actual_vocal_available=False):
        """Inspect the intent without starting or promising any generation.

        'backend_supported' is a *verified* adapter capability set, never
        inferred from model name. Only list controls actually implemented by
        that adapter. In particular, default creative sliders are not magical
        synonyms for raw model sampling parameters.
        """
        supported = frozenset(backend_supported)
        if not supported.issubset(SLIDERS):
            raise ValueError("backend supplied an unknown control name")
        if self.vocal_mode == "my_ai_voice" and not singer_profile_available:
            needs = "Create and consent to a private singer profile first."
        elif self.vocal_mode == "actual_recording" and not actual_vocal_available:
            needs = "Import or record an actual vocal take first."
        else:
            needs = None
        controls = {}
        for name in SLIDERS:
            enabled = name in supported
            why = ""
            if name == "audio_influence" and not reference_available:
                enabled, why = False, "Choose a source/reference audio file."
            if name in ("vocal_cleanup", "vocal_identity"):
                if self.vocal_mode not in ("my_ai_voice", "actual_recording"):
                    enabled, why = False, "No owner vocal is selected."
                elif self.vocal_mode == "my_ai_voice" and not singer_profile_available:
                    enabled, why = False, "Private singer profile required."
                elif self.vocal_mode == "actual_recording" and not actual_vocal_available:
                    enabled, why = False, "Recorded owner vocal required."
            if not enabled and not why:
                why = "This backend has not demonstrated control support."
            controls[name] = {
                "requested": getattr(self, name),
                "enabled": enabled,
                "explanation": why,
            }
        return {
            "schema": "spider-studio-ai-controls-v1",
            "owner_intent": asdict(self),
            "controls": controls,
            "ready_for_backend": needs is None,
            "blocker": needs,
            "audio_engine": "unselected",
            "generation_started": False,
        }
