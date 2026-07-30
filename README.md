# Stilliu

**Every AI writing tool can change your voice. None of them can tell you whether it worked.**

Stilliu is an instrument panel for prose distinctiveness. It measures how close your draft sits to what a generic AI would write for the same content, generates rewrites that deliberately travel away from that centre, and attaches a **score delta to every single rewrite** — so you can see that the intervention moved the measurement, not just that something changed.

Built for the **IBM AI Builders Challenge — July 2026: "Reimagine Creative Industries with AI."**

---

## Problem

AI writing assistants make each individual writer better and every writer more alike. Doshi & Hauser (*Science Advances*, 2024) found generative AI raises individual creativity while measurably reducing the collective diversity of the resulting work. Padmakumar & He (ICLR 2024) showed feedback-tuned models reduce output diversity and increase inter-author similarity. Lu et al. (ICLR 2025) put a number on the gap: human-authored text scores 66.2% higher on their Creativity Index than LLM text, and RLHF *reduces* that index by around 30%.

Two things follow, and the second is the one nobody has addressed.

**Existing generative tools have no measurement.** Sudowrite, Novelcrafter, Jasper, and the built-in style presets of the major chat assistants all expose rich style controls and report nothing back. Reviewers of preset systems independently report that outputs "all sounded fairly similar." A writer applying a style instruction has no signal about whether it did anything.

**Existing measurement tools point the wrong way.** Hemingway, Grammarly, ProWritingAid, and Writer.com all score *conformity to a norm* — readability, correctness, house style. AutoCrit is the only widely-used comparative scorer and it measures proximity to genre convention, which its own reviewers call the cookie-cutter trap. Every one of them rewards you for sounding more like everyone else.

So the writer is caught between tools that change their voice without measuring it and tools that measure the opposite of what matters.

---

## Solution

Stilliu measures **distance**, and treats distinctiveness as the target rather than the deviation.

**1. A computable distinctiveness score.** Stilliu asks a current IBM Granite model to write the blandest possible version of your draft, then measures how far your prose sits from that anchor — blending semantic distance from Granite embeddings with a topic-independent stylometric distance across 12 measured features. The anchor is generated, not assumed, so the score is grounded in what an actual IBM model produces when told to be generic.

**2. Rewrites with the delta attached.** Pick from 18 style presets across 5 named groups, or write your own brief. Each direction returns three axis scores *and* the change versus your draft, so a rewrite that claims to be bolder has to prove it. Every axis reads the same way: **high is good**, everywhere.

**3. Controls that name what they change.** 17 writer controls — format, length, tone, audience, POV, tense, vocabulary, rhythm, opening, divergence distance, banned words, phrases to keep, voice-anchor strength, and a fact-preservation guard that flags invented claims and regenerates the direction that produced them.

The writer stays the author. Stilliu makes the invisible measurable, then gives them somewhere to go.

---

## What makes the measurement defensible

Four decisions carry the product. Each exists because the obvious approach fails in a specific, checkable way.

### Stylometry, because embeddings measure topic, not voice

Sentence embeddings encode *what* a text is about. Two rewrites of the same subject sit close together in embedding space even when their prose is wildly different, so a bold stylistic rewrite scores as "generic" on embedding distance alone. This was a real, shipped defect: same-subject rewrites scored ~90 generic regardless of style.

Distinctiveness therefore blends **semantic distance (40%)** with **stylometric distance (60%)** across 12 topic-independent features: mean sentence length and its standard deviation, mean word length, type-token ratio, function-word ratio, rare-word ratio, long-word ratio, and a punctuation profile of comma, semicolon, dash, question, and exclamation density. Style carries the larger weight because style is the thing being claimed.

This follows the content-controlled evaluation principle from **STEL** (Wegmann & Nguyen, EMNLP 2021) — style must be measured with topic held constant. It is also why Voice Match does not rest on an authorship encoder alone: encoders trained on same-author signal absorb topic alongside style, so Stilliu pairs embedding proximity with an explicit stylometric term instead.

### The baseline is never the model being scored

The anchor for distinctiveness must be independent of the model producing the rewrites. Otherwise the score means "distance from a colder version of myself," which is nothing.

The registry enforces two rules when picking the baseline: never the same model id as the creative model, and prefer a **different provider family**. A Granite baseline against a Llama creative model gives an independent idea of what bland prose sounds like. Only when a region hosts a single usable model does Stilliu accept the collapse — and then it says so in the response rather than hiding it.

This was also a shipped bug. `eu-gb` hosts no Granite instruct model, so a hardcoded Granite baseline silently fell back to the creative model and the hybrid claim quietly stopped being true. The scores still looked fine. They meant nothing. `tests/test_model_registry.py` exists to keep that from recurring.

### Model ids resolve against the region, never hardcoded

A hardcoded model id is a demo that works on one account and dies on another. On startup Stilliu asks watsonx what this account can actually call, then resolves each of the three roles against that list using an ordered preference chain. An explicitly configured id is always tried first, so an env override is honoured. If the region hosts none of the preferences, it takes what exists rather than refusing to start; if the catalogue query itself fails, every role falls back to its configured id. Withdrawn models are filtered out, because a withdrawn model is still listed and would give you an id that exists on paper and 404s in practice.

The registry never imports the watsonx SDK, which is why its logic is fully testable without credentials.

### Distinctiveness is not a quality score

Stilliu deliberately does **not** ship a single overall "quality" number, and does not classify text as AI- or human-written. Detector-style verdicts carry roughly 10% false positives, are biased against non-native writers, and the resulting accusations are a reputational minefield. Stilliu reports distances on named axes and lets the writer decide what to do with them.

---

## The three axes

| Axis | What it measures | 100 means | How it is computed |
|---|---|---|---|
| **Distinctiveness** | Distance from bland AI defaults | Maximally unlike generic AI prose | 40% semantic + 60% stylometric distance from a Granite-generated bland baseline |
| **Voice Match** | Proximity to the author's own voice | Sounds exactly like the writer | 50% semantic proximity to a voice centroid + 50% style proximity to the samples |
| **On-message** | Semantic faithfulness to the draft | Stayed true to the draft's meaning | Embedding proximity to the original draft |

Distinctiveness and Voice Match report an absolute score **and a delta versus your draft**. In the UI each axis is a rail with the draft's score drawn as a ghost tick — the gap between the tick and the fill *is* the product claim, made visible per rewrite.

On-message is the exception: it is reported against a fixed neutral midpoint rather than the draft, because a draft is trivially 100% on-message with itself and a draft-relative delta would carry no information.

Every blend weight is a named constant in `app/services/scoring.py` (`DIST_STYLE_WEIGHT`, `VOICE_SEMANTIC_WEIGHT`, and so on), not an inline literal, because the ratios are the editorial argument the file exists to make. The semantic calibration anchors come from a live probe against Granite embeddings (`calibrate.py`) rather than from intuition.

## Measurement flow

```
Draft text
    │
    ├─► Granite Embedding ──► draft_vector
    │                                        ┐
    ├─► Stylometry (12 features) ► style_vec ├─► Distinctiveness (0–100, high = bold)
    │                                        ┘
    └─► Granite Baseline ──► baseline_text ──► embedding + stylometry
                                               (the independent anchor)

Voice samples (optional)
    └─► Granite Embedding ──► voice_centroid ─┐
    └─► Stylometry ──────────► style_vectors ─┴─► Voice Match (0–100, high = yours)

Each direction
    └─► Granite Embedding ──► direction_vector ──► On-message (0–100, high = faithful)
    └─► Faithfulness guard ──► unsupported claims ──► refine loop if it fails
```

## The refine loop

A direction that fails its thresholds is regenerated with corrective feedback before the writer ever sees it. Two triggers, both in `app/main.py` as named constants: distinctiveness below 30, or — when fact preservation is on — faithfulness below 60. The response marks refined directions so the behaviour is visible rather than silent.

The faithfulness guard extracts checkable claims from generated text (numbers, percentages, years, quoted strings, multi-word proper nouns) and flags any that are not grounded in the source. This exists because the pre-hardening build invented a *Wall Street Journal* interview, cities, and statistics that appeared nowhere in the draft.

## Model roles

Three roles, each resolved against what the region actually hosts:

| Role | Preference | Why |
|---|---|---|
| Creative rewrites | `meta-llama/llama-3-3-70b-instruct` | Instruction-following under a persona constraint is what this role needs |
| Bland baseline | `ibm/granite-4-h-small` → `granite-3-3-8b-instruct` → older Granite | Current Granite generation, and a different provider family from the creative model so the anchor stays independent |
| All measurement | `ibm/granite-embedding-278m-multilingual` → `granite-embedding-107m` → slate retrievers | Multilingual Granite first; slate is present in nearly every region |

`GET /health` reports the ids that were actually resolved, not the ones requested — the UI badges read from it, so they can never claim a model that isn't loaded.

## Architecture

```
Browser (React 18 + Vite + TypeScript)
    │
    ├─ GET  /health                 resolved model ids, demo-mode flag
    ├─ GET  /api/styles             the 18-preset library, grouped
    ├─ POST /api/score              fast path: draft scores only
    ├─ POST /api/analyze            full path: scores + all directions + refine loop
    ├─ POST /api/direction          regenerate one direction (granular apply)
    └─ POST /api/fingerprint/validate   voice-sample check before committing
                │
         FastAPI (uvicorn) — ThreadPoolExecutor for parallel generation
                │
    ┌───────────┴──────────────────────────────────────────────┐
    │  embeddings.py   generation.py   scoring.py   styles.py   │
    │  stylometry.py   guardrails.py   fingerprint.py           │
    │  model_registry.py   textutil.py                          │
    └───────────┬──────────────────────────────────────────────┘
                │
         watsonx.ai (region-resolved)
         ├── granite-embedding-278m-multilingual   all distance measurement
         ├── granite-4-h-small                     bland baseline anchor
         └── llama-3-3-70b-instruct                creative directions
```

Directions are generated in parallel via `ThreadPoolExecutor`, so three rewrites cost roughly one rewrite in wall-clock time.

**Demo safety:** with no credentials the backend starts in demo mode and serves fixture responses. Every screen stays clickable with zero API calls and zero network dependency.

---

## The style library

18 presets across 5 groups. Three design rules, each with a reason:

- **Named for a stance, never an author.** "Sparse Minimalist," not "write like Hemingway." Impersonation is both a legal problem and a cookie-cutter one.
- **Grouped with visible headers.** Naming the *dimensions* of a design space prevents fixation on the first option (Luminate, CHI 2024).
- **Every preset carries an `avoid` ban list.** Positive-only style prompts drift back to model defaults; the instruction has to say what not to do.

| Group | Presets |
|---|---|
| **Compression** | Sparse Minimalist · Telegraphic · Long-Breath Cumulative · Plainspoken Reportorial |
| **Sensory & Figurative** | Sensory-Led · Metaphor-Dense · Object-Anchored · Synaesthetic / Estranged |
| **Argument & Rhetoric** | The Arguer · Socratic Interrogator · Aphorist · Steelman-then-Break |
| **Voice & Persona** | Confiding Second Person · Deadpan Ironist · Unreliable Close-Third · Bureaucratic Uncanny |
| **Counter-LLM** | Anti-Cadence · Rough Draft Energy |

Divergence is exposed as three named notches rather than a bare slider, because each notch can state its expected effect: **nudge** (word choice and rhythm only), **recast** (re-form freely, keep every point), **break** (discard the original structure entirely). Up to 6 directions per request, all genuinely in flight at once — the thread pool is sized to the selection, so the last two are not silently queued behind the first four. The cap bounds both latency and token spend.

The `Counter-LLM` group and the `avoid_ai_cadence` control target the measured markers of machine prose: tricolons, "not just X but Y," em-dash asides, summarising closers, and the known over-represented lexicon.

---

## Running it

Two paths. **Docker** is one command and behaves identically everywhere. **Native** gives you a faster edit loop and your own debugger.

### Credentials

Copy `backend/.env.example` to `backend/.env` and fill in your watsonx API key and project ID.

**Stilliu runs without credentials.** A fresh clone has no `.env` — it is gitignored — so `config.py` defaults the credentials to empty and turns demo mode on by itself, serving fixtures instead of calling watsonx. Every screen stays clickable. You only need an IBM account to see live generation.

That is deliberate: requiring the credentials would mean a clone dies at startup with a validation error before demo mode could be considered, which is the worst possible way for someone evaluating the project to meet it.

Model ids in `.env` are *requests*, not requirements — the registry resolves them against what your region actually hosts and logs any substitution.

> `backend/.env` is gitignored, and `backend/.dockerignore` keeps it out of image layers; Compose injects it at runtime instead.

### Docker

```bash
docker compose up --build
```

Frontend on <http://localhost:5173>, backend on <http://localhost:8000> (API docs at `/docs`). Both directories are bind-mounted, so edits hot-reload inside the containers.

```bash
docker compose exec backend python -m pytest tests/ -v
docker compose exec backend python selfcheck.py
```

### Native

Prerequisites: Python 3.10+, Node 18+. Two terminals.

```bash
# Terminal 1 — backend
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows PowerShell
# source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm install
npm run dev
```

Then open <http://localhost:5173>. The backend takes roughly 10 seconds to warm its SDK clients and resolve model ids on first start; this is logged.

Demo mode is automatic when credentials are absent. To force it on *with* valid credentials, set `DEMO_MODE=true` in the environment, or run `.\start_demo.bat` on Windows.

---

## Verification

Stilliu ships **136 tests** (111 test functions, of which several are parametrised), and the deterministic core is testable with no credentials and no network at all.

```bash
cd backend
python -m pytest tests/ -v   # 136 collected
python selfcheck.py          # deterministic math only — numpy, no SDK, no network
```

| Suite | Collected | Covers |
|---|---|---|
| `test_styles.py` | 78 | The preset library, selection arithmetic, custom briefs, every divergence notch and narration control, the cleared-selection invariant |
| `test_model_registry.py` | 25 | Region resolution, baseline independence, Granite preference order, withdrawn-model filtering |
| `test_guardrails.py` | 12 | Claim extraction and the faithfulness guard |
| `test_stylometry.py` | 11 | The 12 style features and the distance metric |
| `test_scoring.py` | 10 | Multi-axis scoring, delta arithmetic, high-is-good direction |

`selfcheck.py` validates stylometry, guardrails, and scoring with numpy alone — the fastest way to confirm a checkout is sound.

`model_registry.py` and the whole deterministic core deliberately never import the watsonx SDK, which is what makes credential-free testing possible.

### Live measurement scripts

Two scripts make real watsonx calls and **persist their results** to `backend/results/` via `runlog.py`, so numbers survive the terminal that produced them.

```bash
cd backend
# venv active, real credentials in .env

python calibrate.py           # → results/calibration-<utc>.json
python validate_pipeline.py   # → results/validation-<utc>.json
```

**`calibrate.py`** embeds known bland-vs-distinctive text pairs and reports the raw cosine distances, then recommends values for `_DIST_SEM_FLOOR` and `_DIST_SEM_CEIL` — the two constants in `scoring.py` that define the distinctiveness scale — using those exact names, so the output is directly copy-pasteable. Run it when you change region, embedding model, or those constants. The record includes the region, the model ids, the embedding dimension, every pair distance, and the recommended constants — so "which run produced the numbers currently in `scoring.py`" stays answerable.

**`validate_pipeline.py`** runs the whole pipeline end to end on a fixed draft and voice sample: warm clients, score the draft, build a voice centroid, generate directions in parallel, score each on all three axes, and run the faithfulness guard. Its headline is the claim the tool rests on — **how many directions actually beat the draft on distinctiveness** — recorded alongside per-direction deltas, the resolved model ids, and timings.

Each run writes two files: `<kind>-<utc-timestamp>.json` as the permanent record, and `<kind>-latest.json` at a stable path. The timestamped copies are what make "did the score move after I changed the weights?" answerable, since the old numbers still exist. `backend/results/` is gitignored — these are live model outputs, and generated prose is not something to commit by reflex.

To track results over time, run `validate_pipeline.py` before and after a scoring change and compare the two `headline` blocks:

```bash
python -c "import json,glob; [print(f, json.load(open(f))['headline']) for f in sorted(glob.glob('results/validation-*.json'))]"
```

---

## How IBM Bob Was Used

IBM Bob was the primary development tool for the original build of Stilliu — the working proof of concept that established the product idea, the API surface, and the first version of every module in `backend/app/`.

**Scaffolding and architecture.** Bob generated the project skeleton from a plain-English description: the FastAPI application, the Pydantic schemas in `models.py`, the settings layer in `config.py`, the service module split, and the React + Vite + TypeScript frontend with its component structure. The `services/` boundary — one module per responsibility, with `textutil.py` holding pure numpy helpers so the maths stays independently testable — came out of planning with Bob rather than from a later refactor.

**The measurement engine.** The first implementations of `embeddings.py`, `generation.py`, `scoring.py`, and `fingerprint.py` were written with Bob, including the watsonx client wiring, the cached SDK clients, and the parallel `ThreadPoolExecutor` generation path.

**Debugging live watsonx behaviour.** Bob was used to diagnose real failures against real API calls, not mocks: region model-availability mismatches, embedding truncation limits, and the SDK accessor names that move between versions.

**Documentation.** Bob drafted the original README, the environment templates, and the run scripts.

**Where Bob stopped.** The build credits ran out partway through the hardening pass. Everything after the proof of concept — the stylometry engine, the multi-axis rescoring, the model registry, the faithfulness guard, the style library, the UI rebuild, and the test suite — was built on top of Bob's foundation using Claude. This README says so because a submission that measures things should be honest about its own provenance.

---

## Challenge fit

**Theme: Reimagine Creative Industries with AI.**

*How can AI enhance creativity?* By measuring the cost of AI homogenisation and making it actionable. Stilliu is the only tool in this space that reports whether a style intervention actually moved the text.

*Help people create faster?* Six divergent, scored directions in parallel, each with the delta attached — work that would take hours of deliberate manual experimentation to reach.

*Unlock new creative experiences?* Voice fingerprinting gives a writer a personal reference point and answers a question no other tool answers: does this still sound like me?

*New forms of expression?* The preset library crosses stylistic registers in controlled, reproducible ways, with a group specifically built to push against the measured markers of machine prose.

**Where IBM technology sits.** Granite is load-bearing, not decorative. Granite embeddings compute every distance the product reports, and a Granite model generates the bland baseline that the entire distinctiveness axis is measured against. Remove Granite and there is no measurement — which is the whole product.

---

## Limitations

Stated plainly, because a measurement tool that oversells itself is self-refuting.

- **The distinctiveness scale is calibrated, not absolute.** The floor and ceiling constants come from a live probe (`calibrate.py`) on a small set of hand-picked text pairs. A score of 72 is meaningful relative to Stilliu's anchor; it is not a universal units-of-distinctiveness reading.
- **Distinctiveness is measured against a generated baseline, not against a population corpus.** The anchor is what one current Granite model writes when told to be bland. Scoring against a large reference corpus of published prose is the natural next step and is not built.
- **Voice Match needs samples to mean anything.** With no voice samples the axis is omitted rather than guessed. Two or three short samples is thin; the centroid gets meaningfully better with more.
- **The faithfulness guard is regex-based.** It catches numbers, years, quoted strings, and multi-word proper nouns. It will not catch a fluent, plausible, entirely invented sentence that contains no checkable surface features.
- **No authentication, no database, no multi-user state.** This is a single-machine demo by design. Do not deploy it as-is to a shared host.
- **Stylometric features are English-tuned.** The function-word and common-word lists are English, so scores on other languages are not trustworthy even though the embedding model is multilingual.
- **Latency is real.** Cold start is around 10 seconds to warm clients and resolve models; a full analyse with the refine loop takes roughly 25 seconds warm. Parallelism bounds it but does not hide it.

---

## Project structure

```
stilliu/
├── backend/
│   ├── Dockerfile
│   ├── .env.example                Credential + model-id template, documented
│   ├── app/
│   │   ├── main.py                 FastAPI app, 6 routes, lifespan warmup, refine loop
│   │   ├── config.py               Settings; forces demo mode when credentials are absent
│   │   ├── models.py               Pydantic schemas — AxisScores, WriterControls (17 controls)
│   │   ├── fixtures/               Reference copy of the response shape (the live demo
│   │   │                           path is hardcoded in main.py so it cannot drift)
│   │   └── services/
│   │       ├── model_registry.py   Region-aware model resolution; never imports the SDK
│   │       ├── embeddings.py       Granite embedding client (cached)
│   │       ├── generation.py       Baseline (Granite) + directions (Llama), parallel
│   │       ├── scoring.py          Three axes, deltas, high-is-good everywhere
│   │       ├── stylometry.py       12 topic-independent style features
│   │       ├── styles.py           18 presets in 5 groups, each with an avoid list
│   │       ├── guardrails.py       Claim extraction + faithfulness guard
│   │       ├── fingerprint.py      Voice centroid builder
│   │       └── textutil.py         Pure numpy helpers (cosine_distance, clamp)
│   ├── tests/                      136 tests, no credentials required
│   │   ├── test_styles.py          78   preset library + selection invariants
│   │   ├── test_model_registry.py  25   region resolution + baseline independence
│   │   ├── test_guardrails.py      12   faithfulness guard
│   │   ├── test_stylometry.py      11   style features + distance
│   │   └── test_scoring.py         10   multi-axis scoring + deltas
│   ├── runlog.py                   Persists live-script results to results/
│   ├── calibrate.py                Live calibration probe → results/calibration-*.json
│   ├── validate_pipeline.py        Live end-to-end validation → results/validation-*.json
│   ├── integration_test.py         API-level checks against a running server
│   ├── selfcheck.py                Offline numpy-only self-check
│   ├── start.bat / start_demo.bat  Windows shortcuts (live / demo mode)
│   └── requirements.txt
└── frontend/
    ├── Dockerfile
    ├── index.html · vite.config.ts · tsconfig.json · package.json
    └── src/
        ├── main.tsx                React entry point
        ├── App.tsx                 One-viewport shell, tabs both sides, granular apply
        ├── index.css               Class-based design system
        ├── api/client.ts           Typed API client
        ├── hooks/useVoiceFingerprint.ts
        └── components/
            ├── AxisMeter.tsx       Score rail with the draft drawn as a ghost tick
            ├── ControlsPanel.tsx   5 control tabs with off-default counts
            ├── DirectionPanel.tsx  Per-direction output, axis deltas, refine badge
            └── VoiceOnboarding.tsx
```

---

## Research basis

- **Doshi & Hauser (2024)**, *Generative AI enhances individual creativity but reduces the collective diversity of novel content*, Science Advances — the homogenisation result the product exists to address.
- **Lu et al. (ICLR 2025)**, *Creativity Index* (arXiv:2410.04265) — human text scores 66.2% higher than LLM text; RLHF reduces the index by ~30%.
- **Padmakumar & He (ICLR 2024)** (arXiv:2309.05196) — feedback-tuned models reduce diversity and increase inter-author similarity.
- **Wegmann & Nguyen (EMNLP 2021)**, *STEL* (arXiv:2109.04817) — content-controlled style evaluation; the basis for separating style from topic.
- **Wegmann et al. (RepL4NLP 2022)**, *CISR* — same-author / different-conversation contrastive style representation.
- **StyleDistance** (arXiv:2410.12757) — synthetic parallel examples for content-independent style embeddings.
- **Johnson et al. (2023)**, *DSI*, Behavior Research Methods — semantic-distance creativity scoring; explains up to 72% of variance in human creativity ratings.
- **Rivera-Soto et al. (EMNLP 2021)**, *Learning Universal Authorship Representations* (LUAR) — the standard authorship encoder. Stilliu deliberately does **not** use it as a voice-match metric: authorship encoders trained on same-author signal are known to absorb topic alongside style, which is the exact confound STEL and StyleDistance were built to control for. Voice Match therefore pairs embedding proximity with an explicit stylometric term rather than trusting an authorship embedding alone.
- **Luminate** (CHI 2024, arXiv:2310.12953) — naming the dimensions of a design space prevents fixation; the justification for grouped presets.
- **Agarwal, Naaman & Vashistha (CHI 2025)** — AI suggestions erase the cultural lexical-diversity gap (p=0.003 → p=0.75). Counter-evidence noted honestly: an ACL 2025 SRW paper found homogenisation *not* detectable via MTLD/Maas/MATTR, which is why Stilliu measures structural and stylometric distinctiveness rather than lexical diversity alone.

---

## Licence

MIT. See [LICENSE](LICENSE).

---

*Built for the IBM AI Builders Challenge 2026 — "Reimagine Creative Industries with AI."*
