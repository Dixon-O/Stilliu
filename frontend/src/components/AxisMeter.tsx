import React from 'react'

/**
 * AxisMeter — one measured axis, drawn as a rail rather than a dial.
 *
 * Stilliu's whole claim is that it can tell you whether a rewrite actually
 * worked, so the *comparison* has to be the visible thing. The rail carries the
 * direction's score as a fill and the draft's own score as a ghost tick, which
 * makes the improvement a literal gap you can see across all three axes at a
 * glance. It is also a fraction of a dial's height, which is what lets the whole
 * instrument fit one screen.
 *
 * High is good on every axis, so the colour ramp reads in one direction.
 */

/** Which axis this is. Drives the identity dot, so a rail is recognisable
 *  before its label is read. */
export type Axis = 'dist' | 'voice' | 'onmsg'

const AXIS_COLOR: Record<Axis, string> = {
  dist: 'var(--axis-dist)',
  voice: 'var(--axis-voice)',
  onmsg: 'var(--axis-onmsg)',
}

interface Props {
  label: string
  /** 0–100, or null while the value is still being measured. */
  value: number | null
  /** The draft's score on this axis, pinned to the rail for comparison. */
  baseline?: number | null
  /** Direction − draft. Rendered under the value when supplied. */
  delta?: number | null
  /** 'voice' pins the fill to the voice colour instead of the good/bad ramp. */
  tone?: 'auto' | 'voice'
  /** Plain-language explanation of what the axis measures. */
  hint?: string
  /** Which axis, for the identity dot. Defaults to distinctiveness. */
  axis?: Axis
  /**
   * Why this axis cannot be measured yet. When set, the rail is replaced by this
   * sentence — a locked axis says so rather than showing a number it would have
   * to invent, which is the whole reason Voice Match stays empty until samples
   * are validated.
   */
  lockedReason?: string | null
  /** Action that would unlock the axis, rendered inline after the reason. */
  onUnlock?: () => void
  /** Label for the unlock action. */
  unlockLabel?: string
}

function rampColor(value: number): string {
  if (value >= 65) return 'var(--high)'
  if (value >= 40) return 'var(--mid)'
  return 'var(--low)'
}

export default function AxisMeter({
  label,
  value,
  baseline = null,
  delta = null,
  tone = 'auto',
  hint,
  axis = 'dist',
  lockedReason = null,
  onUnlock,
  unlockLabel = 'Add samples',
}: Props) {
  // A locked axis is a different statement from an unmeasured one: "cannot be
  // measured yet, and here is why" rather than "measuring". Say it in words.
  if (lockedReason) {
    return (
      <div className="meter" title={hint}>
        <span className="meter__label">
          <span className="meter__dot" style={{ background: AXIS_COLOR[axis], opacity: 0.35 }} />
          {label}
        </span>
        <span className="meter__locked">
          {lockedReason}
          {onUnlock && (
            <>
              {' '}
              <button type="button" className="meter__unlock" onClick={onUnlock}>
                {unlockLabel}
              </button>
            </>
          )}
        </span>
      </div>
    )
  }

  const pending = value === null
  const pct = pending ? 0 : Math.max(0, Math.min(100, value))
  const color = pending
    ? 'var(--rule-firm)'
    : tone === 'voice'
      ? 'var(--voice)'
      : rampColor(pct)

  // Only worth drawing the comparison tick if there is a comparison to draw.
  const showGhost = !pending && baseline != null
  const ghostPct = showGhost ? Math.max(0, Math.min(100, baseline)) : 0
  const ghostLabel = showGhost ? `Your draft: ${Math.round(ghostPct)}` : undefined

  return (
    <div className="meter" title={hint}>
      <span className="meter__label">
        <span className="meter__dot" style={{ background: AXIS_COLOR[axis] }} />
        {label}
      </span>

      <div
        className="meter__rail"
        role="meter"
        aria-label={hint ? `${label} — ${hint}` : label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pending ? undefined : Math.round(pct)}
        aria-valuetext={pending ? 'not yet measured' : `${Math.round(pct)} out of 100`}
      >
        <div className="meter__fill" style={{ width: `${pct}%`, background: color }} />
        {showGhost && (
          <div className="meter__ghost" style={{ left: `${ghostPct}%` }} title={ghostLabel} />
        )}
      </div>

      <div style={styles.readout}>
        <span className="meter__val" style={{ color: pending ? 'var(--ink-3)' : color }}>
          {pending ? '—' : Math.round(pct)}
        </span>
        {delta != null && !pending && (
          <span
            className="meter__delta"
            style={{ color: delta >= 0.5 ? 'var(--high)' : delta <= -0.5 ? 'var(--low)' : 'var(--ink-3)' }}
          >
            {delta >= 0 ? '+' : '−'}
            {Math.abs(delta).toFixed(0)}
          </span>
        )}
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  readout: { display: 'flex', flexDirection: 'column', alignItems: 'flex-end', lineHeight: 1.15 },
}
