"""Wave 9: supervised local ACE-Step music renders for the Operations Hub.

Reuses installed Studio music_backend.LocalMusicClient. Nothing starts or
downloads a model automatically. A real render needs a confirmed owner GUI
click, an existing user-chosen destination, and a responsive loopback engine.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import sys
import threading

DEFAULT_ROOT = Path(__file__).resolve().parents[1]


def _studio_backend(root=DEFAULT_ROOT):
    studio = Path(root) / "studio"
    source = studio / "music_backend.py"
    if source.is_symlink() or not source.is_file():
        raise RuntimeError("The installed Spider Studio music engine is missing.")
    # Import only the existing approved Studio backend; never execute a
    # model-provided filename, arbitrary subprocess, or network helper.
    if str(studio) not in sys.path:
        sys.path.insert(0, str(studio))
    from music_backend import LocalMusicClient, SongRequest
    return LocalMusicClient, SongRequest


@dataclass(frozen=True)
class SongDraft:
    title: str
    style: str
    lyrics: str = ""
    instrumental: bool = False
    seconds: int = 180
    takes: int = 1
    bpm: int = 0
    endpoint: str = "http://127.0.0.1:8001"

    def validate(self):
        if (not isinstance(self.title, str) or not self.title.strip()
                or len(self.title) > 200):
            raise ValueError("Enter a song title of at most 200 characters.")
        if (not isinstance(self.style, str) or not self.style.strip()
                or len(self.style) > 8000):
            raise ValueError("Enter a musical style of at most 8000 characters.")
        if not isinstance(self.lyrics, str) or len(self.lyrics) > 20000:
            raise ValueError("Lyrics must contain at most 20,000 characters.")
        if type(self.instrumental) is not bool:
            raise ValueError("Instrumental selection must be a boolean.")
        if not self.instrumental and not self.lyrics.strip():
            raise ValueError("Enter lyrics or select instrumental.")
        for name, value, low, high in (
            ("seconds", self.seconds, 10, 600),
            ("takes", self.takes, 1, 2),
        ):
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"{name} must be between {low} and {high}.")
        if type(self.bpm) is not int or (
            self.bpm != 0 and not 30 <= self.bpm <= 300
        ):
            raise ValueError("Tempo must be 0 (auto) or 30 to 300 BPM.")
        client_cls, _ = _studio_backend()
        # Validates numeric loopback URL and explicitly rejects proxy/remote.
        client_cls(self.endpoint)
        return True

    def preview(self):
        self.validate()
        return {
            "workspace": "Spider Studio",
            "operation": "local_ace_step_preview",
            "mode": "preview_only",
            "title": self.title.strip(),
            "style_characters": len(self.style),
            "lyric_characters": len(self.lyrics),
            "instrumental": self.instrumental,
            "duration_seconds": self.seconds,
            "takes": self.takes,
            "bpm": self.bpm,
            "engine_endpoint": self.endpoint,
            "engine_contacted": False,
            "generation_started": False,
            "note": "Preview only. ACE-Step's actual model capability and output "
                    "are not guaranteed. No engine or model installed.",
        }

    def _request(self):
        _, request_cls = _studio_backend()
        return request_cls(
            title=self.title.strip(),
            style=self.style,
            lyrics=self.lyrics,
            instrumental=self.instrumental,
            duration=self.seconds,
            takes=self.takes,
            bpm=self.bpm,
            vocal_mode="ai_lead",
        )


def engine_health(endpoint="http://127.0.0.1:8001"):
    client_cls, _ = _studio_backend()
    health = client_cls(endpoint).health()
    return {
        "workspace": "Spider Studio",
        "mode": "read_only",
        "operation": "ace_step_health",
        "engine_responding": True,
        "health_status": health.get("status", "unknown"),
        "generation_started": False,
        "note": "A health response is not proof that a real render works.",
    }


def render_song(draft, output_directory, *, owner_approved=False,
                stop=None, progress=None):
    """One explicit user-selected render. May continue server-side if cancelled."""
    if owner_approved is not True:
        raise PermissionError("Owner confirmation is required before generating audio.")
    if not isinstance(draft, SongDraft):
        raise ValueError("Choose a reviewed local Studio request.")
    draft.validate()
    target = Path(output_directory).expanduser()
    if target.is_symlink() or not target.is_dir():
        raise ValueError("Choose an existing ordinary output folder.")
    if not target.is_absolute():
        raise ValueError("Choose an absolute output directory.")
    if stop is not None and stop.is_set():
        raise RuntimeError("Generation was cancelled before submission.")
    client_cls, _ = _studio_backend()
    client = client_cls(draft.endpoint)
    # LocalMusicClient owns the original versioned per-job manifest, output
    # WAV validation, dedup/no auto-retry, timeout and cancelled-job handling.
    result = client.generate(
        draft._request(), target, stop=stop, progress=progress,
        timeout=1800, poll_interval=2,
    )
    return {
        "workspace": "Spider Studio",
        "operation": "local_ace_step_render",
        "mode": "owner_approved_write",
        "output_job_directory": str(result),
        "generation_started": True,
        "note": "Listen to each take before approval. Originals remain untouched.",
    }
