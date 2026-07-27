# Stilliu

**A creative writing partner that fights AI sameness.**

---

## Problem Statement

When writers use AI tools, their individual work gets better — but everyone's work starts to sound the same. This is not anecdotal: Doshi & Hauser (2024) and multiple 2026 arXiv papers document measurable convergence in AI-assisted writing toward a statistical mean. Individual quality rises; collective distinctiveness collapses.

The problem is that existing AI writing tools have no mechanism to measure or resist this. They optimise for fluency and correctness, not for distinctiveness. Writers using them have no signal that their voice is eroding.

---

## Solution

**Stilliu** gives writers three things no existing tool provides:

1. **A real, computable measurement** of how generic their draft is — a genuine cosine distance between their draft's embedding and what a default AI would write for the same content, blended with topic-independent stylometric features so the score reflects *how* the text is written, not just *what* it is about.

2. **Three divergent directions** generated using distinct stylistic personas, each scored on three axes (Distinctiveness, Voice Match, On-message) shown as deltas vs the draft — so the writer can see alternatives that are provably bolder, and understand exactly what was traded to get there.

3. **Writer controls** — format, length, tone, audience, persona selection, custom directions, voice anchoring strength, and a fact-preservation guard that flags and regenerates directions that invent claims not present in the source.

The writer stays the author. Stilliu makes the invisible visible — and gives them a path to something better.

---

## AI Approach & Architecture

### The Core Measurement

Stilliu measures **distance**, not abstract quality. Every number the user sees is derived from real cosine distances between embedding vectors — defensible, reproducible, and falsifiable.

**Why stylometry?** Sentence embeddings capture *what* a text is about, not *how* it is written. Two rewrites of the same subject sit close together in embedding space even when their prose styles are wildly different. A bold stylistic rewrite can score as "generic" on pure embedding distance alone. Stilliu blends semantic distance (40%) with topic-independent stylometric distance (60%) — sentence rhythm, lexical variety, function-word mix, punctuation profile — to separate style distinctiveness from topic distance.

```
Draft text
    │
    ├─► Granite Embedding ──► draft_vector
    │                                        ┐
    ├─► Stylometry ──────────► style_vector  ├─► Distinctiveness (0–100, high=bold)
    │                                        ┘
    └─► Granite Baseline ──► baseline_text
              │
              ├─► Granite Embedding ──► baseline_vector
              └─► Stylometry ────────► baseline_style_vector

Voice samples (optional)
    └─► Granite Embedding ──► voice_centroid
    └─► Stylometry ────────► voice_style_vectors ──► Voice Match (0–100, high=yours)

Direction text
    └─► Granite Embedding ──► direction_vector ──► On-message (0–100, high=faithful)
```

### Three Axes — HIGH = GOOD everywhere

| Axis | What it measures | 100 means |
|---|---|---|
| **Distinctiveness** | Distance from bland AI defaults (semantic + stylometric) | Maximally bold, unlike generic AI prose |
| **Voice Match** | Proximity to the author's voice fingerprint | Sounds exactly like the writer |
| **On-message** | Semantic faithfulness to the original draft | Stayed true to the draft's meaning |

Each direction shows its absolute score and its **delta vs the draft** — so the writer sees not just a number but whether the direction improved on what they started with.

### Faithfulness Guard

A regex-based claim extractor identifies checkable facts in each direction (numbers, percentages, years, quoted strings, multi-word proper nouns). Any claim not grounded in the source material is flagged as unsupported. Directions that fail the faithfulness threshold are automatically regenerated with corrective feedback before display.

### Hybrid Model Strategy

| Role | Model |
|---|---|
| Creative persona rewrites | `meta-llama/llama-3-3-70b-instruct` (best instruction-following in eu-gb) |
| Bland baseline generation | `ibm/granite-3-3-8b-instruct` (falls back to Llama if unavailable in-region) |
| All embedding / distance measurement | `ibm/granite-embedding-278m-multilingual` |

### Divergent Generation

Three stylistic personas with independent constraint axes, generated **in parallel** via `ThreadPoolExecutor`:

- **Sparse Minimalist** — compression, declarative sentences, silence
- **The Arguer** — bold claim, step-by-step case, refutes objection
- **Sensory-Led** — concrete physical detail, grounds abstraction in scene

Writer controls shape every direction: format (prose/bullets/punchy/longform), length, tone, audience, and a voice-anchor clause built from verbatim excerpts of the writer's own samples. A **refine loop** regenerates any direction that scores below the distinctiveness threshold or fails the faithfulness guard, with targeted corrective feedback.

### Stack

| Layer | Technology |
|---|---|
| Embeddings | `ibm/granite-embedding-278m-multilingual` via watsonx.ai |
| Generation | `meta-llama/llama-3-3-70b-instruct` + `ibm/granite-3-3-8b-instruct` via watsonx.ai (eu-gb) |
| Backend | Python 3.10 · FastAPI · uvicorn |
| Frontend | React 18 · Vite · TypeScript |
| Deployment | Single-machine, self-contained — no database, no auth |

### Architecture

```
Browser (React + Vite)
    │
    ├─ POST /api/score    ── Fast path: draft scores only (~8s warm)
    └─ POST /api/analyze  ── Full path: scores + directions + refine loop (~25s warm)
                │
         FastAPI (uvicorn)
                │
    ┌───────────┼───────────────────────────────────┐
    │  embeddings.py  │  generation.py  │  scoring.py  │
    │  stylometry.py  │  guardrails.py  │  fingerprint.py │
    └───────────┼───────────────────────────────────┘
                │
         watsonx.ai eu-gb
         ├── granite-embedding-278m-multilingual
         ├── granite-3-3-8b-instruct  (baseline)
         └── llama-3-3-70b-instruct   (creative directions)
```

**Demo safety**: `DEMO_MODE=true` serves pre-computed fixture responses — the full application works with zero API calls, zero network dependency.

---

## Challenge Theme

**IBM AI Builders Challenge — July 2026: "Reimagine Creative Industries with AI"**

Stilliu directly addresses all four challenge questions:
- *How can AI enhance creativity?* — By making the invisible visible: writers can now see and measure the cost of AI homogenisation, and act on it.
- *Help people create faster?* — Three divergent directions generated in ~25s that would take hours of deliberate experimentation to reach manually.
- *Unlock new creative experiences?* — Voice fingerprinting is a genuinely new capability: a personal creative mirror that tells you whether your draft still sounds like you.
- *New forms of expression?* — The persona system produces text that crosses stylistic registers in controlled, reproducible ways.

---

## Running Locally

### Prerequisites
- Python 3.10+
- Node 18+
- IBM Cloud account with watsonx.ai access (eu-gb region)

### Backend

```powershell
cd backend

# Install dependencies
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Configure credentials — copy .env.example to .env and fill in your key + project ID
# Do NOT overwrite an existing .env

# Start (live mode)
.\start.bat

# Start (demo mode — no API calls, no credentials needed)
.\start_demo.bat
```

> **PowerShell note:** Always prefix batch files with `.\` in PowerShell. The server takes ~8s to warm up SDK clients on first start — this is expected and logged.

### Frontend

```powershell
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

### Run Tests

```bash
cd backend
python -m pytest tests/ -v
```

### Offline self-check (no credentials needed)

```bash
cd backend
python selfcheck.py
```

Validates all deterministic math (stylometry, guardrails, scoring) with numpy only — no watsonx SDK, no network.

---

## Project Structure

```
stilliu/
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI app, routes, lifespan warmup, refine loop
│   │   ├── config.py           # Settings via pydantic-settings (hybrid model IDs)
│   │   ├── models.py           # Pydantic schemas — AxisScores, WriterControls, etc.
│   │   ├── fixtures/           # Pre-computed demo responses
│   │   └── services/
│   │       ├── embeddings.py   # Granite embedding client (cached)
│   │       ├── generation.py   # Baseline (Granite) + persona directions (Llama)
│   │       ├── scoring.py      # Multi-axis scoring — high=good everywhere
│   │       ├── stylometry.py   # Topic-independent style feature vectors
│   │       ├── guardrails.py   # Faithfulness / hallucination guard
│   │       ├── fingerprint.py  # Voice centroid builder
│   │       └── textutil.py     # Pure numpy helpers (cosine_distance, clamp, etc.)
│   ├── tests/
│   │   ├── conftest.py         # Demo-mode fixture, env setup
│   │   ├── test_scoring.py     # Multi-axis scoring unit tests
│   │   ├── test_stylometry.py  # Style feature + distance tests
│   │   └── test_guardrails.py  # Faithfulness guard tests
│   ├── selfcheck.py            # Offline numpy-only self-check script
│   ├── start.bat               # Start backend (live mode)
│   ├── start_demo.bat          # Start backend (demo mode)
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── App.tsx              # Main layout, two-phase analyze flow, controls
    │   ├── api/client.ts        # Typed API client (WriterControls, AxisScores, etc.)
    │   ├── hooks/               # useVoiceFingerprint
    │   └── components/
    │       ├── ScoreDials.tsx   # Gauge dials — color by meaning, delta display
    │       ├── DirectionCards.tsx  # Three-axis cards, faithfulness flags, refine badge
    │       ├── ControlsPanel.tsx   # Writer controls (format, tone, personas, etc.)
    │       └── VoiceOnboarding.tsx
    └── package.json
```

---

## Research Basis

- Doshi, A. R., & Hauser, O. P. (2024). Generative AI enhances individual creativity but reduces the collective diversity of novel content. *Science Advances.*
- Multiple 2026 arXiv papers documenting AI-assisted writing homogenisation effects.

---

*Built for IBM AI Builders Challenge 2026 — "Reimagine Creative Industries with AI"*
