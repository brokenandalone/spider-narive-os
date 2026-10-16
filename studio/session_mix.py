"""Reversible, offline stereo render of audited Spider Studio multitrack sessions.

Per-track gain, pan, mute, solo and nonnegative start delay. No instrument
extraction, generative audio, owner-model training or destructive source edits.
"""
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import wave

try:
    from .session_project import inspect_session
    from .multitrack import SessionError
    from .session_track_fx import normalize_track_effects,track_effects_filter
    from .session_clip_edit import normalize_clip_edit,clip_ffmpeg_filters
    from .session_regions import normalize_regions,timeline_filter_segments
except ImportError:
    from session_project import inspect_session
    from multitrack import SessionError
    from session_track_fx import normalize_track_effects,track_effects_filter
    from session_clip_edit import normalize_clip_edit,clip_ffmpeg_filters
    from session_regions import normalize_regions,timeline_filter_segments

DEFAULT_OUTPUT = Path.home() / "Documents/Spider Studio/Music/Session Mixes"
MAX_RENDER_SECONDS = 2 * 3600


def mix_plan(session, controls=None, *, include_reference=False):
    """Validate controls and choose effective stems without invoking FFmpeg."""
    if not isinstance(session, dict) or session.get("verified") is not True:
        raise SessionError("Verify a saved session before attempting to mix.")
    if type(include_reference) is not bool:
        raise SessionError("Reference-mix inclusion must be explicit.")
    controls = {} if controls is None else controls
    if not isinstance(controls, dict):
        raise SessionError("Mix settings must be indexed by track filename.")
    known = {t["filename"] for t in session["tracks"]}
    if not set(controls).issubset(known):
        raise SessionError("Mix settings reference a nonexistent track.")
    planned = []
    for track in session["tracks"]:
        choices = controls.get(track["filename"], {})
        if not isinstance(choices, dict) or not set(choices).issubset(
                {"gain", "pan", "mute", "solo", "delay_ms", "effects", "clip", "regions"}):
            raise SessionError("Unknown per-track mixing control.")
        gain, pan = choices.get("gain", 1.0), choices.get("pan", 0.0)
        delay = choices.get("delay_ms", 0)
        mute, solo = choices.get("mute", False), choices.get("solo", False)
        if (type(gain) not in (int, float) or not math.isfinite(gain)
                or not 0 <= gain <= 2):
            raise SessionError("Track gain must be between 0 and 2.")
        if (type(pan) not in (int, float) or not math.isfinite(pan)
                or not -1 <= pan <= 1):
            raise SessionError("Stereo pan must be between -1 and 1.")
        if type(delay) is not int or not 0 <= delay <= 20000:
            raise SessionError("Track delay must be between 0 and 20000 ms.")
        if type(mute) is not bool or type(solo) is not bool:
            raise SessionError("Mute and solo must be yes or no.")
        effects=normalize_track_effects(choices.get("effects"))
        regions,region_end=normalize_regions(track,choices.get("regions"))
        clip,region=normalize_clip_edit(
            track,choices.get("clip"),delay_ms=delay)
        if regions and (delay!=0 or any(clip.values())):
            raise SessionError(
                "Multi-region timeline editing replaces single clip trims and start delay.")
        planned.append({**track, "gain": float(gain), "pan": float(pan),
                        "delay_ms": delay, "mute": mute, "solo": solo,
                        "effects":effects, "clip":clip, "clip_region":region,
                        "regions":regions, "region_end":region_end})
    # Reference mixes risk doubling tracks; click guides must never enter a release mix.
    eligible = [t for t in planned if not t["mute"] and t["role"] != "click_guide"
                and (include_reference or t["role"] != "reference_mix")]
    if any(t["solo"] for t in eligible):
        eligible = [t for t in eligible if t["solo"]]
    if not eligible:
        raise SessionError("No independent unmuted WAVs selected; reference mix is excluded.")
    if all(t["role"] == "reference_mix" for t in eligible) and not include_reference:
        raise SessionError("An AI reference mix is not independently editable stems.")
    if max(t["region_end"] if t["regions"] else
           t["clip_region"].duration_seconds + t["delay_ms"]/1000
           for t in eligible) > MAX_RENDER_SECONDS:
        raise SessionError("A finished session cannot exceed two hours.")
    return {"active": eligible, "settings": planned,
            "reference_included": any(t["role"] == "reference_mix" for t in eligible),
            "warnings": (["Reference mix included: may double existing instruments."]
                         if any(t["role"] == "reference_mix" for t in eligible) else [])}


def ffmpeg_command(ffmpeg, plan, output):
    """Produce a safe argument vector and bounded filter graph; never use a shell."""
    target = Path(output).expanduser()
    if target.is_symlink() or target.exists() or target.suffix.lower() != ".wav":
        raise SessionError("Mix export must be a new WAV file.")
    active = plan["active"]
    if not active or len(active) > 24:
        raise SessionError("Select 1 to 24 valid session tracks.")
    cmd = [str(ffmpeg), "-hide_banner", "-loglevel", "error",
           "-nostdin", "-n"]
    filters, pads = [], []
    for index, entry in enumerate(active):
        cmd.extend(["-i", str(entry["path"])])
        # All inputs converted to common sample rate and stereo layout.
        # Equal-power balance is deliberately NOT assumed: pan scales the
        # opposing stereo channel and therefore does not secretly boost center.
        left = min(1.0, 1.0 - entry["pan"])
        right = min(1.0, 1.0 + entry["pan"])
        delay = f",adelay={entry['delay_ms']}:all=1" if entry["delay_ms"] else ""
        channel_fx=track_effects_filter(entry.get("effects"))
        effect_section=channel_fx+"," if channel_fx else ""
        if entry.get("regions"):
            declarations,pad=timeline_filter_segments(
                index,entry,entry["regions"])
            filters.extend(declarations)
            # Placement is already applied to each individual region.
            delay=""
        else:
            region=entry.get("clip_region")
            if region is None:
                _,region=normalize_clip_edit(entry,entry.get("clip"),
                                              delay_ms=entry["delay_ms"])
            clip_filters=clip_ffmpeg_filters(region)
            pad=f"[{index}:a:0]"
            # Single clip path retains its older latency and fade semantics.
            filters.append(
                f"{pad}{clip_filters},aresample=48000,"
                "aformat=sample_fmts=fltp:channel_layouts=stereo"
                f"[source{index}]")
            pad=f"[source{index}]"
        filters.append(
            f"{pad}{','+effect_section[:-1] if effect_section else ''}"
            f",volume={entry['gain']:.4f},"
            f"pan=stereo|c0={left:.4f}*c0|c1={right:.4f}*c1"
            f"{delay}[track{index}]"
        )
        pads.append(f"[track{index}]")
    filters.append(
        "".join(pads) + f"amix=inputs={len(active)}:duration=longest:"
        "dropout_transition=0:normalize=0,alimiter=limit=0.95[out]"
    )
    cmd.extend(["-filter_complex", ";".join(filters), "-map", "[out]",
                "-ac", "2", "-ar", "48000", "-c:a", "pcm_s24le", str(target)])
    return cmd


def render_session(folder, *, controls=None, include_reference=False,
                   output_root=None, timeout=3600, stop=None):
    """Verify all WAV checksums again, then render one fresh private mix."""
    if type(timeout) not in (int, float) or not 1 <= timeout <= 7200:
        raise SessionError("Invalid render timeout.")
    stop = stop if stop is not None else threading.Event()
    if stop.is_set():
        raise SessionError("Mix cancelled before beginning.")
    session = inspect_session(folder, stop=stop)
    plan = mix_plan(session, controls, include_reference=include_reference)
    executable = shutil.which("ffmpeg")
    if not executable:
        raise SessionError("FFmpeg is required for offline session mixing.")
    parent = Path(output_root).expanduser() if output_root else DEFAULT_OUTPUT
    if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
        raise SessionError("The output folder must be a real directory.")
    try:
        parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        destination = Path(tempfile.mkdtemp(prefix="session-mix-", dir=parent))
        os.chmod(destination, 0o700)
        output = destination / "session-mix.wav"
        command = ffmpeg_command(executable, plan, output)
        log = destination / "ffmpeg.log"
        with log.open("xb") as stream:
            os.chmod(log, 0o600)
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                       stdout=stream, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                if stop.is_set() or time.monotonic() >= deadline:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                    raise SessionError("Mix cancelled or timed out. All source tracks remain unchanged.")
                stop.wait(0.15)
        if process.returncode != 0 or output.is_symlink() or not output.is_file():
            raise SessionError("FFmpeg could not finish the mix. Review the private ffmpeg.log.")
        try:
            with wave.open(str(output), "rb") as stream:
                if (stream.getnframes() <= 0 or stream.getframerate() != 48000
                        or stream.getnchannels() != 2):
                    raise SessionError("Rendered mix must be a nonempty 48 kHz stereo PCM WAV.")
        except (OSError, EOFError, wave.Error) as error:
            raise SessionError("Rendered mix is not a valid PCM WAV.") from error
        os.chmod(output, 0o600)
        receipt = {
            "schema": 1, "project_title": session["title"],
            "source_session": str(session["directory"]),
            "export_file": output.name, "export_rate": 48000,
            "reference_included": plan["reference_included"],
            "warnings": plan["warnings"], "original_tracks_preserved": True,
            "verified_before_render": True,
            "tracks": [{key: item[key] for key in
                        ("filename", "role", "sha256", "gain", "pan",
                         "delay_ms", "mute", "solo", "effects", "clip", "regions")} for item in plan["settings"]],
            "active_filenames": [track["filename"] for track in plan["active"]],
        }
        with (destination / "mix-receipt.json").open("x", encoding="utf-8") as file:
            os.chmod(destination / "mix-receipt.json", 0o600)
            json.dump(receipt, file, indent=2)
        return output
    except OSError as error:
        raise SessionError("Could not complete a private session mix.") from error
