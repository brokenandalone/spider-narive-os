"""Create physically separate RVC training and holdout folders without voice training.

No generated profile or trusted identity is implied. The held-out clips are
never copied into the training directory; prevent accidental evaluation leakage.
Works only with existing owner-consented, hash-verified Spider Studio datasets.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
import threading

try:
    from .voice_profile import VoiceSampleError
except ImportError:
    from voice_profile import VoiceSampleError

MAX_FILES = 256
MAX_BYTES = 2 * 1024 ** 3
MIN_TRAIN_SECONDS = 600.0
FILE_RE = re.compile(r"^audio/clip-[0-9]{4}\.(wav|mp3|flac)$")
CHECKSUM_RE = re.compile(r"^[0-9a-f]{64}$")


def _read_dataset(folder):
    root = Path(folder).expanduser()
    if root.is_symlink() or not root.is_dir():
        raise VoiceSampleError("Select an existing private RVC training dataset.")
    root = root.resolve()
    manifest = root / "manifest.json"
    if (manifest.is_symlink() or not manifest.is_file()
            or not 0 < manifest.stat().st_size <= 256 * 1024):
        raise VoiceSampleError("Cannot open the consented voice dataset manifest.")
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as error:
        raise VoiceSampleError("Cannot decode the dataset manifest.") from error
    if (not isinstance(data, dict) or data.get("schema") != 1
            or data.get("owner_consent") is not True
            or data.get("speaker") != "owner"):
        raise VoiceSampleError("A documented owner-consented dataset is required.")
    recordings = data.get("samples")
    if not isinstance(recordings, list) or not 3 <= len(recordings) <= MAX_FILES:
        raise VoiceSampleError("Collect at least three separate training clips first.")
    paths, seen, total = [], set(), 0
    for item in recordings:
        if not isinstance(item, dict):
            raise VoiceSampleError("Malformed voice dataset entry.")
        name, fingerprint = item.get("file"), item.get("sha256")
        seconds = item.get("duration_seconds")
        if (not isinstance(name, str) or not FILE_RE.fullmatch(name)
                or name in seen or not isinstance(fingerprint, str)
                or not CHECKSUM_RE.fullmatch(fingerprint)
                or type(seconds) not in (int, float) or not 0.2 <= seconds <= 3600):
            raise VoiceSampleError("Invalid dataset clip name, hash, or duration.")
        seen.add(name)
        source = root / name
        if source.is_symlink() or not source.is_file():
            raise VoiceSampleError("Missing or linked original voice dataset clip.")
        info = source.stat()
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= 64 * 1024 * 1024:
            raise VoiceSampleError("Unexpected voice dataset audio size.")
        total += info.st_size
        if total > MAX_BYTES:
            raise VoiceSampleError("Training split exceeds the 2 GiB size limit.")
        paths.append({"path": source, "name": name, "sha256": fingerprint,
                      "seconds": float(seconds), "size": info.st_size,
                      "mtime_ns": info.st_mtime_ns})
    return root, paths


def _hash(path, stop):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while True:
            if stop.is_set():
                raise VoiceSampleError("Voice training split cancelled.")
            block = stream.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def training_split_plan(dataset, *, stop=None):
    """Read and verify all inputs; report the planned split without copying."""
    stop = stop if stop is not None else threading.Event()
    root, clips = _read_dataset(dataset)
    hashes = set()
    for clip in clips:
        if _hash(clip["path"], stop) != clip["sha256"]:
            raise VoiceSampleError("Voice training dataset checksum mismatch.")
        if clip["sha256"] in hashes:
            raise VoiceSampleError("Duplicate voice clips must not appear in a training split.")
        hashes.add(clip["sha256"])
    total = sum(clip["seconds"] for clip in clips)
    # Stable ordering across machines and calls. Never infer singer identity.
    ordered = sorted(clips, key=lambda entry: entry["sha256"])
    count = max(1, min(len(clips) // 4, math.ceil(len(clips) * 0.12)))
    holdout = ordered[:count]
    hold_names = {entry["name"] for entry in holdout}
    training = [entry for entry in clips if entry["name"] not in hold_names]
    held = [entry for entry in clips if entry["name"] in hold_names]
    training_seconds = round(sum(x["seconds"] for x in training), 3)
    holdout_seconds = round(sum(x["seconds"] for x in held), 3)
    return {"schema": 1, "dataset": root, "train": training, "holdout": held,
            "total_seconds": round(total, 3), "training_seconds": training_seconds,
            "holdout_seconds": holdout_seconds,
            "ready_for_ten_minute_training": training_seconds >= MIN_TRAIN_SECONDS,
            "minutes_to_record_for_training": round(max(0, MIN_TRAIN_SECONDS - training_seconds) / 60, 2),
            "model_training_started": False}


def prepare_training_split(dataset, *, consent=False, stop=None):
    """Copy separate train/evaluation audio only after owner's explicit approval."""
    if consent is not True:
        raise VoiceSampleError("Confirm permission to prepare this owner's voice training split.")
    stop = stop if stop is not None else threading.Event()
    plan = training_split_plan(dataset, stop=stop)
    folder = plan["dataset"] / "training-splits"
    if folder.is_symlink() or (folder.exists() and not folder.is_dir()):
        raise VoiceSampleError("Training split folder must be a real directory.")
    if stop.is_set():
        raise VoiceSampleError("Voice training split cancelled.")
    folder.mkdir(mode=0o700, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="split-", dir=folder))
    os.chmod(output, 0o700)
    try:
        receipts = {}
        for label in ("train", "holdout"):
            target_folder = output / label
            target_folder.mkdir(mode=0o700)
            destination = target_folder / "audio"
            destination.mkdir(mode=0o700)
            rows = []
            for sample in plan[label]:
                if stop.is_set():
                    raise VoiceSampleError("Voice training split cancelled.")
                source = sample["path"]
                target = destination / source.name
                flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                descriptor = os.open(source, flags)
                digest = hashlib.sha256()
                with os.fdopen(descriptor, "rb") as inp, target.open("xb") as out:
                    os.chmod(target, 0o600)
                    original = os.fstat(inp.fileno())
                    if (not stat.S_ISREG(original.st_mode) or original.st_size != sample["size"]
                            or original.st_mtime_ns != sample["mtime_ns"]):
                        raise VoiceSampleError("Dataset changed while staging the split.")
                    while True:
                        if stop.is_set():
                            raise VoiceSampleError("Voice training split cancelled.")
                        data = inp.read(1024 * 1024)
                        if not data:
                            break
                        digest.update(data)
                        out.write(data)
                    after = os.fstat(inp.fileno())
                    if (after.st_size != original.st_size or after.st_mtime_ns != original.st_mtime_ns
                            or digest.hexdigest() != sample["sha256"]):
                        raise VoiceSampleError("Voice clip changed during copy.")
                rows.append({"file": "audio/" + target.name, "sha256": digest.hexdigest(),
                             "duration_seconds": sample["seconds"]})
            receipts[label] = rows
        receipt = {
            "schema": 1, "consented_original_dataset": str(plan["dataset"]),
            "owner_consent": True, "training_started": False,
            "voice_identity_qualified": False,
            "train_seconds": plan["training_seconds"],
            "heldout_seconds": plan["holdout_seconds"],
            "ready_for_ten_minute_training": plan["ready_for_ten_minute_training"],
            "training_audio_directory": "train/audio",
            "evaluation_audio_directory": "holdout/audio",
            "never_mix_heldout_audio_into_training": True,
            "staged_copies_not_a_trained_model": True,
            "train": receipts["train"], "holdout": receipts["holdout"],
        }
        with (output / "split.json").open("x", encoding="utf-8") as stream:
            os.chmod(output / "split.json", 0o600)
            json.dump(receipt, stream, indent=2)
        return output
    except BaseException:
        shutil.rmtree(output, ignore_errors=True)
        raise
