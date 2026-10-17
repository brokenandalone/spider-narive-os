"""Fail-closed, local-only RVC Gradio UI patch for a user-owned checkout.

The upstream RVC WebUI listens on 0.0.0.0 by default. This copies the exact
known source to a new user-local file, patches its Gradio launch bindings,
and leaves the original, any installed services and user models untouched.
"""
from pathlib import Path
import os
import tempfile


class UnsafeRVCVersion(ValueError):
    pass


PUBLIC_BIND = 'server_name="0.0.0.0"'
LOCAL_BIND = 'server_name="127.0.0.1"'
PUBLIC_PROBE = 'host="0.0.0.0"'
LOCAL_PROBE = 'host="127.0.0.1"'
PUBLIC_SHARE = ".launch(share=True)"
LOCAL_SHARE = '.launch(share=False, server_name="127.0.0.1")'


def build_local_ui(source_text):
    if not isinstance(source_text, str):
        raise UnsafeRVCVersion("RVC's original WebUI source could not be read.")
    if (source_text.count(PUBLIC_BIND) != 1
            or source_text.count(PUBLIC_PROBE) != 1
            or source_text.count(PUBLIC_SHARE) != 1):
        raise UnsafeRVCVersion("Unknown RVC WebUI release; refusing to expose a training server.")
    patched = source_text.replace(PUBLIC_BIND, LOCAL_BIND, 1)
    patched = patched.replace(PUBLIC_PROBE, LOCAL_PROBE, 1)
    patched = patched.replace(PUBLIC_SHARE, LOCAL_SHARE, 1)
    if "0.0.0.0" in patched or "share=True" in patched:
        raise UnsafeRVCVersion("RVC WebUI still has an untrusted public bind.")
    return patched


def stage_local_ui(source, target):
    source, target = Path(source), Path(target)
    if source.is_symlink() or not source.is_file() or target.is_symlink():
        raise UnsafeRVCVersion("RVC source and target must be regular, non-symlink files.")
    if source.resolve() == target.resolve():
        raise UnsafeRVCVersion("Never rewrite the original RVC source.")
    expected = build_local_ui(source.read_text(encoding="utf-8"))
    if target.exists():
        if target.read_text(encoding="utf-8") != expected:
            raise UnsafeRVCVersion("The previous local training UI was modified; preserve it for review.")
        return target
    if target.parent.is_symlink() or not target.parent.is_dir():
        raise UnsafeRVCVersion("Choose an existing regular folder in the RVC checkout.")
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent,
                                      prefix=".spider-rvc-ui-", delete=False) as stream:
        staged = Path(stream.name)
        os.chmod(staged, 0o600)
        stream.write(expected)
    try:
        if target.exists():
            raise UnsafeRVCVersion("Local training script appeared during preparation.")
        os.link(staged, target)  # exclusive creation: never replace an existing script
    finally:
        staged.unlink(missing_ok=True)
    return target


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Prepare a loopback-only copy of a known RVC WebUI.")
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    try:
        print(stage_local_ui(args.source, args.destination))
    except (OSError, UnicodeError, UnsafeRVCVersion) as exc:
        parser.exit(2, str(exc) + "\n")
