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

export interface HealthResponse {
  status: string
  demo_mode: boolean
}

export interface FingerprintResponse {
  sample_count: number
  paragraph_count: number
  active: boolean
  message: string
}

const TIMEOUT_MS = 12_000

async function fetchWithTimeout(url: string, options: RequestInit): Promise<Response> {
  const controller = new AbortController()
  const id = setTimeout(() => controller.abort(), TIMEOUT_MS)
  try {
    const res = await fetch(url, { ...options, signal: controller.signal })
    return res
  } finally {
    clearTimeout(id)
  }
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetchWithTimeout(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`API error ${res.status}: ${detail}`)
  }
  return res.json() as Promise<T>
}

export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetchWithTimeout(`${BASE}/health`, { method: 'GET' })
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`)
  return res.json() as Promise<HealthResponse>
}

export async function analyzeDraft(
  draft: string,
  voiceSamples?: string[],
): Promise<AnalyzeResponse> {
  return post<AnalyzeResponse>('/api/analyze', {
    draft,
    voice_samples: voiceSamples ?? null,
  })
}

export async function validateFingerprint(samples: string[]): Promise<FingerprintResponse> {
  return post<FingerprintResponse>('/api/fingerprint/validate', { samples })
}
