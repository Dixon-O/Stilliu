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

Two supported paths. **Docker** is one command and works identically on every OS — use it if you just want the demo running. **Native** is better if you're developing, since you get your own debugger and a faster edit loop.

### Credentials (both paths)

Copy `backend/.env.example` to `backend/.env` and fill in your watsonx API key and project ID.

**Stilliu runs without credentials.** With no `.env`, the backend starts in demo mode and serves fixtures, so every screen is still clickable. You only need an IBM account to see live generation.

> Never commit `backend/.env`. It's gitignored, and `backend/.dockerignore` keeps it out of image layers too — Compose injects it at runtime instead.

---

### Option A — Docker (any OS)

**Prerequisite:** Docker Desktop (Windows/macOS) or Docker Engine + Compose v2 (Linux).

```bash
docker compose up --build
```

Frontend on <http://localhost:5173>, backend on <http://localhost:8000> (API docs at `/docs`). Both directories are bind-mounted, so edits on your machine hot-reload inside the containers.

```bash
docker compose down          # stop
docker compose up --build -d # rebuild and run detached
docker compose logs -f backend
```

Run the tests inside the container:

```bash
docker compose exec backend python -m pytest tests/ -v
docker compose exec backend python selfcheck.py
```

> **Older Compose:** the `env_file: required: false` key needs Compose v2.24+. On older versions, `touch backend/.env` to create an empty file and the stack will come up in demo mode.

---

### Option B — Native

**Prerequisites:** Python 3.10+, Node 18+.

Two terminals. Backend first.

<details open>
<summary><b>Windows (PowerShell)</b></summary>

```powershell
# Terminal 1 — backend
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm install
npm run dev
```

Batch shortcuts also exist: `.\start.bat` (live) and `.\start_demo.bat` (demo mode).

Two PowerShell gotchas worth knowing, because both have bitten this project:

- Always prefix batch files with `.\` — `start.bat` alone won't resolve.
- `&&` is **not** a statement separator in Windows PowerShell 5.1. Use `;` instead, or upgrade to PowerShell 7.
- If activation is blocked, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal.

</details>

<details>
<summary><b>macOS / Linux (bash or zsh)</b></summary>

```bash
# Terminal 1 — backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm install
npm run dev
```

For demo mode without credentials: `DEMO_MODE=true uvicorn app.main:app --reload --port 8000`.

On Debian/Ubuntu you may need `sudo apt install python3-venv` first.

</details>

Then open <http://localhost:5173>. The backend takes roughly 8 seconds to warm its SDK clients on first start — that's expected and logged.

### Tests

```bash
cd backend
python -m pytest tests/ -v   # full suite
python selfcheck.py          # deterministic math only — numpy, no network, no credentials
```

`selfcheck.py` validates stylometry, guardrails, and scoring with numpy alone. It needs no watsonx SDK and no network, so it's the fastest way to confirm a checkout is sound.

---

### Troubleshooting

**Scores show `NaN/100`, or the dials are labelled "Generic Score" / "Voice Distance".**
You're running a stale Vite bundle against the current backend — the old JS reads response fields that no longer exist. Vite's dependency cache survives a plain restart, so clear it:

```bash
# stop the dev server first (Ctrl+C)
cd frontend
rm -rf node_modules/.vite    # PowerShell: Remove-Item -Recurse -Force node_modules\.vite
npm run dev
```

Then hard-reload the browser (Ctrl+Shift+R, or Cmd+Shift+R on macOS). If it persists, open DevTools → Network → tick "Disable cache" and reload once with DevTools open.

**Port already in use.** Something else holds 8000 or 5173.
`netstat -ano | findstr :8000` on Windows, `lsof -i :8000` on macOS/Linux.

**Frontend loads but every API call fails.** The backend isn't up, or isn't on 8000. Check <http://localhost:8000/health> directly. Under Docker, confirm `VITE_API_TARGET=http://backend:8000` — inside the frontend container, `localhost` is the frontend itself.

**Docker: esbuild or rollup "wrong binary" errors.** A host `node_modules` is shadowing the container's. The anonymous volume in `docker-compose.yml` prevents this; if you edited it, restore the `- /app/node_modules` line.

**Docker: edits don't hot-reload.** inotify events don't cross bind mounts on Windows and macOS. Compose sets `VITE_USE_POLLING=true` to handle this — verify it's still in the frontend service's environment.

**The style picker is empty.** It's populated from `GET /api/styles`. Hit <http://localhost:8000/api/styles> directly; if that 404s, your backend predates the style library.


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
