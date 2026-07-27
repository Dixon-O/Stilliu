# Stilliu

**A creative writing partner that fights AI sameness.**

---

## Problem Statement

When writers use AI tools, their individual work gets better — but everyone's work starts to sound the same. This is not anecdotal: Doshi & Hauser (2024) and multiple 2026 arXiv papers document measurable convergence in AI-assisted writing toward a statistical mean. Individual quality rises; collective distinctiveness collapses.

The problem is that existing AI writing tools have no mechanism to measure or resist this. They optimise for fluency and correctness, not for distinctiveness. Writers using them have no signal that their voice is eroding.

---

## Solution

**Stilliu** gives writers two things no existing tool provides:

1. **A real, computable measurement** of how generic their draft is — not an abstract "originality score", but a genuine cosine distance between their draft's embedding and what a default AI would write for the same content.

2. **Three divergent directions** generated using distinct stylistic personas, each scored against the same baseline, so the writer can see alternatives that are provably less generic than what they started with.

The writer stays the author. Stilliu makes the invisible visible — and gives them a path to something better.

---

## AI Approach & Architecture

### The Core Measurement (Non-Negotiable Design Principle)

Stilliu measures **distance**, not abstract quality. Every number the user sees is a real cosine distance between two embedding vectors — defensible, reproducible, and falsifiable.

```
Draft text
    │
    ├─► Granite Embedding ──► draft_vector
    │
    └─► LLM (bland baseline prompt) ──► baseline_text
                                              │
                                              └─► Granite Embedding ──► baseline_vector
                                                                               │
                                              cosine_distance(draft_vector, baseline_vector)
                                                                               │
                                              normalise to 0–100 display score
```

**Generic Distance** = how close the draft sits to what a default AI would write for the same content.
- High score (near 100) = sounds like everyone
- Low score (near 0) = distinctly yours

**Voice Distance** = cosine distance from the writer's own voice fingerprint centroid (built by embedding their past writing samples and averaging the vectors).

### Calibration

Constants are derived from a live probe against the Granite embedding API:
- Bland AI text vs bland AI text: raw distance ~0.089 (very close → generic)
- Distinctive human text vs its own bland baseline: raw distance ~0.35 (typical case)
- Cross-style maximum: ~0.50

These anchor the 0–100 display scale to real, observed distances.

### Divergent Generation

Three stylistic personas with independent constraint axes:
- **Sparse Minimalist** — compression, declarative sentences, silence
- **The Arguer** — bold claim, step-by-step case, refutes objection
- **Sensory-Led** — concrete physical detail, grounds abstraction in scene

All three are generated **in parallel** via `ThreadPoolExecutor`. Each direction is immediately scored against the same baseline, so the user can see its generic distance as a number — not just read the text.

If voice samples are provided, extracted style signals (sentence length, vocabulary richness, punctuation patterns) are injected into each persona prompt as a voice-anchor constraint — divergence from the persona, recognisability from the writer.

### Stack

| Layer | Technology |
|---|---|
| Embeddings | `ibm/granite-embedding-278m-multilingual` via watsonx.ai |
| Generation | `meta-llama/llama-3-3-70b-instruct` via watsonx.ai (eu-gb) |
| Backend | Python 3.10 · FastAPI · uvicorn |
| Frontend | React 18 · Vite · TypeScript |
| Deployment | Single-machine, self-contained — no database, no auth |

### Architecture

```
Browser (React + Vite)
    │
    ├─ POST /api/score    ── Fast path: scores only (~8s warm)
    └─ POST /api/analyze  ── Full path: scores + 3 directions (~20s warm)
                │
         FastAPI (uvicorn)
                │
         ┌──────┴──────────────────────────┐
         │  embeddings.py  │  generation.py  │
         │  (cached client) │  (cached client) │
         └──────┬──────────────────────────┘
                │
         watsonx.ai eu-gb
         ├── granite-embedding-278m-multilingual
         └── llama-3-3-70b-instruct
```

**Demo safety**: `DEMO_MODE=true` serves pre-computed fixture responses from `backend/app/fixtures/demo_responses.json` — the full application works with zero API calls, zero network dependency.

---

## Challenge Theme

**IBM AI Builders Challenge — July 2026: "Reimagine Creative Industries with AI"**

Stilliu directly addresses all four challenge questions:
- *How can AI enhance creativity?* — By making the invisible visible: writers can now see and measure the cost of AI homogenisation, and act on it.
- *Help people create faster?* — Three divergent directions generated in ~20s that would take hours of deliberate experimentation to reach manually.
- *Unlock new creative experiences?* — Voice fingerprinting is a genuinely new capability: a personal creative mirror that tells you whether your draft still sounds like you.
- *New forms of expression?* — The persona system produces text that crosses stylistic registers in controlled, reproducible ways.

---

## How IBM Bob Was Used

IBM Bob (IBM SkillsBuild / BeMyApp) was the build tool across the entire SDLC — not a helper for one task, but the engineer across every phase:

| Phase | Bob's role |
|---|---|
| **Planning** | Analysed the idea brief, identified the "distance not originality" architectural constraint, designed the milestone structure, selected the stack |
| **Architecture** | Designed the two-axis measurement model, the centroid-based voice fingerprint, the persona divergence system |
| **Backend** | Authored all Python — FastAPI app, embedding service, generation service, scoring service, fingerprint service, all Pydantic models |
| **Frontend** | Authored all TypeScript/React — API client, hooks, all components, two-phase score+directions UX flow |
| **Debugging** | Diagnosed and fixed SDK cold-start latency (module-level client caching), PowerShell pipe deadlock in server startup, model availability mismatch between eu-gb region and expected model IDs |
| **Testing** | Wrote all unit tests (scoring service, 8/8 deterministic vector tests), calibration probe script, full pipeline validation script |
| **Calibration** | Ran live embedding probe against Granite API to derive real cosine distance floor/ceiling constants |
| **Git** | Structured all commits with conventional commit messages, rewrote author identity across history |
| **README** | This document |

Every file in this repository was authored through the Bob session. No external code was copied in.

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

# Configure credentials
# Copy .env.example to .env and fill in WATSONX_API_KEY and WATSONX_PROJECT_ID
# Do NOT use 'copy .env.example .env' if you already have a .env — it will overwrite it

# Start (live mode) — note the .\ prefix required by PowerShell
.\start.bat

# Start (demo mode — no API calls, no credentials needed)
.\start_demo.bat
```

> **PowerShell note:** Always prefix batch files with `.\` in PowerShell (e.g. `.\start.bat`).
> The server takes ~8s to warm up SDK clients on first start — this is expected and logged.

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

---

## Project Structure

```
stilliu/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app, routes, lifespan warmup
│   │   ├── config.py        # Settings via pydantic-settings
│   │   ├── models.py        # Pydantic request/response schemas
│   │   ├── fixtures/        # Pre-computed demo responses
│   │   └── services/
│   │       ├── embeddings.py   # Granite embedding + cosine distance
│   │       ├── generation.py   # Baseline + 3 persona directions
│   │       ├── scoring.py      # Normalised distance → display score
│   │       └── fingerprint.py  # Voice centroid builder
│   ├── tests/               # Unit tests (8/8 passing)
│   ├── start.bat            # Start backend (live mode)
│   ├── start_demo.bat       # Start backend (demo mode)
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── App.tsx           # Main layout, two-phase analyze flow
    │   ├── api/client.ts     # Typed API client
    │   ├── hooks/            # useVoiceFingerprint
    │   └── components/       # ScoreDials, DirectionCards, VoiceOnboarding
    └── package.json
```

---

## Research Basis

- Doshi, A. R., & Hauser, O. P. (2024). Generative AI enhances individual creativity but reduces the collective diversity of novel content. *Science Advances.*
- Multiple 2026 arXiv papers documenting AI-assisted writing homogenisation effects.

---

*Built with IBM Bob — IBM AI Builders Challenge 2026*
