import React from 'react'

interface Props {
  label: string
  value: number | null
  subtitle: string
  lowLabel: string
  highLabel: string
  color?: 'accent' | 'green' | 'amber'
  delta?: number | null
}

export default function ScoreDial({ label, value, subtitle, lowLabel, highLabel, color = 'accent', delta }: Props) {
  const isLoading = value === null
  const R = 52, CX = 70, CY = 70
  const circumference = Math.PI * R
  const fillRatio = isLoading ? 0 : value! / 100
  const dashFill = fillRatio * circumference
  const dashGap = circumference - dashFill

  const arcStart = `${CX - R},${CY}`
  const arcEnd   = `${CX + R},${CY}`

  const colorVar = color === 'green' ? '#3ecf8e' : color === 'amber' ? '#f5a623' : '#6b74f8'
  const trackColor = '#2e3350'

  // Color by meaning: high is always good, so green when high, amber when mid, red when low
  const meaningColor = isLoading ? trackColor
    : value! >= 65 ? '#3ecf8e'
    : value! >= 40 ? '#f5a623'
    : '#e5534b'

  const displayColor = color !== 'accent' ? colorVar : meaningColor

  return (
    <div style={styles.wrap}>
      <div style={styles.label}>{label}</div>
      <div style={styles.dialWrap}>
        <svg width="140" height="80" viewBox="0 0 140 80" aria-label={`${label}: ${isLoading ? 'loading' : value}`}>
          <path d={`M ${arcStart} A ${R} ${R} 0 0 1 ${arcEnd}`}
            fill="none" stroke={trackColor} strokeWidth="10" strokeLinecap="round" />
          <path d={`M ${arcStart} A ${R} ${R} 0 0 1 ${arcEnd}`}
            fill="none" stroke={isLoading ? trackColor : displayColor} strokeWidth="10" strokeLinecap="round"
            strokeDasharray={`${dashFill} ${dashGap}`}
            style={{ transition: 'stroke-dasharray 0.7s cubic-bezier(.4,0,.2,1)' }} />
          <text x={CX} y={CY - 8} textAnchor="middle"
            fill={isLoading ? '#7c829e' : displayColor}
            fontSize="22" fontWeight="700" fontFamily="-apple-system, Segoe UI, system-ui, sans-serif">
            {isLoading ? '—' : `${Math.round(value!)}`}
          </text>
        </svg>
        <div style={styles.axisRow}>
          <span style={styles.axisLabel}>{lowLabel}</span>
          <span style={styles.axisLabel}>{highLabel}</span>
        </div>
      </div>
      {delta != null && !isLoading && (
        <div style={{ ...styles.delta, color: delta >= 0 ? '#3ecf8e' : '#e5534b' }}>
          {delta >= 0 ? `+${delta.toFixed(0)}` : delta.toFixed(0)} vs draft
        </div>
      )}
      <div style={styles.subtitle}>{subtitle}</div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  wrap: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px', flex: 1, minWidth: '140px' },
  label: { fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.7px', color: '#7c829e' },
  dialWrap: { display: 'flex', flexDirection: 'column', alignItems: 'center' },
  axisRow: { display: 'flex', justifyContent: 'space-between', width: '130px', marginTop: '-4px' },
  axisLabel: { fontSize: '10px', color: '#7c829e' },
  delta: { fontSize: '11px', fontWeight: 700 },
  subtitle: { fontSize: '12px', color: '#7c829e', textAlign: 'center', maxWidth: '150px' },
}
