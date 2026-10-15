#!/usr/bin/env python3
"""Expand the exact reviewed Workspace MAX v4 engines as readable native source.

GitHub source staging only. No install, network fetch, system service, or
execution of untrusted file contents. Every module is checksum-verified.
"""
import ast
import base64
import hashlib
import io
import lzma
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "tools/native_max_payload/reviewed_max_v4.b85"
B85_SHA256 = "08376ca3d0ddc9fa96f989a1aa81c1c895625fc496ef7d15a286dfef70e7b54d"
TAR_SHA256 = "968942c05f2efc52364e379549602121ddad090447f4b6efdbfdb2bbc30d428e"
MAX_EXTRA_SHA = {
    "max_gui.py": "f343538072e9ecba1c0fa44b00b70fadd8a205845afe8c97154943b5d2077c7d",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def expected_modules():
    source = (ROOT / "the-web/shell/workspace_max_native.py").read_text("utf-8")
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "V4_BLOB_SHA256"
            for target in node.targets
        ):
            mapping = ast.literal_eval(node.value)
            return dict(mapping, **MAX_EXTRA_SHA)
    raise ValueError("No reviewed MAX source-hash registry found")


def main():
    if BUNDLE.is_symlink():
        raise ValueError("Refusing a source-bundle symlink")
    encoded = BUNDLE.read_text(encoding="ascii").strip()
    if sha(encoded.encode("ascii")) != B85_SHA256:
        raise ValueError("Wrong reviewed MAX source-bundle checksum")
    compressed = base64.b85decode(encoded)
    unpacked = lzma.decompress(compressed, memlimit=40 * 1024 * 1024)
    if len(unpacked) > 200000 or sha(unpacked) != TAR_SHA256:
        raise ValueError("Reviewed tar source checksum/size mismatch")
    manifest = expected_modules()
    extracted = {}
    with tarfile.open(fileobj=io.BytesIO(unpacked), mode="r:") as archive:
        for item in archive:
            if not item.isfile() or item.size > 100000:
                raise ValueError("Unexpected source entry")
            path = item.name
            if not path.startswith("spider_monster/"):
                raise ValueError("Source archive escape attempt")
            name = path[len("spider_monster/"):]
            if name not in manifest or name in extracted or "/" in name:
                raise ValueError("Unexpected/duplicate source file")
            blob = archive.extractfile(item).read()
            if sha(blob) != manifest[name]:
                raise ValueError("Source module checksum mismatch: " + name)
            compile(blob, path, "exec")
            extracted[name] = blob
    if extracted.keys() != manifest.keys():
        raise ValueError("Required native source modules are missing")
    action_count = 0
    for name, blob in extracted.items():
        if not name.startswith("max_") or name in (
            "max_core.py", "max_catalog.py", "max_gui.py", "max_board.py"
        ):
            continue
        tree = ast.parse(blob)
        found = [
            node.value for node in tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "ACTIONS"
                    for target in node.targets)
        ]
        if len(found) != 1:
            raise ValueError("MAX operations missing for " + name)
        action_count += len(ast.literal_eval(found[0]))
    if action_count != 137:
        raise ValueError("Expected exactly 137 original advanced operations")
    output = ROOT / "spider_max_source/spider_monster"
    if output.is_symlink():
        raise ValueError("Refusing symlinked output directory")
    if output.exists() and not output.is_dir():
        raise ValueError("Native source target is not a directory")
    for name, blob in extracted.items():
        target = output / name
        if target.is_symlink() or (target.exists() and target.read_bytes() != blob):
            raise ValueError("Existing file differs; refusing overwrite: " + name)
    output.mkdir(parents=True, exist_ok=True)
    for name, blob in sorted(extracted.items()):
        target = output / name
        if not target.exists():
            target.write_bytes(blob)
    print("NATIVE SOURCE MATERIALIZED:", len(extracted),
          "reviewed Python modules;", action_count, "MAX operations.")
    print("Git source changed only. No installed Spider OS component modified.")


if __name__ == "__main__":
    main()
