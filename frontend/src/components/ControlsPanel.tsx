import React from 'react'
import type { WriterControls } from '@/api/client'

interface Props {
  controls: WriterControls
  onChange: (c: WriterControls) => void
  voiceActive: boolean
}

const PERSONA_OPTIONS = ['Sparse Minimalist', 'The Arguer', 'Sensory-Led']

export default function ControlsPanel({ controls, onChange, voiceActive }: Props) {
  function set<K extends keyof WriterControls>(key: K, value: WriterControls[K]) {
    onChange({ ...controls, [key]: value })
  }

  function togglePersona(name: string) {
    const current = controls.personas ?? PERSONA_OPTIONS
    const next = current.includes(name)
      ? current.filter(p => p !== name)
      : [...current, name]
    set('personas', next.length ? next : null)
  }

  const activePersonas = controls.personas ?? PERSONA_OPTIONS

  return (
    <div style={styles.panel}>
      <div style={styles.title}>Controls</div>

      {/* Format + length */}
      <div style={styles.row}>
        <div style={styles.field}>
          <label style={styles.fieldLabel}>Format</label>
          <select style={styles.select} value={controls.fmt}
            onChange={e => set('fmt', e.target.value as WriterControls['fmt'])}>
            <option value="prose">Prose</option>
            <option value="punchy">Punchy</option>
            <option value="bullets">Bullets</option>
            <option value="longform">Long-form</option>
          </select>
        </div>
        <div style={styles.field}>
          <label style={styles.fieldLabel}>Length</label>
          <select style={styles.select} value={controls.length}
            onChange={e => set('length', e.target.value as WriterControls['length'])}>
            <option value="shorter">Shorter</option>
            <option value="match">Match draft</option>
            <option value="longer">Longer</option>
          </select>
        </div>
      </div>

      {/* Tone + audience */}
      <div style={styles.row}>
        <div style={styles.field}>
          <label style={styles.fieldLabel}>Tone</label>
          <input style={styles.input} placeholder="e.g. warm, candid"
            value={controls.tone} onChange={e => set('tone', e.target.value)} />
        </div>
        <div style={styles.field}>
          <label style={styles.fieldLabel}>Audience</label>
          <input style={styles.input} placeholder="e.g. busy execs"
            value={controls.audience} onChange={e => set('audience', e.target.value)} />
        </div>
      </div>

      {/* Personas */}
      <div style={styles.field}>
        <label style={styles.fieldLabel}>Directions to generate</label>
        <div style={styles.chipRow}>
          {PERSONA_OPTIONS.map(p => (
            <button key={p} type="button"
              style={activePersonas.includes(p) ? { ...styles.chip, ...styles.chipOn } : styles.chip}
              onClick={() => togglePersona(p)}>
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Custom persona */}
      <div style={styles.field}>
        <label style={styles.fieldLabel}>Custom direction (optional)</label>
        <input style={styles.input} placeholder="e.g. wry and understated, like a diary entry"
          value={controls.custom_persona} onChange={e => set('custom_persona', e.target.value)} />
      </div>

      {/* Voice strength — only meaningful with an active fingerprint */}
      <div style={styles.field}>
        <label style={styles.fieldLabel}>
          Voice anchoring {voiceActive ? '' : '(add samples to use)'} — {Math.round(controls.voice_strength * 100)}%
        </label>
        <input type="range" min={0} max={1} step={0.1} disabled={!voiceActive}
          value={controls.voice_strength}
          onChange={e => set('voice_strength', parseFloat(e.target.value))}
          style={{ ...styles.range, opacity: voiceActive ? 1 : 0.4 }} />
        <div style={styles.rangeHint}>
          <span>More distinctive</span>
          <span>Hug my voice</span>
        </div>
      </div>

      {/* Preserve facts */}
      <label style={styles.toggle}>
        <input type="checkbox" checked={controls.preserve_facts}
          onChange={e => set('preserve_facts', e.target.checked)} />
        <span>Preserve facts — flag & regenerate directions that invent claims</span>
      </label>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    background: '#1a1d27', border: '1px solid #2e3350', borderRadius: '10px',
    padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px',
  },
  title: {
    fontSize: '12px', fontWeight: 700, textTransform: 'uppercase',
    letterSpacing: '0.7px', color: '#7c829e',
  },
  row: { display: 'flex', gap: '12px' },
  field: { display: 'flex', flexDirection: 'column', gap: '5px', flex: 1 },
  fieldLabel: { fontSize: '11px', color: '#7c829e', fontWeight: 600 },
  select: {
    background: '#141720', border: '1px solid #2e3350', borderRadius: '7px',
    color: '#e8eaf0', fontSize: '13px', padding: '8px 10px', outline: 'none',
  },
  input: {
    background: '#141720', border: '1px solid #2e3350', borderRadius: '7px',
    color: '#e8eaf0', fontSize: '13px', padding: '8px 10px', outline: 'none', width: '100%',
  },
  chipRow: { display: 'flex', gap: '6px', flexWrap: 'wrap' },
  chip: {
    background: 'transparent', border: '1px solid #2e3350', borderRadius: '999px',
    color: '#7c829e', fontSize: '12px', fontWeight: 600, padding: '5px 12px', cursor: 'pointer',
    transition: 'all 0.15s',
  },
  chipOn: { borderColor: '#6b74f8', color: '#6b74f8', background: 'rgba(107,116,248,0.1)' },
  range: { width: '100%', accentColor: '#6b74f8' },
  rangeHint: { display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: '#7c829e' },
  toggle: {
    display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px',
    color: '#c8cad8', cursor: 'pointer',
  },
}
