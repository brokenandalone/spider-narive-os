Run source regression checks with `python3 -m unittest discover -s tests -p 'test_*.py'`.

The Actions workflow runs `sudo bash tests/qemu-install.sh build/Spider_OS_24.04.5_amd64.iso`
after ISO verification. The harness creates its own disposable QCOW2 disk and uses
NoCloud autoinstall data. It exposes no host disks, installs through the existing
Ubuntu bootstrap/Subiquity backend, powers off, and then boots the installed disk
without the ISO. Missing success markers or timeout fail the workflow. Logs remain
in `build/install-test/`. The seed and test service are never put in the released ISO.
