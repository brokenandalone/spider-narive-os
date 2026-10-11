"""Private, reversible owner listening trials for My Voice conversion quality.

No model execution, automatic scoring, speaker recognition, AI generation,
microphone access or network calls. A/B order is randomized, ratings are
human-entered and do not certify that a model is trained or identity-matched.
"""
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import stat
import tempfile
import threading
from datetime import datetime, timezone
import wave

try:
    from .voice_profile import VoiceSampleError
except ImportError:
    from voice_profile import VoiceSampleError

DEFAULT_ROOT = Path.home() / "Documents/Spider Studio/Music/My Voice/Listening Trials"
CRITERIA = ("identity", "pitch", "clarity", "expression", "artifact_free")
MAX_BYTES = 1024 ** 3
MAX_NOTE = 500


def _pcm(path):
    if not isinstance(path, (str, Path)) or not str(path).strip():
        raise VoiceSampleError("Choose an original and a converted vocal WAV.")
    source = Path(path).expanduser()
    if (source.is_symlink() or not source.is_file() or source.suffix.lower() != ".wav"):
        raise VoiceSampleError("Comparison requires existing non-linked PCM WAV recordings.")
    meta = source.stat()
    if not stat.S_ISREG(meta.st_mode) or not 44 <= meta.st_size <= MAX_BYTES:
        raise VoiceSampleError("Voice comparison WAV must be nonempty and at most 1 GiB.")
    try:
        with wave.open(str(source), "rb") as reader:
            if (reader.getcomptype() != "NONE" or not 1 <= reader.getnchannels() <= 2
                    or reader.getsampwidth() not in (1, 2, 3, 4)
                    or not 8000 <= reader.getframerate() <= 192000
                    or reader.getnframes() <= 0):
                raise VoiceSampleError("Comparison requires ordinary mono/stereo PCM WAV.")
            length = reader.getnframes() / reader.getframerate()
            if not 1 <= length <= 1200:
                raise VoiceSampleError("Choose a 1-second to 20-minute vocal recording.")
            return source.resolve(), {
                "rate": reader.getframerate(), "channels": reader.getnchannels(),
                "frames": reader.getnframes(), "duration_seconds": round(length, 4),
                "bytes": meta.st_size, "mtime_ns": meta.st_mtime_ns,
            }
    except (OSError, EOFError, wave.Error) as error:
        raise VoiceSampleError("Could not decode a selected vocal WAV.") from error


def _copy_verified(src, dst, expected, stop):
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(src, flags)
    digest = hashlib.sha256()
    with os.fdopen(fd, "rb") as inp, dst.open("xb") as output:
        os.chmod(dst, 0o600)
        state = os.fstat(inp.fileno())
        if (not stat.S_ISREG(state.st_mode) or state.st_size != expected["bytes"]
                or state.st_mtime_ns != expected["mtime_ns"]):
            raise VoiceSampleError("A vocal changed before the private listening copy.")
        while True:
            if stop.is_set():
                raise VoiceSampleError("Listening trial creation cancelled.")
            chunk = inp.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
            digest.update(chunk)
        after = os.fstat(inp.fileno())
        if (after.st_size != state.st_size or after.st_mtime_ns != state.st_mtime_ns):
            raise VoiceSampleError("An input vocal changed during copy.")
    return digest.hexdigest()


def _trial_manifest(directory):
    root = Path(directory).expanduser()
    if root.is_symlink() or not root.is_dir() or not root.name.startswith("trial-"):
        raise VoiceSampleError("Select a valid private My Voice listening trial.")
    manifest = root / "trial.json"
    secret = root / "private-assignment.json"
    if (manifest.is_symlink() or secret.is_symlink() or
            not manifest.is_file() or not secret.is_file() or
            not 0 < manifest.stat().st_size < 16000 or
            not 0 < secret.stat().st_size < 16000):
        raise VoiceSampleError("The listening-trial receipts are missing or linked.")
    try:
        public = json.loads(manifest.read_text(encoding="utf-8"))
        key = json.loads(secret.read_text(encoding="utf-8"))
    except (ValueError, OSError, UnicodeError) as error:
        raise VoiceSampleError("Listening-trial metadata is corrupt.") from error
    if (not isinstance(public, dict) or public.get("schema") != 1
            or public.get("candidate_labels") != ["A", "B"]
            or not isinstance(key, dict) or key.get("schema") != 1
            or key.get("assignment") not in
               ({"A": "original", "B": "converted"},
                {"A": "converted", "B": "original"})):
        raise VoiceSampleError("Unsupported or altered listening-trial layout.")
    for label in ("A", "B"):
        path = root / (label + ".wav")
        if path.is_symlink() or not path.is_file():
            raise VoiceSampleError("A trial's vocal is missing or linked.")
        target_sha = public.get("candidate_sha256", {}).get(label)
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != target_sha:
            raise VoiceSampleError(f"Trial {label} WAV changed after creation.")
    return root, public, key


def create_voice_trial(original, converted, *, output_root=None, stop=None):
    """Randomize copies and record private provenance without overwriting inputs."""
    stop = stop if stop is not None else threading.Event()
    if stop.is_set():
        raise VoiceSampleError("Listening trial creation cancelled.")
    source_a, meta_a = _pcm(original)
    source_b, meta_b = _pcm(converted)
    if source_a == source_b:
        raise VoiceSampleError("Provide separate original and converted WAV recordings.")
    if abs(meta_a["duration_seconds"] - meta_b["duration_seconds"]) > 3:
        raise VoiceSampleError(
            "Original and converted excerpts differ by more than 3 seconds; "
            "compare aligned sections of the same performance.")
    root = Path(output_root).expanduser() if output_root else DEFAULT_ROOT
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        raise VoiceSampleError("Choose an actual local private listening-trial folder.")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="trial-", dir=root))
    os.chmod(directory, 0o700)
    roles = {"A": "original", "B": "converted"}
    if secrets.randbelow(2):
        roles = {"A": "converted", "B": "original"}
    sources = {"original": (source_a, meta_a), "converted": (source_b, meta_b)}
    digests = {}
    try:
        for label, role in roles.items():
            src, meta = sources[role]
            digests[label] = _copy_verified(src, directory / (label + ".wav"), meta, stop)
        if digests["A"] == digests["B"]:
            raise VoiceSampleError("Both listening candidates contain identical audio.")
        manifest = {
            "schema": 1, "kind": "owner_voice_listening_trial",
            "candidate_labels": ["A", "B"], "candidate_sha256": digests,
            "rating_criteria": list(CRITERIA), "blind_order_not_identity_proof": True,
            "audio_level_matched": False, "timing_automatically_aligned": False,
            "trained_model_verified": False,
            "results_are_manual_only": True, "original_audio_preserved": True,
        }
        with (directory / "trial.json").open("x", encoding="utf-8") as out:
            os.chmod(directory / "trial.json", 0o600)
            json.dump(manifest, out, indent=2)
        secret = {
            "schema": 1, "assignment": roles,
            "original_source": str(source_a), "converted_source": str(source_b),
            "not_a_model_certificate": True,
        }
        with (directory / "private-assignment.json").open("x", encoding="utf-8") as out:
            os.chmod(directory / "private-assignment.json", 0o600)
            json.dump(secret, out, indent=2)
        return directory
    except BaseException:
        shutil.rmtree(directory, ignore_errors=True)
        raise


def save_voice_review(folder, ratings, *, listened_to_both=False, notes=""):
    """Save a new immutable human review without changing either vocal or model."""
    if listened_to_both is not True:
        raise VoiceSampleError("Listen to both A and B before saving a rating.")
    if not isinstance(notes, str) or len(notes) > MAX_NOTE or any(
            ord(ch) < 32 and ch not in "\n\t" for ch in notes):
        raise VoiceSampleError("Listening notes must be plain text under 500 characters.")
    if not isinstance(ratings, dict) or set(ratings) != {"A", "B"}:
        raise VoiceSampleError("Rate both anonymous comparison candidates.")
    for label in ("A", "B"):
        row = ratings[label]
        if not isinstance(row, dict) or set(row) != set(CRITERIA):
            raise VoiceSampleError("Rate identity, pitch, clarity, expression and artifacts.")
        if any(type(value) is not int or not 1 <= value <= 5 for value in row.values()):
            raise VoiceSampleError("Use whole-number listener ratings from 1 to 5.")
    root, public, key = _trial_manifest(folder)
    scores = {label: dict(ratings[label]) for label in ("A", "B")}
    data = {
        "schema": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
        "ratings": scores, "listened_to_both": True,
        "notes": notes, "assignment_revealed_after_scoring": key["assignment"],
        "candidate_sha256": public["candidate_sha256"],
        "subjective_review_only": True,
        "training_started": False, "identity_auto_verified": False,
        "original_audio_unchanged": True,
    }
    fd, temporary = tempfile.mkstemp(prefix=".review-", dir=root)
    os.close(fd)
    temp = Path(temporary)
    try:
        os.chmod(temp, 0o600)
        temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        # Exclusive link never overwrites an existing review; a new filename
        # is created for each run, preserving earlier opinions.
        final = root / ("review-" + secrets.token_hex(16) + ".json")
        os.link(temp, final)
        return final
    finally:
        temp.unlink(missing_ok=True)
