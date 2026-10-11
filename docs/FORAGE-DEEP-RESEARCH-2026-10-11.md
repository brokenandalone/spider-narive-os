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


## Major V3 source additions

- Research depth: Quick (2 searches, up to 6 sources), Standard (4 searches, up to 12), Intensive (6 searches, up to 20); user-selected General/Academic/Technical/Creative lenses.
- The local Ollama model may be set with `SPIDER_FORAGE_MODEL`; existing default remains unchanged. No model is downloaded, installed or switched automatically.
- Research source JSON includes lens, depth, queries, evidence source text, provenance summary and citation audit. Metadata flags missing publication dates, snippet-only results, single-host evidence and near-duplicate article text. **Neither host counts nor lexical overlap prove a fact.**
- Citation references are validated for range and for visibly unreferenced long paragraphs. Failed model citation reviews are withheld and clearly labeled; this is not semantic fact-checking.
- Synthesis input budget is bounded. The saved source JSON retains the original extracted text and reports make truncation explicit.
- The Deep Forage GUI has approved-folder Study/Author exports. The user must select an existing destination folder. Files are copied with a prefix and mode 0600, with exclusive creation; they never overwrite an assignment or manuscript or submit homework.
- A separately speaker-verified Webbie voice bridge can open Deep Forage with an initial research question and list recent report titles/statuses. **The PC currently supplies no trusted speaker-verification signal to this route**, so voice handling must remain disabled by default. A wake phrase or recognized transcript is not verification.
- `forage/forage_cli.py` exposes opt-in `status`, `search --web --query`, `local --query`, `research --topic --depth --focus`, `history`, and `index`. `status` only checks local endpoints and lists reports; the CLI does not silently research or index sources.
- Explicitly selected local index roots can include bounded DOCX files and text-based PDFs. DOCX is parsed locally from bounded OOXML `word/document.xml` only. PDF extraction uses `pdftotext` when installed, with a timeout and no OCR. Scanned PDFs without text and files whose format/dependency is unsupported are skipped. No macro execution, external document-link fetching or whole-home scanning.
- The DOCX/PDF index retains the existing 2 MiB per-file cap, source symlink/credential exclusions, 0600 local SQLite index, atomic rebuild, and immediate configured-root revocation behavior.

### Explicit CLI smoke checks (staged sources only)

```bash
python3 forage/forage_cli.py status
python3 forage/forage_cli.py history
python3 forage/forage_cli.py local --query 'sociology'
python3 -m unittest discover -s tests -p 'test_forage*.py'
python3 -m unittest discover -s tests -p 'test_local_index.py'
python3 -m unittest discover -s tests -p 'test_webbie_workspace_voice_gate.py'
python3 system/release_batch.py --check
```

**Important:** GitHub Actions source success does not prove the new features run on the current installed Spider OS. A private PC audit must compare installed and candidate files, especially customized `webbie/agent/webbie.py`, and verify the actual `pdftotext`, PyQt, SearXNG and Ollama environment. Preserve the October 10–11 guarded batch release blockers until those tests pass.
