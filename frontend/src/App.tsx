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
import type { DirectionCard, DraftScores, StyleLibrary, WriterControls } from '@/api/client'
import AxisMeter from '@/components/AxisMeter'
import ControlsPanel, { type ControlsView, CONTROL_KEYS } from '@/components/ControlsPanel'
import DirectionPanel, { type DirectionSlot, type SlotStatus } from '@/components/DirectionPanel'
import VoiceOnboarding from '@/components/VoiceOnboarding'
import { useVoiceFingerprint } from '@/hooks/useVoiceFingerprint'

/**
 * App — the instrument shell.
 *
 * Three columns, each answering one question and never more than one: the left is
 * *your writing* (the draft, and the samples it gets compared against), the
 * middle is *what came back*, the right is *what to ask for*. The action bar sits
 * above all three because Score and Write apply to the whole workspace, not to
 * whichever column happens to be focused.
 *
 * The arrangement matters for the demo: input, output and controls are visible
 * simultaneously, so tweaking a control and watching one card's delta move is a
 * single glance rather than a navigation exercise.
 */

const PLACEHOLDER = `Paste or write the paragraph you want to measure and rewrite…`

/** Left-column tabs. Both are the writer's own prose, which is why they pair. */
type SourceTab = 'draft' | 'voice'

/** Which column is showing when the viewport is too narrow for three. */
type MobilePane = 'source' | 'results' | 'controls'

const MOBILE_PANES: { id: MobilePane; label: string }[] = [
  { id: 'source',   label: 'Draft' },
  { id: 'results',  label: 'Results' },
  { id: 'controls', label: 'Style & controls' },
]

const SAMPLE_DRAFT =
  'Our platform leverages cutting-edge artificial intelligence to revolutionize how ' +
  'teams collaborate. By seamlessly integrating with your existing workflow, we ' +
  'empower organizations to unlock unprecedented productivity gains and drive ' +
  'meaningful business outcomes at scale.'

export default function App() {
  const [draft, setDraft] = useState('')
  const [sourceTab, setSourceTab] = useState<SourceTab>('draft')
  const [controlsView, setControlsView] = useState<ControlsView>('presets')
  /**
   * Which column is visible below 980px. Above that the CSS shows all three and
   * this is ignored, so one piece of state serves both layouts rather than the
   * component having to know the viewport width.
   */
  const [mobilePane, setMobilePane] = useState<MobilePane>('source')

  // ── Style library (served from styles.py, so the backend owns the list) ────
  const [library, setLibrary] = useState<StyleLibrary | null>(null)
  const [libError, setLibError] = useState<string | null>(null)

  const [controls, setControls] = useState<WriterControls>(DEFAULT_CONTROLS)

  // ── Measurement ───────────────────────────────────────────────────────────
  const [draftScores, setDraftScores] = useState<DraftScores | null>(null)
  const [baselinePreview, setBaselinePreview] = useState('')
  /** The draft text the scores above describe, so we can tell when they go stale. */
  const [scoredFor, setScoredFor] = useState('')

  // ── Directions, keyed by style name so a card keeps its result across reselects ─
  const [cards, setCards] = useState<Record<string, DirectionCard>>({})
  const [stamps, setStamps] = useState<Record<string, string>>({})
  const [cardErrors, setCardErrors] = useState<Record<string, string>>({})
  const [pending, setPending] = useState<string[]>([])

  const [scoring, setScoring] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [demoMode, setDemoMode] = useState(false)
  const [health, setHealth] = useState<{ embed: string; gen: string; baseline: string } | null>(null)
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
        setDemoMode(h.demo_mode)
        setHealth({ embed: h.embed_model, gen: h.gen_model, baseline: h.baseline_model })
      })
      .catch(() => setDemoMode(true))
  }, [])

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
   * Every card that should exist right now, in order — and only the cards the
   * backend will actually fill. It caps the batch at `max_selected` and gives the
   * custom brief one of those slots, so mirroring that arithmetic here is what
   * stops a card from sitting empty forever with no way to fill it.
   */
  const cardStyles = useMemo(() => {
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
  }

  const clearStyles = () => setControls((c) => ({ ...c, personas: [] }))
  const restoreDefaults = () =>
    setControls((c) => ({ ...c, personas: library ? [...library.defaults] : null }))

  // ── Staleness ─────────────────────────────────────────────────────────────
  // A card is out of date when either the controls or the draft have moved since
  // it was written. Recording the stamp per card is what lets us mark only the
  // affected cards instead of blanking every result on any keystroke.
  const stamp = useMemo(
    () => `${controlsSignature(controls)} ${draft.trim()}`,
    [controls, draft],
  )

  const busy = scoring || pending.length > 0
  const trimmed = draft.trim()
  const canGenerate = trimmed.length >= 10 && cardStyles.length > 0 && !busy
  const draftStale = draftScores !== null && trimmed !== scoredFor

  const slots: DirectionSlot[] = cardStyles.map((style) => {
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

  const voiceSamples = fingerprint.isActive ? fingerprint.samples : undefined

  /** How many controls sit off their default — the count on the Controls tab. */
  const movedControls = CONTROL_KEYS.filter((k) => controls[k] !== DEFAULT_CONTROLS[k]).length

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
    setPending(cardStyles)
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
      : cardStyles.length === 0
        ? 'Nothing selected'
        : `Write ${cardStyles.length} direction${cardStyles.length === 1 ? '' : 's'}`

  return (
    <div className="app">
      {/* ── Identity, and what's actually running ─────────────────────────── */}
      <header className="topbar">
        <div className="brand">
          <span className="brand__mark" aria-hidden="true">S</span>
          <span className="brand__text">
            <span className="wordmark">Stil<span>liu</span></span>
            <span className="tagline">instrument panel for prose distinctiveness</span>
          </span>
        </div>

        <span style={S.spacer} />

        <span className="badge">IBM AI Builders Challenge · Jul 2026</span>

        <div style={S.healthWrap}>
          <button
            type="button"
            className={demoMode ? 'health health--demo' : 'health health--live'}
            aria-expanded={healthOpen}
            onClick={() => setHealthOpen((o) => !o)}
          >
            <span className="health__dot" aria-hidden="true" />
            {demoMode ? 'Demo mode' : 'watsonx.ai · live'}
          </button>

          {healthOpen && (
            <>
              {/* Click-away layer. Without it the popover can only be closed by
                  hitting the same pill again, which is a trap on touch. */}
              <div style={S.scrim} onClick={() => setHealthOpen(false)} aria-hidden="true" />
              <div className="popover" role="dialog" aria-label="Runtime models">
                {demoMode ? (
                  <p className="note">
                    Running on fixture responses — no API calls leave this machine. Set
                    credentials in <code>backend/.env</code> to go live.
                  </p>
                ) : (
                  <>
                    <p className="note" style={S.popLead}>
                      Resolved against what this region actually hosts, not what the config
                      asked for.
                    </p>
                    <dl className="popover__rows">
                      <dt>creative</dt>
                      <dd>{health?.gen || '—'}</dd>
                      <dt>baseline</dt>
                      <dd>{health?.baseline || '—'}</dd>
                      <dt>embedding</dt>
                      <dd>{health?.embed || '—'}</dd>
                    </dl>
                  </>
                )}
              </div>
            </>
          )}
        </div>
      </header>

      {/* ── One action bar for the whole workspace ────────────────────────── */}
      <div className="actionbar">
        <button
          className="btn"
          type="button"
          onClick={measure}
          disabled={trimmed.length < 10 || busy}
          title="Score the draft on its own — no generation, so it comes back fast"
        >
          {scoring ? 'Measuring…' : 'Score draft'}
        </button>
        <button
          className="btn btn--primary"
          type="button"
          onClick={generateAll}
          disabled={!canGenerate}
        >
          {generateLabel}
        </button>

        <span className="stat">
          {words} {words === 1 ? 'word' : 'words'}
          {draftStale && ' · edited since scoring'}
        </span>
        <span className="stat">
          <span
            className="health__dot"
            style={{ background: fingerprint.isActive ? 'var(--high)' : 'var(--rule-firm)' }}
            aria-hidden="true"
          />
          {fingerprint.isActive
            ? `voice set · ${fingerprint.samples.length} samples`
            : 'no voice set'}
        </span>

        <span style={S.spacer} />

        {error && (
          <span className="callout callout--err" role="alert" style={S.barError}>
            {error}
          </span>
        )}
      </div>

      {/* Only reachable below 980px, where three columns will not fit. */}
      <div className="mobiletabs" role="tablist" aria-label="Workspace column">
        {MOBILE_PANES.map((p) => (
          <button
            key={p.id}
            role="tab"
            type="button"
            id={`pane-tab-${p.id}`}
            aria-controls={`pane-${p.id}`}
            className={mobilePane === p.id ? 'btn btn--sm btn--primary' : 'btn btn--sm'}
            aria-selected={mobilePane === p.id}
            onClick={() => setMobilePane(p.id)}
          >
            {p.label}
          </button>
        ))}
      </div>

      <div className="workspace">
        {/* ── Left: your writing ───────────────────────────────────────────── */}
        <section
          id="pane-source"
          role="tabpanel"
          aria-labelledby="pane-tab-source"
          className={mobilePane === 'source' ? 'pane pane--active' : 'pane'}
          aria-label="Your writing"
        >
          <div className="pane__tabs" role="tablist" aria-label="Source">
            <button
              role="tab"
              type="button"
              id="src-tab-draft"
              aria-controls="src-panel"
              className="pane__tab"
              aria-selected={sourceTab === 'draft'}
              onClick={() => setSourceTab('draft')}
            >
              Draft
            </button>
            <button
              role="tab"
              type="button"
              id="src-tab-voice"
              aria-controls="src-panel"
              className="pane__tab"
              aria-selected={sourceTab === 'voice'}
              onClick={() => setSourceTab('voice')}
            >
              Voice samples
              {fingerprint.samples.length > 0 && (
                <span className="tab__count">{fingerprint.samples.length}</span>
              )}
            </button>
          </div>

          {sourceTab === 'draft' ? (
            <div
              id="src-panel"
              role="tabpanel"
              aria-labelledby="src-tab-draft"
              style={S.draftWrap}
            >
              <textarea
                className="draft-input"
                placeholder={PLACEHOLDER}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                aria-label="Your draft"
              />

              <div style={S.draftFoot}>
                <span className="note">{draft.length} characters</span>
                <span style={S.spacer} />
                {draft.length === 0 && (
                  <button
                    className="btn btn--quiet btn--sm"
                    type="button"
                    onClick={() => setDraft(SAMPLE_DRAFT)}
                    title="Loads a deliberately bland paragraph, so the scores have somewhere to go"
                  >
                    Load sample
                  </button>
                )}
                <button
                  className="btn btn--quiet btn--sm"
                  type="button"
                  onClick={() => setDraft('')}
                  disabled={draft.length === 0}
                >
                  Clear
                </button>
              </div>

              <div style={S.draftMeters}>
                <AxisMeter
                  axis="dist"
                  label="Distinct"
                  value={draftScores?.distinctiveness ?? null}
                  hint="How far your draft already sits from bland AI defaults."
                />
                <AxisMeter
                  axis="voice"
                  label="Voice"
                  value={draftScores?.voice_match ?? null}
                  tone="voice"
                  // Locked rather than zeroed: a voice score with nothing to
                  // compare against would be the one number here not derived
                  // from anything.
                  lockedReason={fingerprint.isActive ? null : 'Needs your writing samples.'}
                  onUnlock={() => setSourceTab('voice')}
                  hint="How much your draft sounds like your samples."
                />
                {baselinePreview && (
                  <p style={S.baseline} title={baselinePreview}>
                    Measured against: “{baselinePreview}…”
                  </p>
                )}
              </div>
            </div>
          ) : (
            <div
              id="src-panel"
              role="tabpanel"
              aria-labelledby="src-tab-voice"
              className="pane__scroll"
            >
              <VoiceOnboarding
                fingerprint={fingerprint}
                onAddSamples={addSamples}
                onClear={clearFingerprint}
                loading={fpLoading}
                error={fpError}
              />
            </div>
          )}
        </section>

        {/* ── Middle: what came back ───────────────────────────────────────── */}
        <section
          id="pane-results"
          role="tabpanel"
          aria-labelledby="pane-tab-results"
          className={
            mobilePane === 'results'
              ? 'pane pane--center pane--active'
              : 'pane pane--center'
          }
          aria-label="Directions"
        >
          <DirectionPanel
            slots={slots}
            onGenerate={generateOne}
            draftScores={draftScores}
            busy={busy}
            voiceActive={fingerprint.isActive}
            onOpenVoice={() => setSourceTab('voice')}
          />
        </section>

        {/* ── Right: what to ask for ───────────────────────────────────────── */}
        <section
          id="pane-controls"
          role="tabpanel"
          aria-labelledby="pane-tab-controls"
          className={mobilePane === 'controls' ? 'pane pane--active' : 'pane'}
          aria-label="Writer controls"
        >
          <div className="pane__tabs" role="tablist" aria-label="Controls">
            <button
              role="tab"
              type="button"
              id="ctl-view-presets"
              aria-controls="ctl-view-panel"
              className="pane__tab"
              aria-selected={controlsView === 'presets'}
              onClick={() => setControlsView('presets')}
            >
              Style presets
              {selected.length > 0 && <span className="tab__count">{selected.length}</span>}
            </button>
            <button
              role="tab"
              type="button"
              id="ctl-view-controls"
              aria-controls="ctl-view-panel"
              className="pane__tab"
              aria-selected={controlsView === 'controls'}
              onClick={() => setControlsView('controls')}
            >
              Controls
              {movedControls > 0 && <span className="tab__count">{movedControls}</span>}
            </button>
          </div>

          <ControlsPanel
            id="ctl-view-panel"
            labelledBy={controlsView === 'presets' ? 'ctl-view-presets' : 'ctl-view-controls'}
            view={controlsView}
            controls={controls}
            onChange={setControls}
            library={library}
            libError={libError}
            selected={selected}
            onToggleStyle={toggleStyle}
            onClearStyles={clearStyles}
            onRestoreDefaults={restoreDefaults}
            voiceActive={fingerprint.isActive}
          />
        </section>
      </div>

      <footer className="footbar">
        <span>Stilliu — built on watsonx.ai for the IBM AI Builders Challenge, Jul 2026</span>
        <span style={S.spacer} />
        <span>High is good, on every axis</span>
      </footer>
    </div>
  )
}

// ── Layout-only styles; everything visual lives in index.css ──────────────────

const S: Record<string, React.CSSProperties> = {
  spacer: { flex: 1 },
  healthWrap: { position: 'relative' },
  scrim: { position: 'fixed', inset: 0, zIndex: 40 },
  popLead: { marginBottom: 8 },
  barError: { flex: '0 1 auto', maxWidth: '46%' },
  draftWrap: { display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 },
  draftFoot: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    padding: '6px 12px',
    borderTop: '1px solid var(--rule)',
    flex: 'none',
  },
  draftMeters: {
    display: 'flex',
    flexDirection: 'column',
    gap: 7,
    padding: '11px 14px',
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
}
