# Spider OS October 11 Wave Five | Installation Preparation

**Candidate:** `release/oct11-wave5-all-systems-compatibility` in `brokenandalone/spider-narive-os`.  
**Baseline:** Owner-installed October 10 customized PC. **Status: DRAFT, NOT INSTALLED.**

## Combined major additions and constraints

- **The Web:** retain workspace menu readability, desktop/window management and existing GUI repairs. The only new panel integration is a *manual* JARVIS Workflow Board preview from directly typed owner commands. Preview does not execute anything. Its GUI can open only fixed, approved workspace destinations after owner click.
- **Webbie reasoning and local models:** preserve the configured installed Ollama chat model. The GitHub default `qwen3:1.7b` must never replace a verified newer PC choice. The model check is read-only by default and optionally uses one local inference for `--smoke`. No models downloaded or removed.
- **Webbie Brain/Eyes/Hands/Autopilot:** staged bounded workflow modules, not connected to unattended desktop control. New code is in the single installer manifest but user-PC integration must be reviewed.
- **Webbie owner access:** staged signed-off request helpers, owner-private permission store, bounded status and named-application diagnostics. **Persistent authorization is not connected to the resident PC**; no permissions can be presumed from a source merge.
- **Webbie Hearing/Speech:** staged WAV activity filter and voiceprint module. **Do not replace the resident Whisper listener or TTS from the older branch.** Cory/Shayna speaker provider must be enrolled/tested, with TV/replay and STOP behavior verified on hardware.
- **Studio:** Wave Four audio quality checks, production board, DAW handoffs, prior Band Mixer.
- **Author:** Story Atlas, Master Canon ledger and review-only Canon Intelligence.
- **Study:** SNHU planner, coach, reading provenance and local search.
- **Forage, Kali Bay, The Web System and Recovery:** preserve all prior integrated modules and wallpapers.
- **Nova and Media Center:** preserve local AI DJ `127.0.0.1:9876` and existing media source. V7 GPU visualizer installation is a **separate application** transaction after PC GPU testing.
- **BCN website:** visitor/owner source and newsroom updates are a **separate web deployment**. This Spider OS installer cannot deploy the website/backend.

## One safe check session on the actual PC

```bash
cd ~/Downloads
git clone --single-branch --branch release/oct11-wave5-all-systems-compatibility \
  https://github.com/brokenandalone/spider-narive-os.git Spider_OS_Wave5
cd Spider_OS_Wave5
bash tools/prep_oct11_release.sh
```

This reports source hashes, fixed installed-file differences, chosen local model, Nova status and one-batch release blockers. It writes **only a new private reports directory** in `~/Downloads`. The user must review/return these reports. It does not alter services, applications, private projects, voiceprints or OS boot.

**After reviewing source and live PC evidence**, separately run one opt-in model smoke:

```bash
python3 tools/webbie_model_compatibility.py --smoke --json
```

Only sends an unprivileged fixed test prompt to the *installed configured* local Ollama model.

## Hard release gates

- [ ] Current candidate SHA frozen **after last feature branch changes**.
- [ ] Verify CI and full tests on that exact SHA and identify any errors as blockers.
- [ ] Check all newer PRs, including #89, #90, #92, #95, #96 and PR #94 model safety for overlapping files; old Wave Four SHA is **not** source acceptance for Wave Five.
- [ ] Verify installed PC source files and actual active service model/voice setting. Any modified installed code remains untouched until independently reconciled.
- [ ] Preserve private data, schoolwork, music stems, manuscripts, local Ollama tags, webcam device config, microphone source, wallpapers, OneDrive and Nova port 9876.
- [ ] Test actual Webbie chat via installed chosen model, listening, natural TTS, STOP, voice trust, camera consent and computer actions.
- [ ] Test The Web, Study, Studio, Author, Forage, Kali Bay, Media/Nova and boot/GUI continuity on real PC.
- [ ] Test backup and rollback *before* activation, without consuming an extra install slot.
- [ ] Check prior same-day successful or partial-install receipts; one full system-wide installation maximum per Indianapolis calendar day.
- [ ] Explicit owner approval of the exact reviewed SHA, then ONE central installer transaction only.
- [ ] Perform after-install source acceptance, service/audio/playback tests and preserve rollback receipt.

**Source tests are not proof of on-PC installation.**
