import React, { useEffect, useMemo, useState } from 'react'
import {
  analyzeDraft,
  checkHealth,
  controlsSignature,
  DEFAULT_CONTROLS,
  fetchStyles,
  generateDirection,
  scoreDraft,
} from '@/api/client'
import type {
  DirectionCard,
  DraftScores,
  HealthResponse,
  StyleLibrary,
  WriterControls,
} from '@/api/client'
import AxisMeter from '@/components/AxisMeter'
import ControlsPanel from '@/components/ControlsPanel'
import DirectionPanel, { type DirectionSlot, type SlotStatus } from '@/components/DirectionPanel'
import { useVoiceFingerprint } from '@/hooks/useVoiceFingerprint'

const PLACEHOLDER = `Paste your draft here — an opening paragraph, a caption, a scene, an argument. Whatever you're working on.`

export default function App() {
  const [draft, setDraft] = useState('')

  // ── Style library (served from styles.py, so the backend owns the list) ────
  const [library, setLibrary] = useState<StyleLibrary | null>(null)
  const [libError, setLibError] = useState<string | null>(null)

  const [controls, setControls] = useState<WriterControls>(DEFAULT_CONTROLS)

  // ── Measurement ───────────────────────────────────────────────────────────
  const [draftScores, setDraftScores] = useState<DraftScores | null>(null)
  const [baselinePreview, setBaselinePreview] = useState('')
  /** The draft text the scores above describe, so we can tell when they go stale. */
  const [scoredFor, setScoredFor] = useState('')

  // ── Directions, keyed by style name so a tab keeps its card across reselects ─
  const [cards, setCards] = useState<Record<string, DirectionCard>>({})
  const [stamps, setStamps] = useState<Record<string, string>>({})
  const [cardErrors, setCardErrors] = useState<Record<string, string>>({})
  const [pending, setPending] = useState<string[]>([])
  const [wanted, setWanted] = useState<string | null>(null)

  const [scoring, setScoring] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [demoMode, setDemoMode] = useState(false)
  /** The full /health payload, so the popover can name the resolved models. */
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [healthOpen, setHealthOpen] = useState(false)

  const {
    fingerprint,
    loading: fpLoading,
    error: fpError,
    addSamples,
    clearFingerprint,
  } = useVoiceFingerprint()

  useEffect(() => {
    checkHealth()
      .then((h) => {
        setHealth(h)
        setDemoMode(h.demo_mode)
      })
      // No backend reachable is indistinguishable from demo mode from here, and
      // demo mode is the safe reading — it promises less.
      .catch(() => setDemoMode(true))
  }, [])

  // A popover that can only be dismissed by the button that opened it is a trap
  // for anyone who clicks past it, so close on outside click and on Escape.
  useEffect(() => {
    if (!healthOpen) return
    const onDown = (e: MouseEvent) => {
      if (!(e.target as Element | null)?.closest('.health')) setHealthOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setHealthOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [healthOpen])

  useEffect(() => {
    let cancelled = false
    fetchStyles()
      .then((lib) => { if (!cancelled) setLibrary(lib) })
      .catch((err) => {
        if (!cancelled) setLibError(err instanceof Error ? err.message : 'Failed to load styles')
      })
    return () => { cancelled = true }
  }, [])

  // ── Selection ─────────────────────────────────────────────────────────────
  // `personas === null` means the writer hasn't touched the picker, so the
  // backend's own defaults are what they'll get; we mirror that here. Once they
  // do touch it, the array is authoritative — including when it is empty.
  const selected = controls.personas ?? library?.defaults ?? []
  const customName = library?.custom_style_name ?? 'Your Custom Direction'
  const hasCustom = controls.custom_persona.trim().length > 0
  const maxTabs = library?.max_selected ?? 6

  /**
   * Every tab that should exist right now, in order — and only the tabs the
   * backend will actually fill. It caps the batch at `max_selected` and gives
   * the custom brief one of those slots, so mirroring that arithmetic here is
   * what stops a tab from sitting empty forever with no way to fill it.
   */
  const tabStyles = useMemo(() => {
    const room = hasCustom ? maxTabs - 1 : maxTabs
    const presets = selected.slice(0, Math.max(room, 0))
    return hasCustom ? [...presets, customName] : presets
  }, [selected, hasCustom, customName, maxTabs])

  function toggleStyle(name: string) {
    const on = selected.includes(name)
    const next = on ? selected.filter((n) => n !== name) : [...selected, name]
    // Always write the array, even when it ends up empty. `[]` means "cleared on
    // purpose" and the backend honours it as empty; collapsing it to `null` here
    // is what used to make deselecting everything silently snap back to the
    // three default styles.
    setControls((c) => ({ ...c, personas: next }))
    if (!on) setWanted(name)
  }

  const clearStyles = () => setControls((c) => ({ ...c, personas: [] }))
  const restoreDefaults = () =>
    setControls((c) => ({ ...c, personas: library ? [...library.defaults] : null }))

  // ── Staleness ─────────────────────────────────────────────────────────────
  // A card is out of date when either the controls or the draft have moved since
  // it was written. Recording the stamp per card is what lets us mark only the
  // affected tabs instead of blanking every result on any keystroke.
  const stamp = useMemo(
    // Joined as JSON rather than glued together with a separator character: it is
    // unambiguous by construction, so no draft can ever imitate the boundary, and
    // it keeps this file plain text. A literal NUL byte here made git treat the
    // whole file as binary and silently stopped diffing it.
    () => JSON.stringify([controlsSignature(controls), draft.trim()]),
    [controls, draft],
  )

  const busy = scoring || pending.length > 0
  const trimmed = draft.trim()
  const canGenerate = trimmed.length >= 10 && tabStyles.length > 0 && !busy
  const draftStale = draftScores !== null && trimmed !== scoredFor

  const slots: DirectionSlot[] = tabStyles.map((style) => {
    const card = cards[style] ?? null
    const err = cardErrors[style]
    const status: SlotStatus = pending.includes(style)
      ? 'loading'
      : err
        ? 'error'
        : card
          ? 'ready'
          : 'empty'
    return { style, card, status, error: err ?? null, stale: !!card && stamps[style] !== stamp }
  })

  const activeStyle = wanted && tabStyles.includes(wanted) ? wanted : (tabStyles[0] ?? null)
  const voiceSamples = fingerprint.isActive ? fingerprint.samples : undefined

  // ── Actions ───────────────────────────────────────────────────────────────

  /** Score the draft on its own — fast, no generation. */
  async function measure() {
    if (trimmed.length < 10 || busy) return
    setError(null)
    setScoring(true)
    try {
      const res = await scoreDraft(trimmed, voiceSamples)
      setDraftScores(res.draft_scores)
      setBaselinePreview(res.baseline_preview)
      setScoredFor(trimmed)
      if (res.demo_mode) setDemoMode(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Measuring the draft failed.')
    } finally {
      setScoring(false)
    }
  }

  /** Write every selected style in one batch. */
  async function generateAll() {
    if (!canGenerate) return
    const at = stamp
    setError(null)
    setCardErrors({})
    setPending(tabStyles)
    try {
      const res = await analyzeDraft(trimmed, voiceSamples, controls)
      setDraftScores(res.draft_scores)
      setBaselinePreview(res.baseline_preview)
      setScoredFor(trimmed)
      if (res.demo_mode) setDemoMode(true)

      const nextCards: Record<string, DirectionCard> = {}
      const nextStamps: Record<string, string> = {}
      for (const d of res.directions) {
        nextCards[d.persona] = d
        nextStamps[d.persona] = at
      }
      setCards((prev) => ({ ...prev, ...nextCards }))
      setStamps((prev) => ({ ...prev, ...nextStamps }))
      if (res.directions.length > 0) setWanted(res.directions[0].persona)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Generating directions failed.'
      setError(msg.includes('timed out') ? `${msg} Your draft scores are still valid.` : msg)
    } finally {
      setPending([])
    }
  }

  /**
   * Write one direction on its own.
   *
   * This is the granular path: change a control, rewrite only the direction
   * you're reading. One model call instead of up to six, and the backend scores
   * it against the same anchors so its deltas stay comparable with the rest.
   */
  async function generateOne(style: string) {
    if (trimmed.length < 10 || busy) return
    const at = stamp
    setError(null)
    setCardErrors((prev) => {
      const { [style]: _drop, ...rest } = prev
      return rest
    })
    setPending([style])
    setWanted(style)
    try {
      const res = await generateDirection(trimmed, voiceSamples, controls, style)
      setDraftScores(res.draft_scores)
      if (res.baseline_preview) setBaselinePreview(res.baseline_preview)
      setScoredFor(trimmed)
      if (res.demo_mode) setDemoMode(true)
      setCards((prev) => ({ ...prev, [style]: res.direction }))
      setStamps((prev) => ({ ...prev, [style]: at }))
    } catch (err) {
      setCardErrors((prev) => ({
        ...prev,
        [style]: err instanceof Error ? err.message : 'This direction failed.',
      }))
    } finally {
      setPending([])
    }
  }

  const words = trimmed ? trimmed.split(/\s+/).length : 0
  const generateLabel =
    pending.length > 1
      ? 'Writing…'
      : tabStyles.length === 0
        ? 'Nothing selected'
        : `Write ${tabStyles.length} direction${tabStyles.length === 1 ? '' : 's'}`

  return (
    <div className="app">
      <header className="topbar">
        <span className="wordmark">Stil<span>liu</span></span>
        <span className="tagline">Find what makes your writing unmistakable.</span>
        <span style={S.spacer} />

        {/* Which models are actually loaded, one click away. Reading /health
            rather than config is what stops this claiming a model the region
            never resolved. */}
        <div className="health">
          <button
            type="button"
            className="health__pill"
            aria-expanded={healthOpen}
            onClick={() => setHealthOpen((o) => !o)}
            title="Which models are serving this session"
          >
            <span className={demoMode ? 'health__dot health__dot--demo' : 'health__dot health__dot--live'} />
            {demoMode ? 'demo mode' : 'watsonx.ai · live'}
          </button>

          {healthOpen && (
            <div className="health__popover" role="dialog" aria-label="Resolved models">
              <span className="eyebrow">Resolved models</span>
              <div className="health__row">
                <span className="health__role">Creative</span>
                <span className="health__model">{health?.gen_model || '—'}</span>
              </div>
              <div className="health__row">
                <span className="health__role">Baseline anchor</span>
                <span className="health__model">{health?.baseline_model || '—'}</span>
              </div>
              <div className="health__row">
                <span className="health__role">Embedding</span>
                <span className="health__model">{health?.embed_model || '—'}</span>
              </div>
              <p className="health__note">
                {demoMode
                  ? 'Serving fixture responses — no API calls and no credentials needed. Every screen stays clickable.'
                  : 'Resolved against what this region actually hosts. The baseline is kept in a different provider family from the creative model, so distinctiveness is not measured against a colder run of the same model.'}
              </p>
            </div>
          )}
        </div>
      </header>

      <div className="workspace">
        {/* ── Left: the draft, then every control ──────────────────────────── */}
        <div className="col">
          <section className="card card--flex" style={S.draftCard} aria-label="Your draft">
            <div className="panel-head">
              <span className="eyebrow">Your draft</span>
              <span className="note note--right">
                {words} {words === 1 ? 'word' : 'words'}
                {draftStale && ' · edited since measuring'}
              </span>
            </div>

            <textarea
              className="draft-input"
              placeholder={PLACEHOLDER}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              aria-label="Your draft"
            />

            <div style={S.draftMeters}>
              <AxisMeter
                axis="dist"
                label="Distinctive"
                value={draftScores?.distinctiveness ?? null}
                hint="How far your draft already sits from bland AI defaults."
              />
              <AxisMeter
                axis="voice"
                label="Voice"
                value={draftScores?.voice_match ?? null}
                tone="voice"
                // Locked rather than zeroed until there are samples to measure
                // against. A guessed voice score would be the one number in this
                // tool that isn't derived from anything.
                lockedReason={fingerprint.isActive ? null : 'Needs your writing samples.'}
                hint={
                  fingerprint.isActive
                    ? 'How much your draft sounds like your samples.'
                    : 'Add writing samples in the Voice tab to unlock this axis.'
                }
              />
              {baselinePreview && (
                <p style={S.baseline} title={baselinePreview}>
                  Measured against: “{baselinePreview}…”
                </p>
              )}
            </div>
          </section>

          <ControlsPanel
            controls={controls}
            onChange={setControls}
            library={library}
            libError={libError}
            selected={selected}
            onToggleStyle={toggleStyle}
            onClearStyles={clearStyles}
            onRestoreDefaults={restoreDefaults}
            voiceActive={fingerprint.isActive}
            fingerprint={fingerprint}
            onAddSamples={addSamples}
            onClearVoice={clearFingerprint}
            voiceLoading={fpLoading}
            voiceError={fpError}
          />

          {error && (
            <p className="callout callout--err" role="alert">
              {error}
            </p>
          )}

          <div style={S.actions}>
            <button
              className="btn"
              type="button"
              onClick={measure}
              disabled={trimmed.length < 10 || busy}
              title="Score the draft on its own — no generation, so it comes back fast"
            >
              {scoring ? 'Measuring…' : 'Measure draft'}
            </button>
            <button
              className="btn btn--primary btn--grow"
              type="button"
              onClick={generateAll}
              disabled={!canGenerate}
            >
              {generateLabel}
            </button>
          </div>
        </div>

        {/* ── Right: one tab per direction ─────────────────────────────────── */}
        <div className="col">
          <DirectionPanel
            slots={slots}
            activeStyle={activeStyle}
            onSelect={setWanted}
            onGenerate={generateOne}
            draftScores={draftScores}
            busy={busy}
          />
        </div>
      </div>
    </div>
  )
}

// ── Layout-only styles; everything visual lives in index.css ──────────────────

const S: Record<string, React.CSSProperties> = {
  spacer: { flex: 1 },
  /**
   * The draft sizes itself to its content instead of claiming a share of the
   * column. It used to be `flex: 1 1 38%`, which meant an empty textarea still
   * took a third of the left side and squeezed the controls panel down to its
   * tab row. Now it grows only as the draft does, up to 44% of the column, and
   * everything it doesn't need goes to the controls below it.
   */
  draftCard: { flex: '0 1 auto', maxHeight: '44%' },
  draftMeters: {
    display: 'flex',
    flexDirection: 'column',
    gap: 7,
    padding: '10px 14px',
    borderTop: '1px solid var(--rule)',
    background: 'var(--well)',
    flex: 'none',
  },
  baseline: {
    fontFamily: 'var(--serif)',
    fontSize: 11.5,
    fontStyle: 'italic',
    color: 'var(--ink-3)',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  actions: { display: 'flex', gap: 8, flex: 'none' },
}
