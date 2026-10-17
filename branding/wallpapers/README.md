# The Web wallpaper collection

The collection includes 59 byte-distinct artwork files recovered from the earlier expanded kit, today’s seven-workspace kit, matching panels and additional named designs. Original files are copied without image conversion. Historical color variants and concept artwork remain optional entries; the purple collection is the current visual direction.

The Web’s Wallpaper selector previews each entry and saves one choice per workspace under the user’s XDG config directory. Existing workspace backgrounds remain the defaults and can be restored with **Original workspace background**. Webbie, Deep Forage and Communocations use their new full artwork when no original background exists. Forage and Deep Forage now have separate choices.

`collection.json` records names, categories and SHA-256 checksums. Byte-identical duplicate uploads are stored once. Similar PNG/JPEG exports are retained because their files differ. All collection assets are included by the existing full-source installer/build copy; no download is needed while selecting a wallpaper.

Source integration does not update an already installed desktop. Deploy this payload through the existing staged upgrade process, preserving local configuration and owner-modified files. This change does not alter the session locker or boot splash.
