// ── Stilliu API client ──────────────────────────────────────────────────────
// All API calls go through here. Typed against the FastAPI response models.

const BASE = '' // Vite proxy routes /api and /health to localhost:8000

// ── Writer controls ───────────────────────────────────────────────────────────
export type Divergence = 'nudge' | 'recast' | 'break'

export type Pov = 'keep' | 'first' | 'second' | 'third'
export type Tense = 'keep' | 'present' | 'past'
export type Vocabulary = 'plain' | 'standard' | 'elevated'
export type Rhythm = 'keep' | 'uniform' | 'varied' | 'jagged'
export type Opening = 'keep' | 'claim' | 'image' | 'question' | 'in_media_res'

export interface WriterControls {
  preserve_facts: boolean
  fmt: 'prose' | 'bullets' | 'punchy' | 'longform'
  length: 'shorter' | 'match' | 'longer'
  tone: string
  audience: string
  /**
   * `null` and `[]` mean different things and the backend honours the
   * difference: `null` is "the writer hasn't opened the picker yet" and gets
   * the defaults, `[]` is "the writer cleared it on purpose" and stays empty.
   * Never collapse an empty array to null.
   */
  personas: string[] | null
  custom_persona: string
  divergence: Divergence
  avoid_ai_cadence: boolean
  voice_strength: number
  pov: Pov
  tense: Tense
  vocabulary: Vocabulary
  rhythm: Rhythm
  opening: Opening
  banned_words: string
  keep_phrases: string
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
  pov: 'keep',
  tense: 'keep',
  vocabulary: 'standard',
  rhythm: 'keep',
  opening: 'keep',
  banned_words: '',
  keep_phrases: '',
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

// ── Narration controls ────────────────────────────────────────────────────────
// Each table's first entry is the no-op value, so leaving a control alone adds
// nothing to the prompt. Labels are short because these render as segmented
// controls; the longer explanation lives in `hint`.

export interface Option<T> { value: T; label: string; hint?: string }

export const POV_OPTIONS: Option<Pov>[] = [
  { value: 'keep',   label: 'As drafted' },
  { value: 'first',  label: 'I',   hint: 'First person.' },
  { value: 'second', label: 'You', hint: 'Direct address.' },
  { value: 'third',  label: 'They', hint: 'Third person.' },
]

export const TENSE_OPTIONS: Option<Tense>[] = [
  { value: 'keep',    label: 'As drafted' },
  { value: 'present', label: 'Present' },
  { value: 'past',    label: 'Past' },
]

export const VOCABULARY_OPTIONS: Option<Vocabulary>[] = [
  { value: 'plain',    label: 'Plain',    hint: 'Short, concrete, everyday words.' },
  { value: 'standard', label: 'Standard', hint: 'No instruction — the style decides.' },
  { value: 'elevated', label: 'Elevated', hint: 'Precise and uncommon where it earns its place.' },
]

export const RHYTHM_OPTIONS: Option<Rhythm>[] = [
  { value: 'keep',    label: 'As drafted' },
  { value: 'uniform', label: 'Even',   hint: 'Sentences of similar length throughout.' },
  { value: 'varied',  label: 'Varied', hint: 'Long sentence, then a short one.' },
  { value: 'jagged',  label: 'Jagged', hint: 'Extremes and fragments. Most visible on the rhythm score.' },
]

export const OPENING_OPTIONS: Option<Opening>[] = [
  { value: 'keep',         label: 'As drafted' },
  { value: 'claim',        label: 'A claim',    hint: 'Open on the boldest assertion.' },
  { value: 'image',        label: 'An image',   hint: 'Open on something seen or heard.' },
  { value: 'question',     label: 'A question', hint: 'Open on the question the piece answers.' },
  { value: 'in_media_res', label: 'Mid-action', hint: 'Open already in motion, no set-up.' },
]

export const FORMAT_OPTIONS: Option<WriterControls['fmt']>[] = [
  { value: 'prose',    label: 'Prose' },
  { value: 'bullets',  label: 'Bullets' },
  { value: 'punchy',   label: 'Punchy' },
  { value: 'longform', label: 'Longform' },
]

export const LENGTH_OPTIONS: Option<WriterControls['length']>[] = [
  { value: 'shorter', label: 'Shorter' },
  { value: 'match',   label: 'Match' },
  { value: 'longer',  label: 'Longer' },
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
  /**
   * What this preset refuses to do. Optional because a backend predating the
   * field simply omits it, and a missing ban list should hide the row rather
   * than render an empty one.
   */
  avoid?: string
}

export interface StyleLibrary {
  groups: StyleGroup[]
  styles: StylePreset[]
  defaults: string[]
  max_selected: number
  /** Label the backend uses for the direction built from `custom_persona`. */
  custom_style_name: string
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

/** Response from POST /api/direction — exactly one card, same anchors as a batch run. */
export interface DirectionResponse {
  direction: DirectionCard
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
  // One generation instead of up to six, but it still pays the full scoring
  // and refine-loop cost, so it sits between the two.
  direction: 100_000,
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

/**
 * Pull the human-readable message out of a FastAPI error body.
 * The backend puts writer-facing text in `detail` (e.g. "No styles selected."),
 * so surface that verbatim rather than a raw JSON dump.
 */
function errorMessage(status: number, body: string): string {
  try {
    const parsed = JSON.parse(body) as { detail?: unknown }
    if (typeof parsed.detail === 'string' && parsed.detail.trim()) return parsed.detail
  } catch {
    /* not JSON — fall through to the raw body */
  }
  return body.trim() ? `${status}: ${body.slice(0, 300)}` : `Request failed (${status}).`
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
    throw new Error(errorMessage(res.status, await res.text()))
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
 * Regenerate one direction against the current controls.
 *
 * This is the granular counterpart to analyzeDraft: change a control, re-run
 * only the direction you are reading. It costs one generation instead of up to
 * six, and because the backend scores it against the same draft/baseline/voice
 * anchors, its deltas stay comparable with cards from a full run.
 */
export async function generateDirection(
  draft: string,
  voiceSamples: string[] | undefined,
  controls: WriterControls,
  style: string,
): Promise<DirectionResponse> {
  return post<DirectionResponse>(
    '/api/direction',
    { draft, voice_samples: voiceSamples ?? null, controls, style },
    TIMEOUTS.direction,
  )
}

/**
 * A stable fingerprint of everything that changes generated output.
 *
 * Stored next to each card so the UI can tell the writer *which* directions are
 * now out of date after a tweak. `personas` is excluded on purpose: adding or
 * removing a style from the selection doesn't invalidate the other styles'
 * output, it only changes which tabs exist.
 */
export function controlsSignature(controls: WriterControls): string {
  const { personas: _personas, ...rest } = controls
  return JSON.stringify(
    Object.keys(rest)
      .sort()
      .map((k) => [k, (rest as Record<string, unknown>)[k]]),
  )
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
