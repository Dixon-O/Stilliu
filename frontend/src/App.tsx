import React, { useState, useEffect } from 'react'
import { analyzeDraft } from '@/api/client'
import { checkHealth } from '@/api/client'
import type { AnalyzeResponse } from '@/api/client'
import ScoreDial from '@/components/ScoreDials'
import DirectionCards from '@/components/DirectionCards'
import VoiceOnboarding from '@/components/VoiceOnboarding'
import { useVoiceFingerprint } from '@/hooks/useVoiceFingerprint'

const PLACEHOLDER = `Paste your draft here — an opening paragraph, a caption, a scene, an argument. Whatever you're working on. Stilliu will measure how generic it sounds and generate three distinct directions for where it could go.`

export default function App() {
  const [draft, setDraft] = useState('')
  const [result, setResult] = useState<AnalyzeResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [demoMode, setDemoMode] = useState(false)

  const { fingerprint, loading: fpLoading, error: fpError, addSamples, clearFingerprint } = useVoiceFingerprint()

  // Health check on mount — sets demo mode banner
  useEffect(() => {
    checkHealth()
      .then(h => setDemoMode(h.demo_mode))
      .catch(() => setDemoMode(true))
  }, [])

  async function handleAnalyze(e: React.FormEvent) {
    e.preventDefault()
    if (!draft.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await analyzeDraft(
        draft.trim(),
        fingerprint.isActive ? fingerprint.samples : undefined,
      )
      setResult(res)
      if (res.demo_mode) setDemoMode(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={styles.root}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerInner}>
          <div style={styles.logo}>Stilliu</div>
          <div style={styles.tagline}>Find what makes your writing unmistakable.</div>
          {demoMode && (
            <div style={styles.demoBanner}>
              Demo mode — fixture responses · no API calls
            </div>
          )}
        </div>
      </header>

      {/* Main layout */}
      <main style={styles.main}>
        {/* Left panel */}
        <div style={styles.leftPanel}>
          <form onSubmit={handleAnalyze} style={styles.form}>
            <textarea
              style={styles.textarea}
              placeholder={PLACEHOLDER}
              value={draft}
              onChange={e => setDraft(e.target.value)}
              rows={10}
            />
            <button
              type="submit"
              style={loading ? { ...styles.submitBtn, opacity: 0.6 } : styles.submitBtn}
              disabled={loading || !draft.trim()}
            >
              {loading ? 'Analysing…' : 'Analyse'}
            </button>
          </form>

          {error && <div style={styles.errorMsg}>{error}</div>}

          {/* Score dials */}
          <div style={styles.dialsRow}>
            <ScoreDial
              label="Generic Score"
              value={result?.scores.generic_distance ?? null}
              subtitle="How close to a bland AI default"
              lowLabel="Distinctive"
              highLabel="Generic"
              color="accent"
            />
            <ScoreDial
              label="Voice Distance"
              value={result?.scores.voice_distance ?? null}
              subtitle={fingerprint.isActive ? 'Drift from your voice' : 'Add samples to unlock'}
              lowLabel="Your voice"
              highLabel="Drifting"
              color="green"
            />
          </div>

          {/* Voice fingerprint onboarding */}
          <VoiceOnboarding
            fingerprint={fingerprint}
            onAddSamples={addSamples}
            onClear={clearFingerprint}
            loading={fpLoading}
            error={fpError}
          />
        </div>

        {/* Right panel */}
        <div style={styles.rightPanel}>
          <div style={styles.panelTitle}>Divergent Directions</div>
          <DirectionCards
            cards={result?.directions ?? []}
            loading={loading}
          />
        </div>
      </main>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  root: {
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
  },
  header: {
    borderBottom: '1px solid #2e3350',
    background: '#0f1117',
    padding: '0 24px',
  },
  headerInner: {
    maxWidth: '1400px',
    margin: '0 auto',
    padding: '16px 0',
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    flexWrap: 'wrap',
  },
  logo: {
    fontSize: '20px',
    fontWeight: 800,
    color: '#6b74f8',
    letterSpacing: '-0.3px',
  },
  tagline: {
    fontSize: '13px',
    color: '#7c829e',
  },
  demoBanner: {
    marginLeft: 'auto',
    fontSize: '11px',
    fontWeight: 600,
    color: '#f5a623',
    background: 'rgba(245,166,35,0.1)',
    border: '1px solid rgba(245,166,35,0.3)',
    borderRadius: '5px',
    padding: '4px 10px',
  },
  main: {
    flex: 1,
    maxWidth: '1400px',
    margin: '0 auto',
    width: '100%',
    padding: '28px 24px',
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '28px',
    alignItems: 'start',
  },
  leftPanel: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  rightPanel: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  panelTitle: {
    fontSize: '12px',
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.7px',
    color: '#7c829e',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  textarea: {
    background: '#1a1d27',
    border: '1px solid #2e3350',
    borderRadius: '10px',
    color: '#e8eaf0',
    fontSize: '14px',
    lineHeight: 1.65,
    padding: '14px 16px',
    resize: 'vertical',
    outline: 'none',
    width: '100%',
    transition: 'border-color 0.15s',
  },
  submitBtn: {
    background: '#6b74f8',
    border: 'none',
    borderRadius: '8px',
    color: '#fff',
    fontSize: '14px',
    fontWeight: 700,
    padding: '12px 24px',
    alignSelf: 'flex-start',
    transition: 'opacity 0.15s',
  },
  errorMsg: {
    fontSize: '13px',
    color: '#e5534b',
    background: 'rgba(229,83,75,0.08)',
    border: '1px solid rgba(229,83,75,0.25)',
    borderRadius: '7px',
    padding: '10px 14px',
  },
  dialsRow: {
    display: 'flex',
    gap: '12px',
    background: '#1a1d27',
    border: '1px solid #2e3350',
    borderRadius: '10px',
    padding: '20px 16px',
    justifyContent: 'center',
  },
}
