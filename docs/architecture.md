# Architecture

## Initial target

Spider Narive OS starts as a freestanding x86_64 kernel loaded by GRUB using the Multiboot specification. The first milestone is deliberately minimal: enter 32-bit protected mode, establish a stack, call C code, write to VGA text memory, and halt.

## Planned layers

1. Boot protocol and early CPU setup
2. Kernel initialization and physical memory management
3. Interrupt controller, timer, keyboard, and serial drivers
4. Virtual memory and process isolation
5. Filesystem and storage drivers
6. System-call boundary and userspace
7. User interface and system services

Every layer should have a documented interface and a QEMU-testable milestone before the next layer is introduced.
