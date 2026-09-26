#include <stdint.h>

static volatile uint16_t *const vga = (uint16_t *)0xB8000;

void kernel_main(uint32_t multiboot_magic, uint32_t multiboot_info) {
    (void)multiboot_info;
    const char *message = multiboot_magic == 0x2BADB002
        ? "Spider Narive OS booted."
        : "Spider Narive OS: invalid boot signature.";

    for (uint32_t i = 0; message[i] != '\0'; ++i) {
        vga[i] = (uint16_t)message[i] | (uint16_t)0x0F00;
    }
}
