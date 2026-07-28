// ── Stilliu API client ──────────────────────────────────────────────────────
// All API calls go through here. Typed against the FastAPI response models.

const BASE = '' // Vite proxy routes /api and /health to localhost:8000

// ── Writer controls ───────────────────────────────────────────────────────────
export type Divergence = 'nudge' | 'recast' | 'break'

export interface WriterControls {
  preserve_facts: boolean
  fmt: 'prose' | 'bullets' | 'punchy' | 'longform'
  length: 'shorter' | 'match' | 'longer'
  tone: string
  audience: string
  personas: string[] | null
  custom_persona: string
  divergence: Divergence
  avoid_ai_cadence: boolean
  voice_strength: number
}

export const DEFAULT_CONTROLS: WriterControls = {
  preserve_facts: true,
  fmt: 'prose',
  length: 'match',
  tone: '',
  audience: '',
  personas: null,
  custom_persona: '',
  divergence: 'recast',
  avoid_ai_cadence: false,
  voice_strength: 0.5,
}

/** Named notches beat a bare slider — each one states what it will do. */
export const DIVERGENCE_NOTCHES: {
  value: Divergence
  label: string
  hint: string
}[] = [
  { value: 'nudge',  label: 'Nudge',  hint: 'Same structure, sharpened. Word choice and rhythm only.' },
  { value: 'recast', label: 'Recast', hint: 'Re-formed freely in the style, every point kept.' },
  { value: 'break',  label: 'Break',  hint: 'Original shape discarded and rebuilt. Highest risk, highest gain.' },
]

// ── Style preset library (served from backend/app/services/styles.py) ─────────
export interface StyleGroup {
  id: string
  label: string
  blurb: string
}

export interface StylePreset {
  name: string
  group: string
  group_label: string
  description: string
}

export interface StyleLibrary {
  groups: StyleGroup[]
  styles: StylePreset[]
  defaults: string[]
  max_selected: number
}

// ── Multi-axis scores (HIGH = GOOD everywhere) ────────────────────────────────
export interface AxisScores {
  distinctiveness: number
  voice_match: number | null
  on_message: number
}

export interface AxisDeltas {
  distinctiveness: number
  voice_match: number | null
  on_message: number
}

export interface DraftScores {
  distinctiveness: number
  voice_match: number | null
  summary: string
}

export interface DirectionCard {
  persona: string
  persona_description: string
  text: string
  scores: AxisScores
  deltas: AxisDeltas
  faithfulness: number
  unsupported_claims: string[]
  summary: string
  refined: boolean
}

export interface AnalyzeResponse {
  draft_scores: DraftScores
  directions: DirectionCard[]
  baseline_preview: string
  demo_mode: boolean
}

export interface ScoreOnlyResponse {
  draft_scores: DraftScores
  baseline_preview: string
  demo_mode: boolean
}

export interface HealthResponse {
  status: string
  demo_mode: boolean
  embed_model: string
  gen_model: string
  baseline_model: string
}

export interface FingerprintResponse {
  sample_count: number
  paragraph_count: number
  active: boolean
  message: string
}

// Timeouts match backend config (score_timeout=60s, analyze_timeout=120s)
// plus a small browser-side buffer so the backend fallback fires first.
const TIMEOUTS = {
  health:  8_000,
  score:   75_000,   // backend score_timeout=60s + 15s buffer
  analyze: 140_000,  // backend analyze_timeout=120s + 20s buffer
}

async function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeoutMs: number,
): Promise<Response> {
  const controller = new AbortController()
  const id = setTimeout(() => controller.abort('timeout'), timeoutMs)
  try {
    const res = await fetch(url, { ...options, signal: controller.signal })
    return res
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new Error(`Request timed out after ${Math.round(timeoutMs / 1000)}s. The backend is still processing — please try again.`)
    }
    throw err
  } finally {
    clearTimeout(id)
  }
}

async function post<T>(path: string, body: unknown, timeoutMs: number): Promise<T> {
  const res = await fetchWithTimeout(
    `${BASE}${path}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
    timeoutMs,
  )
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`API error ${res.status}: ${detail}`)
  }
  return res.json() as Promise<T>
}

export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetchWithTimeout(`${BASE}/health`, { method: 'GET' }, TIMEOUTS.health)
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`)
  return res.json() as Promise<HealthResponse>
}

/** Fast path — draft scores only. Backend timeout: 60s. Frontend allows 75s. */
export async function scoreDraft(
  draft: string,
  voiceSamples?: string[],
): Promise<ScoreOnlyResponse> {
  return post<ScoreOnlyResponse>(
    '/api/score',
    { draft, voice_samples: voiceSamples ?? null },
    TIMEOUTS.score,
  )
}

/** Full analysis — scores + divergent directions. Backend timeout: 120s. Frontend allows 140s. */
export async function analyzeDraft(
  draft: string,
  voiceSamples: string[] | undefined,
  controls: WriterControls,
): Promise<AnalyzeResponse> {
  return post<AnalyzeResponse>(
    '/api/analyze',
    { draft, voice_samples: voiceSamples ?? null, controls },
    TIMEOUTS.analyze,
  )
}

export async function validateFingerprint(samples: string[]): Promise<FingerprintResponse> {
  return post<FingerprintResponse>('/api/fingerprint/validate', { samples }, TIMEOUTS.health)
}

/**
 * Fetch the style preset library. The list lives in styles.py on the backend so
 * adding a preset there makes it appear in the picker with no frontend change.
 */
export async function fetchStyles(): Promise<StyleLibrary> {
  const res = await fetchWithTimeout(`${BASE}/api/styles`, { method: 'GET' }, TIMEOUTS.health)
  if (!res.ok) throw new Error(`Could not load style library: ${res.status}`)
  return res.json() as Promise<StyleLibrary>
}
