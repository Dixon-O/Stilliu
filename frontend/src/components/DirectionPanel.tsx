import React, { useState } from 'react'
import type { DirectionCard, DraftScores } from '@/api/client'
import AxisMeter from './AxisMeter'

/**
 * DirectionPanel — the results workspace.
 *
 * Directions are a grid of cards rather than a row of tabs. Tabs made comparing
 * the second direction against the fifth a memory exercise: you could only ever
 * see one set of scores at a time, and comparison is the entire point of this
 * tool. A grid puts every rewrite and every delta on screen together, which is
 * the one arrangement that lets you actually pick a winner.
 *
 * Each card still regenerates on its own — one model call, scored against the
 * same anchors, so its deltas stay comparable with the rest.
 */

export type SlotStatus = 'empty' | 'loading' | 'ready' | 'error'

export interface DirectionSlot {
  /** Style name. Doubles as the card heading and the React key. */
  style: string
  card: DirectionCard | null
  status: SlotStatus
  error?: string | null
  /** True when the controls have moved since this card was generated. */
  stale: boolean
}

interface Props {
  slots: DirectionSlot[]
  onGenerate: (style: string) => void
  /** The draft's own scores, pinned to each rail for comparison. */
  draftScores: DraftScores | null
  /** True while any request is in flight — keeps the writer from stacking calls. */
  busy: boolean
  /** Shown above the grid until a voice fingerprint exists. */
  voiceActive: boolean
  onOpenVoice: () => void
}

export default function DirectionPanel({
  slots,
  onGenerate,
  draftScores,
  busy,
  voiceActive,
  onOpenVoice,
}: Props) {
  return (
    <div className="pane__scroll">
      {!voiceActive && (
        <div className="nudge">
          <span>Add voice samples to see whether these rewrites still sound like you.</span>
          <button type="button" className="btn btn--sm nudge__action" onClick={onOpenVoice}>
            Add samples
          </button>
        </div>
      )}

      <div className="sectionhead">
        <h2>Directions</h2>
        <span className="note">
          {slots.length === 0
            ? 'nothing selected'
            : `${slots.length} selected · up to 6 per request`}
        </span>
      </div>

      <div className="legend">
        <span>
          <span className="meter__dot" style={{ background: 'var(--axis-dist)' }} />
          Distinctiveness
        </span>
        <span>
          <span className="meter__dot" style={{ background: 'var(--axis-voice)' }} />
          Voice Match
        </span>
        <span>
          <span className="meter__dot" style={{ background: 'var(--axis-onmsg)' }} />
          On-message
        </span>
        <span>
          <span className="legend__tick" />
          ghost tick = your draft's score on that axis
        </span>
      </div>

      {slots.length === 0 ? (
        <div className="empty">
          <span className="empty__rule" />
          <p style={S.emptyLead}>No directions yet</p>
          <p className="note" style={{ maxWidth: 380 }}>
            Write a draft on the left, pick up to six presets (or a custom brief) on the
            right, then hit <strong>Write directions</strong>. Every rewrite comes back
            with its axis scores and the delta versus your draft attached.
          </p>
        </div>
      ) : (
        <div className="cards">
          {slots.map((slot) => (
            <Card
              key={slot.style}
              slot={slot}
              draftScores={draftScores}
              busy={busy}
              onGenerate={onGenerate}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ── One direction ────────────────────────────────────────────────────────────

function Card({
  slot,
  draftScores,
  busy,
  onGenerate,
}: {
  slot: DirectionSlot
  draftScores: DraftScores | null
  busy: boolean
  onGenerate: (style: string) => void
}) {
  const [copied, setCopied] = useState(false)
  const [showFlags, setShowFlags] = useState(false)
  const card = slot.card

  function copy(text: string) {
    void navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    })
  }

  const flagged = !!card && card.faithfulness < 80
  const delta = card?.deltas.distinctiveness ?? null

  return (
    <article className={slot.status === 'loading' ? 'dcard dcard--pending' : 'dcard'}>
      <div className="dcard__head">
        <div className="dcard__title">
          <span className="dcard__name">{slot.style}</span>
          {card && (
            <div className="dcard__badges">
              {card.refined && (
                <span className="badge" title="The refine loop rewrote this to raise a weak axis">
                  refined
                </span>
              )}
              {flagged && (
                <button
                  type="button"
                  className="badge badge--warn"
                  onClick={() => setShowFlags((f) => !f)}
                  title={`Faithfulness ${card.faithfulness}/100 — click to see the claims`}
                >
                  check facts
                </button>
              )}
              {slot.stale && (
                <span className="badge" title="Your controls changed after this was written">
                  stale
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {slot.status === 'loading' && (
        <div style={S.shimmerStack}>
          {[100, 92, 97, 74].map((w, i) => (
            <div key={i} className="shimmer" style={{ width: `${w}%` }} />
          ))}
        </div>
      )}

      {slot.status === 'error' && (
        <>
          <p className="callout callout--err">{slot.error ?? 'This direction failed.'}</p>
          <button
            className="btn btn--sm"
            type="button"
            disabled={busy}
            onClick={() => onGenerate(slot.style)}
          >
            Try again
          </button>
        </>
      )}

      {slot.status === 'empty' && (
        <>
          <p className="note">
            Not written yet. Generate just this one, or run every style at once from the
            action bar.
          </p>
          <button
            className="btn btn--primary btn--sm"
            type="button"
            disabled={busy}
            onClick={() => onGenerate(slot.style)}
          >
            Write this direction
          </button>
        </>
      )}

      {slot.status === 'ready' && card && (
        <>
          <p className="note">{card.persona_description}</p>

          {slot.stale && (
            <p className="callout callout--warn">
              Your controls changed after this was written, so the scores below describe
              the older settings.
            </p>
          )}

          {showFlags && card.unsupported_claims.length > 0 && (
            <div className="callout callout--warn">
              <strong>Not found in your draft:</strong>{' '}
              {card.unsupported_claims.slice(0, 5).join(' · ')}
            </div>
          )}

          <p className="dcard__text">{card.text}</p>

          <div className="dcard__axes">
            <AxisMeter
              axis="dist"
              label="Distinct"
              value={card.scores.distinctiveness}
              baseline={draftScores?.distinctiveness ?? null}
              delta={card.deltas.distinctiveness}
              hint="100 means it departs boldly from bland AI defaults. The tick is your draft."
            />
            {(card.scores.voice_match != null || draftScores?.voice_match != null) && (
              <AxisMeter
                axis="voice"
                label="Voice"
                value={card.scores.voice_match}
                baseline={draftScores?.voice_match ?? null}
                delta={card.deltas.voice_match}
                tone="voice"
                hint="100 means it reads as yours, measured against your writing samples."
              />
            )}
            <AxisMeter
              axis="onmsg"
              label="On-message"
              value={card.scores.on_message}
              hint="100 means every point in your draft survived the rewrite. Measured against a neutral midpoint, not your draft."
            />
          </div>

          {delta != null && (
            <p
              className={
                delta >= 0.5
                  ? 'dcard__verdict dcard__verdict--good'
                  : delta <= -0.5
                    ? 'dcard__verdict dcard__verdict--bad'
                    : 'dcard__verdict note'
              }
            >
              {delta >= 0.5
                ? `${Math.abs(delta).toFixed(0)} points more distinctive than your draft.`
                : delta <= -0.5
                  ? `${Math.abs(delta).toFixed(0)} points less distinctive than your draft.`
                  : 'About as distinctive as your draft.'}
            </p>
          )}

          <div className="dcard__foot">
            <button
              className={copied ? 'btn btn--sm btn--done' : 'btn btn--sm'}
              type="button"
              onClick={() => copy(card.text)}
            >
              {copied ? 'Copied' : 'Copy'}
            </button>
            <button
              className="btn btn--sm"
              type="button"
              disabled={busy}
              onClick={() => onGenerate(slot.style)}
              title="One model call — the other directions are left alone"
            >
              Rewrite this one
            </button>
          </div>
        </>
      )}
    </article>
  )
}

const S: Record<string, React.CSSProperties> = {
  shimmerStack: { display: 'flex', flexDirection: 'column', gap: 8 },
  emptyLead: { fontFamily: 'var(--mono)', fontSize: 12.5, fontWeight: 700, color: 'var(--ink-2)' },
}
