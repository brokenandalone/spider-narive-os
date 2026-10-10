#!/usr/bin/env python3
"""Full Kali desktop gateway for Spider OS Kali Bay.

Controls ONLY the owner-defined 'spider-kali-desktop' libvirt VM.
No VM is installed, created, downloaded or enabled by this source file.
No arbitrary domain name, command, URL, guest shell or network configuration
may be supplied through Webbie or the Kali UI.
"""
import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

VM_NAME = "spider-kali-desktop"
LIBVIRT_URI = "qemu:///system"
TIMEOUT = 10


def tool(name):
    return shutil.which(name)


def _run(argv, timeout=TIMEOUT):
    return subprocess.run(
        argv, capture_output=True, text=True, check=False, timeout=timeout,
    )


def inspect_vm():
    """Read-only state, including common host readiness hints."""
    result = {
        "name": VM_NAME,
        "uri": LIBVIRT_URI,
        "state": "unavailable",
        "configured": False,
        "virt_manager": bool(tool("virt-manager")),
        "virt_viewer": bool(tool("virt-viewer")),
        "kvm_device": Path("/dev/kvm").exists(),
        "reason": "",
    }
    virsh = tool("virsh")
    if not virsh:
        result["reason"] = "libvirt tools are not installed."
        return result
    try:
        listing = _run([virsh, "-c", LIBVIRT_URI, "list", "--all", "--name"])
    except (OSError, subprocess.TimeoutExpired):
        result["reason"] = "Unable to query libvirt without changing the host."
        return result
    if listing.returncode:
        result["reason"] = (
            "Cannot access the system libvirt connection; check service and "
            "user permissions without enabling root access for Webbie."
        )
        return result
    names = {item.strip() for item in listing.stdout.splitlines() if item.strip()}
    if VM_NAME not in names:
        result["state"] = "not-configured"
        result["reason"] = "Create a Kali Linux VM named spider-kali-desktop in virt-manager."
        return result
    result["configured"] = True
    try:
        state = _run([virsh, "-c", LIBVIRT_URI, "domstate", VM_NAME])
    except (OSError, subprocess.TimeoutExpired):
        result["reason"] = "Unable to inspect the defined Kali virtual machine."
        return result
    if state.returncode:
        result["reason"] = "libvirt could not retrieve the Kali virtual machine's state."
        return result
    name = state.stdout.strip().casefold()
    result["state"] = {
        "running": "running",
        "shut off": "stopped",
        "paused": "paused",
    }.get(name, "unknown")
    return result


def _launch(argv):
    subprocess.Popen(
        argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True,
    )


def open_manager():
    executable = tool("virt-manager")
    if not executable:
        return False, "Install virt-manager on Spider OS after host compatibility checks."
    _launch([executable, "--connect", LIBVIRT_URI])
    return True, "Opened the graphical virtual machine manager."


def open_console():
    vm = inspect_vm()
    if vm["state"] != "running":
        return False, "Kali desktop is not running. Open the VM manager to prepare or start it."
    viewer = tool("virt-viewer")
    if not viewer:
        return False, "virt-viewer is missing; open the console through virt-manager instead."
    _launch([viewer, "--connect", LIBVIRT_URI, VM_NAME])
    return True, "Opened the existing Kali Linux guest desktop console."


def start_desktop():
    """Explicit owner UI action only. Never called on normal Webbie conversation."""
    vm = inspect_vm()
    if vm["state"] != "stopped":
        return False, "Kali VM is not in a stopped, ready-to-start state."
    virsh = tool("virsh")
    try:
        proc = _run([virsh, "-c", LIBVIRT_URI, "start", VM_NAME], timeout=25)
    except (OSError, subprocess.TimeoutExpired):
        return False, "Could not complete the requested Kali VM start."
    if proc.returncode:
        return False, "Kali VM start was denied or unsuccessful. Review libvirt access in virt-manager."
    return True, "Kali VM start succeeded. Open its desktop console to use Kali."


def main(argv=None):
    parser = argparse.ArgumentParser(description="Spider OS fixed Kali desktop VM gateway")
    parser.add_argument("action", choices=["status", "manager", "console", "start"])
    args = parser.parse_args(argv)
    if args.action == "status":
        print(json.dumps(inspect_vm(), sort_keys=True))
        return 0
    try:
        success, message = {
            "manager": open_manager,
            "console": open_console,
            "start": start_desktop,
        }[args.action]()
    except OSError:
        success, message = False, "The requested Kali desktop action could not start."
    print(message)
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
