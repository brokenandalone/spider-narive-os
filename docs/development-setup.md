# Development setup

## Toolchain

Install or build an x86_64 ELF cross-toolchain exposing:

- `x86_64-elf-gcc`
- `x86_64-elf-ld`
- `x86_64-elf-objcopy`

Also install `grub-mkrescue`, `xorriso`, `qemu-system-x86_64`, and GNU `make`.

## Local workflow

1. Clone the repository.
2. Confirm the tools are available with `command -v x86_64-elf-gcc`.
3. Run `./scripts/build.sh`.
4. Run `./scripts/run.sh` to boot the image in QEMU.
5. Keep generated files in `build/`; they are ignored by Git.

Do not use `sudo` for the build unless your toolchain or system requires it. The scripts fail early when required tools are missing.
