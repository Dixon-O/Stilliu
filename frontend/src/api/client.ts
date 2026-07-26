// ── Stilliu API client ──────────────────────────────────────────────────────
// All API calls go through here. Typed against the FastAPI response models.

const BASE = '' // Vite proxy routes /api and /health to localhost:8000

export interface ScoreResult {
  generic_distance: number
  voice_distance: number | null
  generic_raw: number
  voice_raw: number | null
}

export interface DirectionCard {
  persona: string
  persona_description: string
  text: string
  generic_distance: number
}

export interface AnalyzeResponse {
  scores: ScoreResult
  directions: DirectionCard[]
  demo_mode: boolean
}

export interface ScoreOnlyResponse {
  scores: ScoreResult
  baseline_preview: string
  demo_mode: boolean
}

export interface HealthResponse {
  status: string
  demo_mode: boolean
  embed_model: string
  gen_model: string
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
    // Translate AbortError into a human-readable message
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

/** Fast path — scores only. Backend timeout: 60s. Frontend allows 75s. */
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

/** Full analysis — scores + three divergent directions. Backend timeout: 120s. Frontend allows 140s. */
export async function analyzeDraft(
  draft: string,
  voiceSamples?: string[],
): Promise<AnalyzeResponse> {
  return post<AnalyzeResponse>(
    '/api/analyze',
    { draft, voice_samples: voiceSamples ?? null },
    TIMEOUTS.analyze,
  )
}

export async function validateFingerprint(samples: string[]): Promise<FingerprintResponse> {
  return post<FingerprintResponse>('/api/fingerprint/validate', { samples }, TIMEOUTS.health)
}
