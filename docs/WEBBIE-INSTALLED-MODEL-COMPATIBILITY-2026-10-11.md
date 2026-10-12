# Webbie Installed Model Compatibility | October 11 Upgrade Hold

**The October 10 working PC is authoritative.** The GitHub candidate's
`DEFAULT_MODEL = "qwen3:1.7b"` is only a fallback and **must not silently replace**
a newer model used by the owner's installed Webbie. A known installed
`qwen3:4b` is not proof of the current selected model; the PC must report it.

## What was found

- Current proposed Webbie `brain.py` selects `webbie/config/default.json`
  `ollama.model` when available and otherwise falls back to `qwen3:1.7b`.
- Wave Four's guarded installer does **not** include that config file or
  Ollama model blobs. Model tags remain physically installed.
- That is necessary but **insufficient**: the October 10 PC may run a
  customized model selector, have a different live service environment, or
  lack an exact matching configured model. Replacing its `brain.py`
  without a comparison risks repeating yesterday's regression.
- PR #93 (Studio v11, Author intelligence, Study passages, local model
  resilience), PR #92 (JARVIS Workflow Board), PR #90 (unified workflow)
  and PR #89 (Hearing/Speech v3) overlap on Webbie and shared shell files.
  None are equivalent to a fully reconciled PC installation.

## Required compatibility workflow

1. Stage the exact reviewed branch under the owner's home directory; do
   not `sudo` a Git pull or a read-only check.
2. From that staged branch on Spider OS run:

   ```bash
   python3 tools/webbie_model_compatibility.py --json
   python3 tools/daily_pc_acceptance.py --phase before --json
   python3 tools/daily_release_continuity.py --json
   ```

   The first command reads only the installed Webbie `default.json` and
   local model selector, the candidate selector/installer manifest,
   current-shell nonsecret `WEBBIE_BRAIN_MODEL` if present, and local
   Ollama `/api/tags`. It never pulls/swaps models, restarts Webbie, or
   captures speech/video. Its result **must not be marked approved**
   when `status` is BLOCKED or installed chat model is unknown.

3. With the exact configured installed model present and the owner ready
   to test an Ollama request, run the voluntary bounded LOCAL test:

   ```bash
   python3 tools/webbie_model_compatibility.py --smoke --json
   ```

   This sends only `Reply with the word ready.` to the **configured
   installed model** on `127.0.0.1:11434`. It never sends user text,
   saved context, secrets or manuscripts. Chat inference can take time
   or load the model into RAM. A pass **only** proves the selected local
   model responded in this environment, not that the entire agent works.

4. Inspect actual `webbie.service` runtime model overrides locally.
   Do not paste or upload entire environment dumps: they can expose
   unrelated tokens. An unknown override is a deployment hold. Review
   the installed `brain.py` source/hash differences and preserve
   the existing preferred model and custom PC fixes.

5. After the combined candidate incorporates all currently approved
   upgrades, independently test live Webbie: wake, sleep, universal
   STOP, assistant speaking interruption, Cory/Shayna permissions,
   normal multi-turn chat, memory continuity, task grants, camera
   permissions, Studio, Media/Nova, and GPU. Passing source unit tests
   or the isolated local Ollama request is **not** this acceptance.

6. Only when the exact candidate SHA, CI, preinstall comparisons, backup,
   rollback rehearsal, approved voice verification and model smoke are
   recorded may the independent `model_compatibility_verified` and
   other release gates be set true with owner approval.

**FAIL CLOSED:** If the configured model is missing, Ollama is offline,
source selector mismatches, model smoke fails, or an unexpected
Webbie service override is present, stop the system update and keep the
installed PC unchanged. Do not force a qwen3:1.7b downgrade, pull a
replacement, or quietly reroute to cloud providers.
