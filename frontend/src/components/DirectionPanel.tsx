import React, { useState } from 'react'
import type { DirectionCard, DraftScores } from '@/api/client'
import AxisMeter from './AxisMeter'

/**
 * DirectionPanel — the output side, one tab per style.
 *
 * Directions used to stack vertically, which meant comparing the second against
 * the fifth was a scrolling exercise and the axis scores of the one you were
 * reading were usually off-screen. Tabs put every direction's identifier along
 * the top, keep the three meters fixed in place as you switch, and let a single
 * direction be regenerated on its own — so tweaking one control costs one model
 * call instead of the whole batch.
 */

export type SlotStatus = 'empty' | 'loading' | 'ready' | 'error'

export interface DirectionSlot {
  /** Style name. Doubles as the tab label and the React key. */
  style: string
  card: DirectionCard | null
  status: SlotStatus
  error?: string | null
  /** True when the controls have moved since this card was generated. */
  stale: boolean
}

interface Props {
  slots: DirectionSlot[]
  activeStyle: string | null
  onSelect: (style: string) => void
  onGenerate: (style: string) => void
  /** The draft's own scores, pinned to each rail for comparison. */
  draftScores: DraftScores | null
  /** True while any request is in flight — keeps the writer from stacking calls. */
  busy: boolean
}

export default function DirectionPanel({
  slots,
  activeStyle,
  onSelect,
  onGenerate,
  draftScores,
  busy,
}: Props) {
  const [copied, setCopied] = useState(false)
  const [showDetail, setShowDetail] = useState(false)

  // Falls back to the first tab, so a style that has just been deselected can
  // never leave the panel pointing at nothing.
  const activeIndex = Math.max(slots.findIndex((s) => s.style === activeStyle), 0)
  const active = slots[activeIndex] ?? null
  const card = active?.card ?? null

  function copy(text: string) {
    void navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    })
  }

  if (slots.length === 0) {
    return (
      <section className="card card--flex" style={S.card} aria-label="Directions">
        <div className="empty">
          <span className="empty__rule" />
          <p style={S.emptyLead}>No directions yet</p>
          <p className="note" style={{ maxWidth: 340 }}>
            Pick your styles on the left, paste a draft, then generate. Each style becomes
            its own tab up here, measured against your draft on three axes.
          </p>
        </div>
      </section>
    )
  }

  return (
    <section className="card card--flex" style={S.card} aria-label="Directions">
      <div className="tabs" role="tablist" aria-label="Generated directions">
        {slots.map((s, i) => (
          <button
            key={s.style}
            role="tab"
            type="button"
            className="tab"
            // Style names carry spaces and apostrophes, so the tab/panel pairing
            // is keyed by position rather than by the label itself.
            id={`dir-tab-${i}`}
            aria-controls="dir-panel"
            aria-selected={active?.style === s.style}
            onClick={() => {
              onSelect(s.style)
              setShowDetail(false)
            }}
            title={
              s.status === 'empty'
                ? 'Not generated yet'
                : s.stale
                  ? 'Your controls changed after this was written'
                  : undefined
            }
          >
            {s.style}
            {s.status === 'loading' && <span style={S.pulse}>·</span>}
            {s.status === 'error' && <span style={S.errMark}>!</span>}
            {s.status === 'empty' && <span style={S.emptyMark}>+</span>}
            {s.status === 'ready' && s.stale && <span className="tab__dot" />}
          </button>
        ))}
      </div>

      {/* ── Measurement, fixed in place so switching tabs compares like for like ── */}
      {active && (
        <>
          <div className="legend">
            <span><span className="meter__dot" style={{ background: 'var(--axis-dist)' }} />Distinctive — distance from bland AI defaults</span>
            <span><span className="meter__dot" style={{ background: 'var(--axis-voice)' }} />Voice — how much it sounds like you</span>
            <span><span className="meter__dot" style={{ background: 'var(--axis-onmsg)' }} />On-message — meaning preserved</span>
            <span style={S.legendTick}><span className="legend__tick" />Your draft</span>
          </div>

          <div style={S.meters}>
            <AxisMeter
              axis="dist"
              label="Distinctive"
              value={card ? card.scores.distinctiveness : null}
              baseline={draftScores?.distinctiveness ?? null}
              delta={card ? card.deltas.distinctiveness : null}
              hint="100 means it departs boldly from bland AI defaults. The tick is your draft."
            />
            {(card?.scores.voice_match != null || draftScores?.voice_match != null) && (
              <AxisMeter
                axis="voice"
                label="Voice"
                value={card ? card.scores.voice_match : null}
                baseline={draftScores?.voice_match ?? null}
                delta={card ? card.deltas.voice_match : null}
                tone="voice"
                hint="100 means it reads as yours, measured against your writing samples."
              />
            )}
            <AxisMeter
              axis="onmsg"
              label="On-message"
              value={card ? card.scores.on_message : null}
              hint="100 means every point in your draft survived the rewrite. Reported against a neutral midpoint, not your draft — a draft is trivially 100% on-message with itself."
            />
          </div>
        </>
      )}

      {/* ── The direction itself ─────────────────────────────────────────────── */}
      <div
        className="scroll"
        role="tabpanel"
        id="dir-panel"
        aria-labelledby={`dir-tab-${activeIndex}`}
        style={S.body}
      >
        {active?.status === 'loading' && (
          <div style={S.shimmerStack}>
            {[100, 94, 88, 97, 72, 90, 60].map((w, i) => (
              <div key={i} className="shimmer" style={{ width: `${w}%` }} />
            ))}
          </div>
        )}

        {active?.status === 'error' && (
          <div style={S.stack}>
            <p className="callout callout--err">{active.error ?? 'This direction failed.'}</p>
            <button
              className="btn btn--sm"
              type="button"
              disabled={busy}
              onClick={() => onGenerate(active.style)}
            >
              Try again
            </button>
          </div>
        )}

        {active?.status === 'empty' && (
          <div className="empty">
            <span className="empty__rule" />
            <p style={S.emptyLead}>{active.style}</p>
            <p className="note" style={{ maxWidth: 320 }}>
              Not written yet. Generate just this one, or run every style at once from the
              left.
            </p>
            <button
              className="btn btn--primary btn--sm"
              type="button"
              disabled={busy}
              onClick={() => onGenerate(active.style)}
              style={{ marginTop: 4 }}
            >
              Write this direction
            </button>
          </div>
        )}

        {active?.status === 'ready' && card && (
          <div style={S.stack}>
            <div style={S.head}>
              <p className="note" style={{ flex: 1 }}>{card.persona_description}</p>
              {card.refined && (
                <span className="badge" title="The refine loop rewrote this to raise a weak axis">
                  refined
                </span>
              )}
              {card.faithfulness < 80 && (
                <span className="badge badge--warn" title={`Faithfulness ${card.faithfulness}/100`}>
                  check facts
                </span>
              )}
            </div>

            {active.stale && (
              <div className="callout callout--warn" style={S.staleRow}>
                <span style={{ flex: 1 }}>
                  Your controls changed after this was written, so the scores below describe
                  the older settings.
                </span>
                <button
                  className="btn btn--sm"
                  type="button"
                  disabled={busy}
                  onClick={() => onGenerate(active.style)}
                >
                  Rewrite with new controls
                </button>
              </div>
            )}

            {card.faithfulness < 80 && card.unsupported_claims.length > 0 && (
              <div className="callout callout--warn">
                <strong>Not found in your draft:</strong>{' '}
                {card.unsupported_claims.slice(0, 4).join(' · ')}
              </div>
            )}

            <p className="prose">{card.text}</p>

            {showDetail && card.summary && (
              <div className="quote-well">
                <span className="note">{card.summary}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Actions, pinned so Copy never scrolls away ───────────────────────── */}
      {active?.status === 'ready' && card && (
        <div style={S.footer}>
          <button
            className={copied ? 'btn btn--sm btn--done' : 'btn btn--sm'}
            type="button"
            onClick={() => copy(card.text)}
          >
            {copied ? 'Copied' : 'Copy this direction'}
          </button>
          <button
            className="btn btn--sm"
            type="button"
            disabled={busy}
            onClick={() => onGenerate(active.style)}
            title="One model call — the other directions are left alone"
          >
            Rewrite this one
          </button>
          {card.summary && (
            <button
              className="btn btn--quiet btn--sm"
              type="button"
              onClick={() => setShowDetail((d) => !d)}
            >
              {showDetail ? 'Hide score detail' : 'Score detail'}
            </button>
          )}
        </div>
      )}
    </section>
  )
}

const S: Record<string, React.CSSProperties> = {
  card: { flex: 1, minHeight: 0 },
  meters: {
    display: 'flex',
    flexDirection: 'column',
    gap: 7,
    padding: '11px 14px',
    borderBottom: '1px solid var(--rule)',
    background: 'var(--well)',
    flex: 'none',
  },
  body: { flex: 1, padding: '14px 16px' },
  stack: { display: 'flex', flexDirection: 'column', gap: 11 },
  head: { display: 'flex', alignItems: 'flex-start', gap: 7, flexWrap: 'wrap' },
  staleRow: { display: 'flex', alignItems: 'center', gap: 9, flexWrap: 'wrap' },
  shimmerStack: { display: 'flex', flexDirection: 'column', gap: 9 },
  footer: {
    display: 'flex',
    gap: 7,
    flexWrap: 'wrap',
    padding: '10px 14px',
    borderTop: '1px solid var(--rule)',
    flex: 'none',
  },
  legendTick: { marginLeft: 'auto' },
  emptyLead: { fontFamily: 'var(--mono)', fontSize: 12.5, fontWeight: 700, color: 'var(--ink-2)' },
  pulse: { color: 'var(--accent)', fontWeight: 900, fontSize: 16, lineHeight: 0 },
  errMark: { color: 'var(--low)', fontWeight: 900 },
  emptyMark: { color: 'var(--ink-3)', fontWeight: 900 },
}
