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

## Persistent everyday brain: integrated in the native Webbie Cognitive Center

Owner's intent: Heretic's *finished model behavior* should be available in every Webbie conversation, not just a standalone training panel. The real resident `webbie/brain/brain.py` now checks `resident_model_choice.read_choice()` on **each normal model turn**, before the original `webbie/config/default.json` model. The choice is owner-only and stored at `~/.config/spider-os/webbie-brain-choice.json` with 0600 permissions, without modifying root-owned Spider OS files. Restarting Webbie or the computer does not reset it.

Open the **existing Webbie Cognitive Center > My everyday AI brain** or, in the Heretic panel, **Use installed model as Webbie's everyday brain**. Select a model that is already present in local Ollama and approve it once. Existing Natasha speech, Webbie long-term memory, offline/online modes, and native tool permissions continue through the same agent. Choose **Use original Qwen3 brain** to roll back the preference; this does not delete any model.

A Hugging Face Heretic weight folder is not automatically an Ollama model. First convert/quantize it into a compatible local Ollama model, test its quality on the actual computer, and ensure it appears in the local `/api/tags` inventory. No model import, benchmark, replacement, download or training was performed by this GitHub commit. The selector does not automatically remove refusals from existing Qwen3 model weights, nor does it give the model more OS permissions. Emergency fallback intentionally remains the original `qwen3:8b` when the full brain fails.

For CPU-constrained runs, the separate AI V2 worker now allows an owner-selected model up to a 70-second default primary wait and a 90-second outer response boundary, subject to configured caps. Existing default Qwen3 retains its previous lower limits. STOP and voice-turn cancellation remain as previously implemented; pending model inference itself may finish later in the background of the existing process.

### Practical status

This is a **GitHub source integration**, not an installation on the owner's customized Spider OS. Testing on the owner's computer, compatible Heretic-derived GGUF/Ollama model, voice calibration, and remaining installed-source reconciliation are still pending. Do not claim that Heretic was activated on the PC or that it gives Webbie unrestricted shell/root/device control.

## Direct Q4 model installation for everyday Webbie, without running Heretic training

The owner can now choose Webbie Cognitive Center > My everyday AI brain > **Install Heretic Q4 and use it every day**. This is a one-time, explicit GUI confirmation, not a separate assistant.

The approved installer uses community quantization `hf.co/mradermacher/Qwen3-8B-heretic-GGUF:Q4_K_M` of `p-e-w/Qwen3-8B-heretic`. Sources: https://huggingface.co/mradermacher/Qwen3-8B-heretic-GGUF and https://huggingface.co/p-e-w/Qwen3-8B-heretic . Hugging Face lists the Q4_K_M model at approximately **5.03 GB**, far smaller than the 16.4 GB unquantized file. The quantizer is a third party; review origin and suitability before installation.

The native button launches the packaged `tools/install_everyday_heretic.sh --approved-by-owner` through Konsole after a visible owner Yes confirmation. The script checks local Ollama, 10 GiB available disk, a private lock to avoid duplicate pulls, and then runs `ollama pull` for the single fixed source. Only after confirming the exact model appears in local Ollama does `tools/activate_heretic_brain.py --owner-approved-install` select it as Webbie's persistent conversation model. An installation/download failure leaves original Qwen3 preferred. No model is automatically downloaded by a voice command or browser result; the user can cancel the Konsole download with Ctrl+C.

This option **does not require running the Heretic model-ablation CLI** on the 15 GiB CPU-only machine. The Heretic research lab remains available separately for experimental model development. Neither this script nor the research lab grants new filesystem/terminal/Kali/other application permissions to model output. It changes only the language model used for ordinary answers. Natasha, memory, normal voice behavior and pre-existing owner grants remain the same.

**Actual deployment status:** GitHub branch only. The model download has NOT occurred on the owner's PC, and the new model has NOT been benchmarked against owner audio latency or native tool workflows. The installed-source drift and owner-hardware release gate still apply.
