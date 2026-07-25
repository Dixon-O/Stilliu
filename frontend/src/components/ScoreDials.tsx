import React from 'react'

interface Props {
  label: string
  value: number | null
  subtitle: string
  lowLabel: string
  highLabel: string
  color?: 'accent' | 'green'
}

export default function ScoreDial({ label, value, subtitle, lowLabel, highLabel, color = 'accent' }: Props) {
  const isLoading = value === null

  // Converts a 0–100 score to a fill percentage on a 180° arc
  // The arc starts at 9 o'clock and sweeps 180° (bottom half of circle)
  const R = 52
  const CX = 70
  const CY = 70
  const circumference = Math.PI * R // half-circle
  const fillRatio = isLoading ? 0 : value! / 100
  const dashFill = fillRatio * circumference
  const dashGap = circumference - dashFill

  // Arc path: semicircle from left to right (bottom)
  const arcStart = `${CX - R},${CY}`
  const arcEnd   = `${CX + R},${CY}`

  const colorVar = color === 'green' ? '#3ecf8e' : '#6b74f8'
  const trackColor = '#2e3350'

  return (
    <div style={styles.wrap}>
      <div style={styles.label}>{label}</div>
      <div style={styles.dialWrap}>
        <svg width="140" height="80" viewBox="0 0 140 80" aria-label={`${label}: ${isLoading ? 'loading' : value}`}>
          {/* Track arc */}
          <path
            d={`M ${arcStart} A ${R} ${R} 0 0 1 ${arcEnd}`}
            fill="none"
            stroke={trackColor}
            strokeWidth="10"
            strokeLinecap="round"
          />
          {/* Fill arc */}
          <path
            d={`M ${arcStart} A ${R} ${R} 0 0 1 ${arcEnd}`}
            fill="none"
            stroke={isLoading ? trackColor : colorVar}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={`${dashFill} ${dashGap}`}
            style={{ transition: 'stroke-dasharray 0.7s cubic-bezier(.4,0,.2,1)' }}
          />
          {/* Value text */}
          <text
            x={CX}
            y={CY - 8}
            textAnchor="middle"
            fill={isLoading ? '#7c829e' : colorVar}
            fontSize="22"
            fontWeight="700"
            fontFamily="-apple-system, Segoe UI, system-ui, sans-serif"
          >
            {isLoading ? '—' : `${Math.round(value!)}`}
          </text>
        </svg>
        <div style={styles.axisRow}>
          <span style={styles.axisLabel}>{lowLabel}</span>
          <span style={styles.axisLabel}>{highLabel}</span>
        </div>
      </div>
      <div style={styles.subtitle}>{subtitle}</div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  wrap: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '4px',
    flex: 1,
    minWidth: '160px',
  },
  label: {
    fontSize: '11px',
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.7px',
    color: '#7c829e',
  },
  dialWrap: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
  },
  axisRow: {
    display: 'flex',
    justifyContent: 'space-between',
    width: '130px',
    marginTop: '-4px',
  },
  axisLabel: {
    fontSize: '10px',
    color: '#7c829e',
  },
  subtitle: {
    fontSize: '12px',
    color: '#7c829e',
    textAlign: 'center',
    maxWidth: '160px',
  },
}
