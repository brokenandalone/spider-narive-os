# Forage + Deep Forage | October 11 source upgrade

**Status:** draft source branch only. Not merged, installed, or tested on Cory's current PC.

## Architecture

- **Forage** is quick web and explicitly selected local-file search. The existing `local_index.py` consent boundary remains unchanged.
- **Deep Forage** runs in the separate native research window and uses the same `engine.py` public search router. It does not read the local index by default, alter Study/Author documents or automatically publish anything.
- `search_backends.py` tries the existing local SearXNG at `http://127.0.0.1:8888/search`, then tries the installed `ddgs` library if SearXNG is down or returns no usable web hits. It does not start or install SearXNG. SearXNG's available external search engines depend on its own configuration. Search result records carry engine and reported date when available.
- `research_archive.py` saves a unique Markdown report **and** a private JSON source bundle to `~/Documents/Spider OS/Forage/Research/`. JSON includes retrieved evidence text; treat these files as personal research data. Writes are exclusive with mode 0600. Old reports are listed as history without a migration.
- The Deep Forage Qt window has a bounded 20-item sequential queue, queued-topic display, report/source buttons, and a report-history selector. There is one research worker; queueing does **not** start parallel background searches.

## Cancellation, quality, and limitations

- Stop clears pending questions and sends a cooperative cancellation signal to the active worker. The worker checks between searches, sources, before saving, and between streamed Ollama chunks. A pending network read can still delay stopping until it returns; stopping must not forcibly kill the GUI thread.
- Cancelled runs do not save incomplete drafts. Search and model failures still save an honest evidence-status report with source links, never fabricated findings. Citation validation remains conservative and is **not** a substitute for scholarly source checking.
- SearXNG/DDGS result URLs are filtered for scheme, loopback/private literal IPs, local-only names, and URLs with embedded credentials. This is *not* a complete DNS-rebinding protection or guarantee of source quality; follow only trusted pages.
- The program uses local Ollama; no new model is pulled or selected by this branch. Reports are not added to long-term Webbie memory without an explicit, future-approved integration.
- Search histories/JSON are retained until the user deletes them. No automatic uploads or syncing. Selected-source local indexing does not include PDFs/DOCX yet.
- Source code now appears in the guarded `system/release_batch.py` manifest. This is **not** permission to run the installer: source tree, local Python/venv, SearXNG health, Webbie and existing PC customizations must be reconciled first.

## Tests and acceptance

```bash
python3 -m unittest tests.test_forage_research_v2 tests.test_forage_evidence tests.test_local_index
python3 system/release_batch.py --check
```

On the owner's *staged* Spider OS tree, not live services: check local `curl -fsS 'http://127.0.0.1:8888/search?q=test&format=json'`, verify installed DDGS virtualenv/Python version, run Qt with `QT_QPA_PLATFORM=offscreen`, inspect report and source export, test queueing and stop, ensure GUI doesn't hang, and verify no regression to Webbie microphone/camera. Do not merge the draft into main or restart working services as part of a test.
