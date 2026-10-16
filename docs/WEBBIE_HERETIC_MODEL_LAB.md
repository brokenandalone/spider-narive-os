# Webbie + Heretic: integrated optional local model lab

Status: **development source in the Spider OS rebuild branch only**. Heretic has NOT been installed or run on the owner's PC, and no resident Webbie model, voice, permission, service, or native bay has been replaced.

## Official dependency and what it actually does

Official project: https://github.com/p-e-w/heretic . License: AGPL-3.0-or-later. Heretic is a model-alteration research program that reduces refusal behavior. It is not an AI assistant, memory system, automatic intelligence improvement or computer-control service. The upstream package is installed optionally in a separate private Python venv, not vendored into Spider OS.

Heretic expects a Hugging Face Transformer model. The owner's optimized local Ollama qwen3:8b is a different format and is NOT a direct Heretic training input. Derived models require evaluation and a separately reviewed conversion/import process before they could ever be used in Ollama. The current resident model is NOT swapped by this feature.

## Native features added

- Existing Webbie Cognitive Center contains a Heretic model lab button and owner-confirmed interactive experiment dialog. No additional dock, launcher, daemon or service was created.
- Existing Webbie agent responds to the exact read-only command 'Heretic lab status'. It cannot start Heretic through a spoken command, model output, website or scheduled task.
- Lab reports RAM, disk, isolated Heretic executable and Konsole availability without downloads or model changes.
- Fixed allowlisted experimental models: Qwen/Qwen3-0.6B, Qwen/Qwen3-1.7B, Qwen/Qwen3-4B-Instruct-2507. These are real Hugging Face model identifiers.
- Launch uses a fixed argument array in Konsole, requires the explicit GUI Yes button, and keeps the experiment isolated in the owner's Documents/Spider OS/Webbie/Heretic Experiments directory.
- The upstream CLI may download large model weights and offer to upload altered weights; an owner must review any such interactive choice. Stop the experiment with Ctrl+C in the separate Konsole. The global Webbie STOP does NOT manage this separate terminal session; do not imply otherwise.
- Release source inventory includes webbie/brain/heretic_lab.py. The upstream AGPL code and optional heavy Python dependencies are not included in this repository.

## Hardware limitation

The installed PC last reported approximately 15 GiB RAM and CPU-based Qwen3. Heretic requires substantially more memory and disk than normal quantized Ollama inference. The GUI's conservative planning thresholds (not upstream official guarantees) are 8 GiB physical RAM for 0.6B, 16 GiB for 1.7B and 32 GiB for the 4B experiment, plus 15 GiB free disk. The smallest option is the sensible first research test for this PC. A CPU experiment can still be slow, fail, or exhaust resources; none was attempted.

## Optional, explicitly owner-run setup

From a separate CLEAN checkout of rebuild/spider-os-installed-truth-20261016 (do not pull into the dirty review clone), run:

    bash tools/setup_heretic_lab.sh --check

That is read-only. If the owner explicitly wants the large, optional dependency install, run:

    bash tools/setup_heretic_lab.sh --install

It requests the typed confirmation INSTALL HERETIC, checks for disk space, and installs the official heretic-llm package into ~/.local/share/spider-os/heretic-venv via a Python virtual environment. It does not install services or switch models. Exact PyPI version and Python/PyTorch compatibility are not pinned or established, so this is not yet a reproducible production package.

## Making Webbie the integrated assistant envisioned

1. Keep one source of truth for her resident AI V2, memory, Natasha, wake/voice system and owner speaker authorization.
2. Integrate real Author, Studio, Study, Kali, Media/Nova, Forage and Art Lab native tools rather than new fake launchers.
3. Consolidate existing research, curiosity, proactive and learning services instead of making duplicate research queues.
4. Deliver verified multistep actions via scoped native authorization with STOP, truthful action receipts and rollback, never free-form model/root shell.
5. Keep Heretic as optional locally supervised model research. A model that refuses less is not automatically more accurate, smarter or safer; benchmark thoroughly before any opt-in production use.
6. Reconcile remaining owner-installed code and pass hosted CI plus on-PC end-to-end voice/desktop tests before any single daily release.

**No installation of the rebuilt system is authorized or performed by this branch.**
