# Spider Audio Studio Wave 10: recording library audit (source only)

The existing Spider Audio Studio now has a native **Recording Library Audit** tab.
The owner explicitly chooses a directory and receives a read-only inventory of
WAV sample rate, channels, bit depth, duration and compatibility with current
44.1/48 kHz 16/24-bit mono/stereo recording tools. Invalid files are marked,
not repaired. Symlinked WAVs and directories are ignored, scanning is bounded
to 2,000 WAVs and five directory levels, and no playback, microphone, AI service,
radio service, or catalog/tag mutation is initiated.

The results appear as readable JSON in the bay so the owner can copy them.
This is a source-only feature in draft PR #117, not an installed upgrade. Local
hardware tests, owner file-drift reconciliation and the existing safety-gated
install process are still required before any deployment.
