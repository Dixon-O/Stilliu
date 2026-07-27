import React, { useState, useEffect } from 'react'
import { scoreDraft, analyzeDraft, checkHealth, DEFAULT_CONTROLS } from '@/api/client'
import type { AnalyzeResponse, DraftScores, WriterControls } from '@/api/client'
import ScoreDial from '@/components/ScoreDials'
import DirectionCards from '@/components/DirectionCards'
import ControlsPanel from '@/components/ControlsPanel'
import VoiceOnboarding from '@/components/VoiceOnboarding'
import { useVoiceFingerprint } from '@/hooks/useVoiceFingerprint'

const PLACEHOLDER = `Paste your draft here — an opening paragraph, a caption, a scene, an argument. Whatever you're working on. Stilliu measures how distinctive it sounds, then generates directions that push it further while keeping your voice.`

export default function App() {
  const [draft, setDraft] = useState('')
  const [draftScores, setDraftScores] = useState<DraftScores | null>(null)
  const [result, setResult] = useState<AnalyzeResponse | null>(null)
  const [baselinePreview, setBaselinePreview] = useState('')
  const [scoringLoading, setScoringLoading] = useState(false)
  const [directionsLoading, setDirectionsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [demoMode, setDemoMode] = useState(false)
  const [modelInfo, setModelInfo] = useState('')
  const [controls, setControls] = useState<WriterControls>(DEFAULT_CONTROLS)

  const { fingerprint, loading: fpLoading, error: fpError, addSamples, clearFingerprint } = useVoiceFingerprint()

  useEffect(() => {
    checkHealth()
      .then(h => {
        setDemoMode(h.demo_mode)
        if (h.embed_model) setModelInfo(`${h.embed_model} · ${h.gen_model}`)
      })
      .catch(() => setDemoMode(true))
  }, [])

  async function handleAnalyze(e: React.FormEvent) {
    e.preventDefault()
    if (!draft.trim()) return

    const samples = fingerprint.isActive ? fingerprint.samples : undefined
    setError(null)
    setResult(null)
    setDraftScores(null)

    setScoringLoading(true)
    try {
      const scoreRes = await scoreDraft(draft.trim(), samples)
      setDraftScores(scoreRes.draft_scores)
      setBaselinePreview(scoreRes.baseline_preview)
      if (scoreRes.demo_mode) setDemoMode(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Scoring failed. Please try again.')
      setScoringLoading(false)
      return
    } finally {
      setScoringLoading(false)
    }

    setDirectionsLoading(true)
    try {
      const fullRes = await analyzeDraft(draft.trim(), samples, controls)
      setResult(fullRes)
      setDraftScores(fullRes.draft_scores)
      setBaselinePreview(fullRes.baseline_preview)
      if (fullRes.demo_mode) setDemoMode(true)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Direction generation failed.'
      setError(msg.includes('timed out') ? `${msg} Scores above are still valid.` : msg)
    } finally {
      setDirectionsLoading(false)
    }
  }

  const loading = scoringLoading || directionsLoading

  return (
    <div style={styles.root}>
      <header style={styles.header}>
        <div style={styles.headerInner}>
          <div style={styles.logo}>Stilliu</div>
          <div style={styles.tagline}>Find what makes your writing unmistakable.</div>
          {modelInfo && !demoMode && <div style={styles.modelInfo}>{modelInfo}</div>}
          {demoMode && <div style={styles.demoBanner}>Demo mode — fixture responses · no API calls</div>}
        </div>
      </header>

      <main style={styles.main}>
        {/* Left panel */}
        <div style={styles.leftPanel}>
          <form onSubmit={handleAnalyze} style={styles.form}>
            <textarea style={styles.textarea} placeholder={PLACEHOLDER}
              value={draft} onChange={e => setDraft(e.target.value)} rows={10} />
            <button type="submit"
              style={loading ? { ...styles.submitBtn, opacity: 0.6 } : styles.submitBtn}
              disabled={loading || !draft.trim()}>
              {scoringLoading ? 'Measuring…' : directionsLoading ? 'Generating directions…' : 'Analyse'}
            </button>
          </form>

          {error && <div style={styles.errorMsg}>{error}</div>}

          {/* Draft scores — high = good */}
          <div style={styles.dialsRow}>
            <ScoreDial
              label="Distinctiveness"
              value={draftScores?.distinctiveness ?? null}
              subtitle="How far your draft is from bland AI defaults"
              lowLabel="Generic" highLabel="Bold"
            />
            <ScoreDial
              label="Voice match"
              value={draftScores?.voice_match ?? null}
              subtitle={fingerprint.isActive ? 'How much it sounds like you' : 'Add samples to unlock'}
              lowLabel="Drifting" highLabel="Yours" color="green"
            />
          </div>

          {baselinePreview && (
            <div style={styles.baselineBox}>
              <span style={styles.baselineLabel}>Bland baseline it's measured against:</span>
              <span style={styles.baselineText}>"{baselinePreview}…"</span>
            </div>
          )}

          <ControlsPanel controls={controls} onChange={setControls} voiceActive={fingerprint.isActive} />

          <VoiceOnboarding fingerprint={fingerprint} onAddSamples={addSamples}
            onClear={clearFingerprint} loading={fpLoading} error={fpError} />
        </div>

        {/* Right panel */}
        <div style={styles.rightPanel}>
          <div style={styles.panelTitle}>Divergent Directions</div>
          <p style={styles.panelHint}>
            Each direction shows three axes vs your draft: how much bolder, how well it holds your voice, and whether it stayed on message.
          </p>
          <DirectionCards
            cards={result?.directions ?? []}
            loading={directionsLoading}
            draftDistinctiveness={draftScores?.distinctiveness}
            draftVoiceMatch={draftScores?.voice_match}
          />
        </div>
      </main>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  root: { minHeight: '100vh', display: 'flex', flexDirection: 'column' },
  header: { borderBottom: '1px solid #2e3350', background: '#0f1117', padding: '0 24px' },
  headerInner: {
    maxWidth: '1400px', margin: '0 auto', padding: '16px 0',
    display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap',
  },
  logo: { fontSize: '20px', fontWeight: 800, color: '#6b74f8', letterSpacing: '-0.3px' },
  tagline: { fontSize: '13px', color: '#7c829e' },
  modelInfo: {
    marginLeft: 'auto', fontSize: '11px', color: '#7c829e', background: '#1a1d27',
    border: '1px solid #2e3350', borderRadius: '5px', padding: '4px 10px',
    fontFamily: '"Cascadia Code", "Fira Code", "Courier New", monospace',
  },
  demoBanner: {
    marginLeft: 'auto', fontSize: '11px', fontWeight: 600, color: '#f5a623',
    background: 'rgba(245,166,35,0.1)', border: '1px solid rgba(245,166,35,0.3)',
    borderRadius: '5px', padding: '4px 10px',
  },
  main: {
    flex: 1, maxWidth: '1400px', margin: '0 auto', width: '100%', padding: '28px 24px',
    display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '28px', alignItems: 'start',
  },
  leftPanel: { display: 'flex', flexDirection: 'column', gap: '20px' },
  rightPanel: { display: 'flex', flexDirection: 'column', gap: '10px' },
  panelTitle: {
    fontSize: '12px', fontWeight: 700, textTransform: 'uppercase',
    letterSpacing: '0.7px', color: '#7c829e',
  },
  panelHint: { fontSize: '12px', color: '#7c829e', lineHeight: 1.5, margin: '0 0 6px' },
  form: { display: 'flex', flexDirection: 'column', gap: '12px' },
  textarea: {
    background: '#1a1d27', border: '1px solid #2e3350', borderRadius: '10px',
    color: '#e8eaf0', fontSize: '14px', lineHeight: 1.65, padding: '14px 16px',
    resize: 'vertical', outline: 'none', width: '100%', transition: 'border-color 0.15s',
  },
  submitBtn: {
    background: '#6b74f8', border: 'none', borderRadius: '8px', color: '#fff',
    fontSize: '14px', fontWeight: 700, padding: '12px 24px', alignSelf: 'flex-start',
    transition: 'opacity 0.15s', cursor: 'pointer',
  },
  errorMsg: {
    fontSize: '13px', color: '#e5534b', background: 'rgba(229,83,75,0.08)',
    border: '1px solid rgba(229,83,75,0.25)', borderRadius: '7px', padding: '10px 14px',
  },
  dialsRow: {
    display: 'flex', gap: '12px', background: '#1a1d27', border: '1px solid #2e3350',
    borderRadius: '10px', padding: '20px 16px', justifyContent: 'center',
  },
  baselineBox: {
    display: 'flex', flexDirection: 'column', gap: '4px',
    background: '#141720', border: '1px solid #2e3350', borderRadius: '8px', padding: '10px 12px',
  },
  baselineLabel: { fontSize: '10px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px', color: '#7c829e' },
  baselineText: { fontSize: '12px', color: '#9297ad', fontStyle: 'italic', lineHeight: 1.5 },
}
