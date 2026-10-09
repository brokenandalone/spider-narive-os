# Webbie camera and optional familiar-face profiles

This source batch extends The Web's existing shared Webbie panel. **It does not replace the existing Whisper/ALSA/PipeWire microphone listener or any voice-agent service.** If the webcam microphone is already working, keep its configuration unchanged.

## Runtime prerequisites

- A compatible Video4Linux2 webcam, exposed under `/dev/videoN`.
- The distro package `ffmpeg` for in-memory single-frame capture. The installer checks this instead of silently installing dependencies.
- A locally running Ollama service and a **vision-capable** model with the tag `gemma3:4b` (or adjust the local vision model intentionally). Text-only Qwen3 models cannot interpret image pixels.
- **Optional**: a compatible installed Python `face_recognition` package and its local model files. The app remains usable with zero face profiles and with the package absent. Do not install heavyweight facial components automatically.

## User workflow

1. Open the Webbie side panel in The Web. Her existing webcam microphone remains unchanged.
2. Choose `/dev/videoN`, click **Turn camera on**.
3. Click **Look now** for a one-time webcam image and local scene description, or **Watch room** for a new local scene check about every 45 seconds. The label states when the camera is active. No images or video are recorded to disk by this feature.
4. **Both familiar-face profiles start empty.** The two fixed slots are **Cory** and **Shayna**. Each individual can personally agree to **Enroll face** when ready, independently of the other. Enrollment captures a voluntary local image, extracts numerical face features and discards the image. More samples can be added later, up to five per person.
5. **Forget face** wipes the chosen person's saved descriptors. Profiles persist only in the owner's local `~/.local/share/spider-os/webbie-face-profiles.json` file, mode 0600; they are never checked into the source repository.
6. Sleeping or turning off Webbie's camera disables new frame checks and drops in-memory scene and face-match observations. Wake-up requires a fresh camera opt-in. The visually sleeping portrait can remain on-screen without camera access.
7. Once the camera is enabled, ask **Hey Webbie, what do you see?** A spoken request gets one fresh local description. It works without either facial profile. It does not modify Whisper's microphone settings.\n8. The existing desktop Webbie chat can use a recent, clearly labeled **untrusted** room description and a **probabilistic** face-match cue only when the user explicitly sends a message. It never includes or exposes raw image data in text requests.

## Limits and safety

- **Face similarity is not proof of identity.** Unknown or ambiguous faces remain unrecognized. No general-purpose surveillance, stranger identification, profiling, background uploads or remote access is included.
- **Enrollment is not mandatory.** Neither profile blocks ordinary conversation, webcam room descriptions, audio or any other bay.
- **This does not implement secure voice speaker verification.** A working microphone and Whisper transcription are not, by themselves, proof of who spoke. Existing speaker authorization must be independently tested before trusting sensitive voice commands.
- **Voice-to-vision integration:** With the camera explicitly turned on, say **Hey Webbie, what do you see?** or **Hey Webbie, look around.** The existing resident wake-word agent sends a narrow LOOK request to a private local UNIX socket owned by The Web. The UI captures a fresh image, analyzes it through local Ollama, and returns only a short description for the voice agent to speak. With the camera off or Webbie asleep, the local socket does not listen. The interface never automatically opens the camera from a voice request.
- Camera capture supports a selection of real V4L2 devices. The physical webcam and optional face-matching package require installed-machine validation. GitHub tests use synthetic frames and disposable profiles.
- This branch is intended as a targeted extension of the Author/Webbie branch, not a desktop installer rerun.
