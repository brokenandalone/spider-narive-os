#!/usr/bin/env python3
"""Spider OS unmounted /dev/sda1 boot bridge.

READ-ONLY hardware audit, plus an OFFLINE candidate GRUB test menu.
No mount, dd, mkfs, grub-install, update-grub, or live-disk writes.
Do not use a prepared candidate on the real boot partition without
independent backups and an approved boot/rollback procedure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

SPIDER_UUID = "b8b48e84-c748-4741-9b94-a2f5bab50ca6"
ROOT_DEVICE = "/dev/mapper/kali--vg-root"
EFI_STUB = Path("/boot/efi/EFI/SpiderOS/grub.cfg")
GRUB_PATH = "/grub/grub.cfg"
VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+~-]*$")
BOOT_ENTRY = re.compile(r"^menuentry 'Spider OS GNU/Linux'[^\n]*\{", re.M)
KERNEL = re.compile(r"^[ \t]*linux[ \t]+/vmlinuz-([^ \t]+)[ \t]+([^\n]+)$", re.M)
INITRD = re.compile(r"^[ \t]*initrd[ \t]+/initrd\.img-([^ \t\n]+)[ \t]*$", re.M)


def run(*argv: str) -> str:
    cp = subprocess.run(argv, text=True, capture_output=True, check=False)
    if cp.returncode:
        raise RuntimeError(f"{argv[0]} failed: {cp.stderr.strip()[:250]}")
    return cp.stdout


def debugfs(device: str, command: str) -> str:
    # debugfs is read-only by default; NEVER pass -w.
    cp = subprocess.run(["debugfs", "-R", command, device],
                        text=True, capture_output=True, check=False)
    result = cp.stdout + "\n" + cp.stderr
    if cp.returncode or re.search(r"File not found|ext2_lookup|Cannot open|Bad magic|Filesystem not open", result, re.I):
        raise RuntimeError(f"debugfs {command!r}: {result.strip()[:250]}")
    return cp.stdout


def original_entry(cfg: str) -> tuple[str, str]:
    match = BOOT_ENTRY.search(cfg)
    if not match:
        raise ValueError("Exact active Spider OS primary menuentry not found")
    # Stop at the next top-level closing brace, not a grub variable expansion.
    end = cfg.find("\n}", match.end())
    if end == -1:
        raise ValueError("Primary menuentry has no top-level closing brace")
    block = cfg[match.start():end + 2]
    kernel = KERNEL.findall(block)
    initrd = INITRD.findall(block)
    if len(kernel) != 1 or len(initrd) != 1:
        raise ValueError("Primary boot entry must have one kernel and one initrd")
    old_ver, args = kernel[0]
    if initrd[0] != old_ver or not VERSION.fullmatch(old_ver):
        raise ValueError("Kernel and initramfs versions differ")
    if f"root={ROOT_DEVICE}" not in args.split():
        raise ValueError("Unexpected Linux root device in boot entry")
    if SPIDER_UUID not in block:
        raise ValueError("Primary menuentry does not select the sda1 UUID")
    return old_ver, args


def stat_size(device: str, path: str) -> int:
    result = debugfs(device, f"stat {path}")
    m = re.search(r"\bSize:\s*(\d+)\b", result)
    if not m or "Type: regular" not in result:
        raise RuntimeError(f"Expected regular boot file missing at {path}")
    return int(m.group(1))


def filesystem_free(device: str) -> int:
    result = debugfs(device, "stats")
    count = re.search(r"^Free blocks:\s*(\d+)", result, re.M)
    size = re.search(r"^Block size:\s*(\d+)", result, re.M)
    if not count or not size:
        raise RuntimeError("Cannot read sda1 filesystem free blocks")
    return int(count.group(1)) * int(size.group(1))


def inspect(device: str, stub: Path, root_boot: Path) -> tuple[str, str, str, int]:
    reported = run("blkid", "-s", "UUID", "-o", "value", device).strip()
    if reported != SPIDER_UUID:
        raise ValueError(f"Device UUID {reported!r} is not expected SpiderOS sda1 UUID")
    text = stub.read_text()
    if "search.fs_uuid " + SPIDER_UUID not in text or "configfile $prefix/grub.cfg" not in text:
        raise ValueError("EFI SpiderOS stub does not point to the known sda1 config")
    # findmnt status 1 is expected when the active boot filesystem is unmounted.
    mount_check = subprocess.run(
        ["findmnt", "-rn", "--source", device, "-o", "TARGET"],
        text=True, capture_output=True, check=False,
    )
    if mount_check.returncode not in (0, 1):
        raise RuntimeError(f"Cannot inspect boot mount status: {mount_check.stderr[:200]}")
    if mount_check.stdout.strip():
        raise ValueError(f"Boot partition unexpectedly mounted at {mount_check.stdout.strip()}")
    cfg = debugfs(device, f"cat {GRUB_PATH}")
    old, args = original_entry(cfg)
    for basename in (f"vmlinuz-{old}", f"initrd.img-{old}"):
        actual = stat_size(device, "/" + basename)
        normal = root_boot / basename
        if not normal.is_file():
            raise ValueError(f"Main root kernel file missing: {normal}")
        if actual != normal.stat().st_size:
            raise ValueError(f"SIZE MISMATCH: sda1 {basename}: {actual}, main boot: {normal.stat().st_size}")
        print(f"FOUND ON SDA1 AND ROOT: {basename} ({actual:,} bytes)")
    free = filesystem_free(device)
    print(f"FREE SDA1: {free // (1024 * 1024)} MiB")
    print(f"CURRENT WORKING DEFAULT: {old}")
    print("SIZES MATCH, but identical bytes and a successful boot are not established by this audit.")
    print("HOLD UPGRADE: sda1 is unmounted; normal Ubuntu kernel updates will not automatically stage here.")
    return cfg, old, args, free


def make_candidate(cfg: str, new_version: str, new_kernel_bytes: int,
                   new_initrd_bytes: int, free_bytes: int) -> str:
    if not VERSION.fullmatch(new_version):
        raise ValueError("Invalid kernel version")
    current, args = original_entry(cfg)
    if new_version == current:
        raise ValueError("Candidate must be a different kernel; do not duplicate the default")
    if f"/vmlinuz-{new_version}" in cfg or f"/initrd.img-{new_version}" in cfg:
        raise ValueError("This candidate kernel is already referenced in the active GRUB config")
    required = new_kernel_bytes + new_initrd_bytes + 64 * 1024 * 1024
    if free_bytes < required:
        raise ValueError(f"Insufficient sda1 free space: have {free_bytes}, require {required}")
    # Do not depend on gfxmode() running for this standalone menuentry.
    args = re.sub(r"(?<!\S)\$vt_handoff(?!\S)", "", args).strip()
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", new_version)
    addition = (
        "\n# SPIDER_OS_TEST_ENTRY: preserve the original default/recovery entries.\n"
        f"menuentry 'Spider OS TEST kernel {new_version} (manual selection only)' "
        f"--class spider --id spider_test_{safe_id} {{\n"
        "    insmod part_gpt\n"
        "    insmod ext2\n"
        f"    search --no-floppy --fs-uuid --set=root {SPIDER_UUID}\n"
        f"    linux /vmlinuz-{new_version} {args}\n"
        f"    initrd /initrd.img-{new_version}\n"
        "}\n"
    )
    marker = "### END /etc/grub.d/10_linux ###"
    if cfg.count(marker) != 1:
        raise ValueError("Unexpected GRUB structure; cannot append safe test entry")
    result = cfg.replace(marker, marker + "\n" + addition)
    if original_entry(result) != original_entry(cfg):
        raise AssertionError("Default entry was modified")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["audit", "prepare"])
    parser.add_argument("--device", default="/dev/sda1")
    parser.add_argument("--efi-stub", type=Path, default=EFI_STUB)
    parser.add_argument("--root-boot", type=Path, default=Path("/boot"))
    parser.add_argument("--version", help="new installed kernel version; prepare only")
    parser.add_argument("--output", type=Path, help="new offline directory; prepare only")
    args = parser.parse_args()
    if args.mode == "prepare" and (not args.version or not args.output):
        parser.error("prepare requires --version and --output")
    try:
        cfg, old, old_args, free = inspect(args.device, args.efi_stub, args.root_boot)
        if args.mode == "audit":
            return 0
        new_kernel = args.root_boot / f"vmlinuz-{args.version}"
        new_initrd = args.root_boot / f"initrd.img-{args.version}"
        for item in (new_kernel, new_initrd):
            if not item.is_file() or item.stat().st_size == 0:
                raise ValueError(f"Required installed new kernel asset missing: {item}")
        candidate = make_candidate(cfg, args.version, new_kernel.stat().st_size,
                                   new_initrd.stat().st_size, free)
        destination = args.output.absolute()
        if destination == Path("/") or str(destination).startswith("/boot/") or destination == Path("/boot"):
            raise ValueError("Offline candidate must not be placed under /boot")
        destination.mkdir(parents=True, mode=0o700, exist_ok=False)
        os.chmod(destination, 0o700)
        (destination / "grub.cfg.candidate").write_text(candidate)
        details = {
            "mode": "OFFLINE PREVIEW ONLY - NOT INSTALLED",
            "existing_version": old,
            "candidate_version": args.version,
            "sda1_uuid": SPIDER_UUID,
            "free_bytes": free,
            "kernel": {"path": str(new_kernel), "sha256": sha256(new_kernel)},
            "initrd": {"path": str(new_initrd), "sha256": sha256(new_initrd)},
            "original_grub_sha256": hashlib.sha256(cfg.encode()).hexdigest(),
        }
        (destination / "manifest.json").write_text(json.dumps(details, indent=2) + "\n")
        print(f"Candidate created at {destination}; no boot partition was changed.")
        print("DO NOT copy these files to /dev/sda1 until independently backed up, reviewed and recovery-tested.")
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 2


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as infile:
        for chunk in iter(lambda: infile.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
