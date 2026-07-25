import { useState, useCallback } from 'react'
import { validateFingerprint } from '@/api/client'

export interface VoiceFingerprint {
  samples: string[]
  isActive: boolean
  sampleCount: number
  paragraphCount: number
  message: string
}

const EMPTY: VoiceFingerprint = {
  samples: [],
  isActive: false,
  sampleCount: 0,
  paragraphCount: 0,
  message: '',
}

export function useVoiceFingerprint() {
  const [fingerprint, setFingerprint] = useState<VoiceFingerprint>(EMPTY)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const addSamples = useCallback(async (rawSamples: string[]) => {
    const valid = rawSamples.map(s => s.trim()).filter(s => s.length > 0)
    if (valid.length < 2) {
      setError('Add at least 2 writing samples to activate voice fingerprinting.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const result = await validateFingerprint(valid)
      setFingerprint({
        samples: valid,
        isActive: result.active,
        sampleCount: result.sample_count,
        paragraphCount: result.paragraph_count,
        message: result.message,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fingerprint validation failed.')
    } finally {
      setLoading(false)
    }
  }, [])

  const clearFingerprint = useCallback(() => {
    setFingerprint(EMPTY)
    setError(null)
  }, [])

  return { fingerprint, loading, error, addSamples, clearFingerprint }
}
