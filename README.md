# Spider Narive OS

A clean starting point for building a small native x86_64 operating system.

> This repository is currently a development scaffold. It is not yet a complete operating system.

## Goals

- Boot reliably in QEMU on x86_64
- Keep the kernel, boot files, drivers, filesystem, and userspace separated
- Build repeatably in GitHub Actions and on a Linux development machine
- Document design decisions as the project grows

## Repository layout

- `src/bootloader/` — bootloader configuration and boot-time files
- `src/kernel/` — kernel entry point and core code
- `src/drivers/` — hardware drivers
- `src/filesystem/` — filesystem work
- `src/userspace/` — future user programs
- `scripts/` — build and emulator helpers
- `docs/` — architecture and development notes
- `tests/` — host-side and integration tests

## Requirements

A Linux environment with `make`, an x86_64 ELF cross-compiler, GNU binutils, QEMU, GRUB tools, and `xorriso`.

The build scripts use `x86_64-elf-gcc` and `x86_64-elf-ld` so that host-system libraries are not accidentally linked into the kernel.

## Build and run

```sh
./scripts/build.sh
./scripts/run.sh
```

The first milestone displays a message in the VGA text buffer and halts safely. It is intentionally small; memory management, interrupts, drivers, processes, and userspace will be added incrementally.

## License

MIT. See `LICENSE`.
