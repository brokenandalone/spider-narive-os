# Webbie local webcam vision: permission-first foundation

This feature is **source built, not installed or enabled on the owner's PC**.
It is deliberately separate from the floating portrait/OneDrive add-on in PR #21.

## Source behavior

- Importing Webbie, opening a workspace, launching Spider OS, or running
  `status` never opens the webcam.
- Only an explicit **Look at room once** button in the native Webbie workspace,
  followed by a confirmation prompt, is permitted to activate the camera.
- The workspace displays **CAMERA ACTIVE** while acquiring the single frame,
  then switches to **CAMERA OFF** before sending the frame to the locally
  installed vision model. No persistent capture, hidden background monitoring,
  file recording, cloud account access or automatic document editing.
- Requires `ffmpeg`, a readable `/dev/videoN` camera device, and an already
  installed Ollama model with vision input support. The code does not download
  models or bypass Linux camera permissions.
- The captured frame stays in memory, is resized to 640px width, and goes
  only to loopback `http://127.0.0.1:11434/api/generate` with proxies disabled.
- A single snapshot cannot establish ongoing room awareness. Continuous
  monitoring, persistent video, person recognition, and desktop/screen capture
  remain **off** and need independent approval, visible indicators, stop
  controls, and performance/privacy qualification.

Source examples, not yet installed:

```bash
python3 webbie/vision/local_camera.py status
python3 webbie/vision/local_camera.py describe --device /dev/video0 --model gemma3:4b
```

**Never run the second example automatically or from a systemd service.**
The user must explicitly initiate it on the installed machine.

## Installed-PC acceptance (later)

1. Establish which camera device is the intended webcam.
2. Verify the user's chosen local multimodal Ollama model is installed
   and capable of consuming images. Text-only Qwen3:4b is not enough.
3. Check that no webcam indicator appears on log-in or Webbie tab open.
4. Click Look at room once, deny permission; ensure no capture.
5. Explicitly approve one frame and check the visible indicator.
6. Check camera access is released after the snapshot and no image file
   or background upload appears.
7. Test fallback for unplugged camera, failed capture and model unavailable.
8. Ask before building persistent room or screen awareness.

This work should be integrated into a reviewed later Webbie/Author source
update. Do not replace the owner-customized resident voice service with an
unqualified copy from GitHub.
