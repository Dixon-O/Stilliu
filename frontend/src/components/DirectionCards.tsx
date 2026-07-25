import React, { useState } from 'react'
import type { DirectionCard as DirectionCardType } from '@/api/client'

interface Props {
  cards: DirectionCardType[]
  loading: boolean
}

export default function DirectionCards({ cards, loading }: Props) {
  const [copied, setCopied] = useState<string | null>(null)

  function handleCopy(text: string, persona: string) {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(persona)
      setTimeout(() => setCopied(null), 2000)
    })
  }

  if (loading) {
    return (
      <div style={styles.grid}>
        {[0, 1, 2].map(i => (
          <div key={i} style={{ ...styles.card, ...styles.skeleton }}>
            <div style={styles.skeletonLine} />
            <div style={{ ...styles.skeletonLine, width: '60%' }} />
            <div style={{ ...styles.skeletonLine, marginTop: '12px' }} />
            <div style={{ ...styles.skeletonLine, width: '85%' }} />
            <div style={{ ...styles.skeletonLine, width: '70%' }} />
          </div>
        ))}
      </div>
    )
  }

  if (cards.length === 0) {
    return (
      <div style={styles.empty}>
        <div style={styles.emptyIcon}>↑</div>
        <p>Paste a draft and hit <strong>Analyse</strong> to generate three divergent directions.</p>
      </div>
    )
  }

  return (
    <div style={styles.grid}>
      {cards.map(card => (
        <div key={card.persona} style={styles.card}>
          <div style={styles.cardHeader}>
            <div>
              <div style={styles.personaLabel}>{card.persona}</div>
              <div style={styles.personaDesc}>{card.persona_description}</div>
            </div>
            <div style={styles.scoreChip}>
              <span style={styles.scoreNum}>{Math.round(card.generic_distance)}</span>
              <span style={styles.scoreUnit}>/100</span>
            </div>
          </div>
          <p style={styles.cardText}>{card.text}</p>
          <button
            style={copied === card.persona ? { ...styles.copyBtn, ...styles.copyBtnDone } : styles.copyBtn}
            onClick={() => handleCopy(card.text, card.persona)}
          >
            {copied === card.persona ? 'Copied!' : 'Copy'}
          </button>
        </div>
      ))}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  grid: {
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
  },
  card: {
    background: '#1a1d27',
    border: '1px solid #2e3350',
    borderRadius: '10px',
    padding: '18px',
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  skeleton: {
    gap: '10px',
    opacity: 0.5,
  },
  skeletonLine: {
    height: '12px',
    background: '#2e3350',
    borderRadius: '4px',
    width: '100%',
    animation: 'pulse 1.5s ease-in-out infinite',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: '10px',
  },
  personaLabel: {
    fontSize: '13px',
    fontWeight: 700,
    color: '#6b74f8',
  },
  personaDesc: {
    fontSize: '11px',
    color: '#7c829e',
    marginTop: '2px',
  },
  scoreChip: {
    background: '#22263a',
    border: '1px solid #2e3350',
    borderRadius: '6px',
    padding: '4px 8px',
    display: 'flex',
    alignItems: 'baseline',
    gap: '2px',
    flexShrink: 0,
  },
  scoreNum: {
    fontSize: '15px',
    fontWeight: 700,
    color: '#3ecf8e',
  },
  scoreUnit: {
    fontSize: '10px',
    color: '#7c829e',
  },
  cardText: {
    fontSize: '14px',
    color: '#c8cad8',
    lineHeight: 1.65,
  },
  copyBtn: {
    alignSelf: 'flex-start',
    background: 'transparent',
    border: '1px solid #2e3350',
    borderRadius: '6px',
    color: '#7c829e',
    fontSize: '12px',
    fontWeight: 600,
    padding: '5px 12px',
    transition: 'border-color 0.15s, color 0.15s',
  },
  copyBtnDone: {
    borderColor: '#3ecf8e',
    color: '#3ecf8e',
  },
  empty: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
    padding: '48px 24px',
    color: '#7c829e',
    textAlign: 'center',
    fontSize: '14px',
  },
  emptyIcon: {
    fontSize: '28px',
    color: '#2e3350',
  },
}
