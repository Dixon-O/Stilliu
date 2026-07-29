import React, { useState } from 'react'
import type { VoiceFingerprint } from '@/hooks/useVoiceFingerprint'

/**
 * VoiceOnboarding — build the voice fingerprint that unlocks the voice-match axis.
 *
 * This used to carry its own collapse toggle. It now lives inside the Voice tab
 * of the controls panel, so the tab *is* the disclosure and a second one would
 * just be a click in the way.
 */

interface Props {
  fingerprint: VoiceFingerprint
  onAddSamples: (samples: string[]) => Promise<void>
  onClear: () => void
  loading: boolean
  error: string | null
}

const PLACEHOLDER =
  "Paste a paragraph or two of something you've already written. The more natural and unedited, the better."

const MIN_SAMPLES = 2
const MAX_SAMPLES = 5

export default function VoiceOnboarding({
  fingerprint,
  onAddSamples,
  onClear,
  loading,
  error,
}: Props) {
  const [samples, setSamples] = useState<string[]>(['', ''])

  const filled = samples.filter((s) => s.trim().length > 0)
  const canSubmit = filled.length >= MIN_SAMPLES && !loading

  function update(i: number, value: string) {
    setSamples((prev) => prev.map((s, j) => (j === i ? value : s)))
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!canSubmit) return
    void onAddSamples(filled)
  }

  if (fingerprint.isActive) {
    return (
      <div style={S.stack}>
        <div className="callout" style={S.activeCallout}>
          <strong>{fingerprint.message}</strong>
        </div>
        <p className="field__hint">
          Your fingerprint is a centroid of paragraph-level embeddings plus a stylometric
          profile of your sentence rhythm and word habits. Every direction is scored against
          both, so voice-match of 100 means it reads as yours.
        </p>
        <button className="btn btn--sm" type="button" onClick={onClear}>
          Clear fingerprint
        </button>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} style={S.stack}>
      <p className="field__hint">
        Paste {MIN_SAMPLES}–{MAX_SAMPLES} samples of your natural writing to unlock the
        voice-match axis. Computed per session and never stored.
      </p>

      {samples.map((value, i) => (
        <div className="field" key={i}>
          <label className="field__label">
            Sample {i + 1}
            {i < MIN_SAMPLES ? ' · required' : ' · optional'}
          </label>
          <textarea
            className="textarea"
            rows={3}
            placeholder={PLACEHOLDER}
            value={value}
            onChange={(e) => update(i, e.target.value)}
          />
        </div>
      ))}

      {samples.length < MAX_SAMPLES && (
        <button
          className="btn btn--quiet btn--sm"
          type="button"
          style={{ alignSelf: 'flex-start' }}
          onClick={() => setSamples((prev) => [...prev, ''])}
        >
          + Add another sample
        </button>
      )}

      {error && <p className="callout callout--err">{error}</p>}

      <button className="btn btn--primary" type="submit" disabled={!canSubmit}>
        {loading
          ? 'Building fingerprint…'
          : filled.length < MIN_SAMPLES
            ? `Add ${MIN_SAMPLES - filled.length} more sample${MIN_SAMPLES - filled.length === 1 ? '' : 's'}`
            : `Build fingerprint from ${filled.length} samples`}
      </button>
    </form>
  )
}

const S: Record<string, React.CSSProperties> = {
  stack: { display: 'flex', flexDirection: 'column', gap: 10 },
  activeCallout: {
    color: 'var(--high)',
    background: 'var(--high-tint)',
    borderColor: '#a9e0cd',
  },
}
