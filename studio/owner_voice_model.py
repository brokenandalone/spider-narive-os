"""Private My Voice model pointer, not a model trainer or deserializer.

A saved pointer never establishes identity, model trust, or audio quality.
Owners explicitly register only their self-trained local model files. Deleting
the pointer does not delete weights, voice samples, or RVC training artifacts.
"""
from pathlib import Path
import json
import os
import tempfile

try:
    from .voice_profile import HOME, VoiceSampleError
except ImportError:
    from voice_profile import HOME, VoiceSampleError

REGISTRY = "trained-owner-model.json"
MAX_MODEL_BYTES = 4 * 1024 ** 3
MAX_INDEX_BYTES = 4 * 1024 ** 3


def _asset(path, extension, label, maximum):
    item = Path(path).expanduser()
    if (item.is_symlink() or not item.is_file()
            or item.suffix.lower() != extension):
        raise VoiceSampleError(f"Choose a regular {label} {extension} file, not a symlink.")
    metadata = item.stat()
    if not 0 < metadata.st_size <= maximum:
        raise VoiceSampleError(f"{label} must be nonempty and no larger than 4 GiB.")
    return {"path": str(item.resolve()), "bytes": metadata.st_size,
            "modified_ns": metadata.st_mtime_ns}


def _directory(root):
    folder = Path(root) if root is not None else HOME
    if folder.is_symlink():
        raise VoiceSampleError("Private My Voice folder must not be a symlink.")
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    if folder.is_symlink():
        raise VoiceSampleError("Private My Voice folder must not be a symlink.")
    os.chmod(folder, 0o700)
    return folder


def _entry(root):
    return _directory(root) / REGISTRY


def remember_owner_model(model, index=None, *, consent=False, root=None):
    """Save only paths and file signatures after explicit owner confirmation."""
    if consent is not True:
        raise VoiceSampleError("Explicitly confirm that this is your own trained singing model.")
    trained = _asset(model, ".pth", "trained voice model", MAX_MODEL_BYTES)
    companion = _asset(index, ".index", "voice index", MAX_INDEX_BYTES) if index else None
    directory = _directory(root)
    target = directory / REGISTRY
    if target.is_symlink() or (target.exists() and not target.is_file()):
        raise VoiceSampleError("Refusing an unsafe existing model registry.")
    info = {"schema": 1, "profile": "Justin Therapy", "model": trained,
            "index": companion, "audio_identity_approved": False,
            "voice_training_verified_by_app": False}
    staged = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory,
                                         prefix=".model-", delete=False) as stream:
            staged = Path(stream.name)
            os.chmod(staged, 0o600)
            json.dump(info, stream, indent=2)
        if target.is_symlink():
            raise VoiceSampleError("Refusing to replace a linked model registry.")
        os.replace(staged, target)
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)
    return info


def load_owner_model(*, root=None):
    """Return valid pointers only; never load or execute a PyTorch model."""
    target = _entry(root)
    if target.is_symlink() or not target.is_file():
        return None
    if not 0 < target.stat().st_size <= 16 * 1024:
        return None
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        if data.get("schema") != 1 or data.get("profile") != "Justin Therapy":
            return None
        model = data["model"]
        current = _asset(model["path"], ".pth", "trained voice model", MAX_MODEL_BYTES)
        if current != model:
            return None
        index = data.get("index")
        if index is not None and _asset(index["path"], ".index", "voice index", MAX_INDEX_BYTES) != index:
            return None
        return {"model": current["path"], "index": index["path"] if index else "",
                "voice_training_verified_by_app": False}
    except (OSError, KeyError, ValueError, TypeError, UnicodeError):
        return None


def forget_owner_model(*, root=None):
    """Forget the app's pointer only; never delete audio or model weights."""
    target = _entry(root)
    if target.is_symlink():
        raise VoiceSampleError("Refusing to unlink a model registry symlink.")
    if target.exists() and not target.is_file():
        raise VoiceSampleError("The model registry is not a regular file.")
    target.unlink(missing_ok=True)
