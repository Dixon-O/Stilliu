import React, { useState } from 'react'
import type { VoiceFingerprint } from '@/hooks/useVoiceFingerprint'

interface Props {
  fingerprint: VoiceFingerprint
  onAddSamples: (samples: string[]) => Promise<void>
  onClear: () => void
  loading: boolean
  error: string | null
}

const PLACEHOLDER = `Paste a writing sample here — a paragraph or two from something you've written previously. The more natural and unedited, the better.`

function toggleDotStyle(active: boolean): React.CSSProperties {
  return {
    width: '7px',
    height: '7px',
    borderRadius: '50%',
    background: active ? '#3ecf8e' : '#2e3350',
    flexShrink: 0,
  }
}

export default function VoiceOnboarding({ fingerprint, onAddSamples, onClear, loading, error }: Props) {
  const [open, setOpen] = useState(false)
  const [draft1, setDraft1] = useState('')
  const [draft2, setDraft2] = useState('')
  const [draft3, setDraft3] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const samples = [draft1, draft2, draft3].filter(s => s.trim().length > 0)
    void onAddSamples(samples)
  }

  const toggleStyle: React.CSSProperties = fingerprint.isActive
    ? { ...styles.toggle, ...styles.toggleActive }
    : styles.toggle

  return (
    <div style={styles.wrap}>
      <button
        style={toggleStyle}
        onClick={() => setOpen(o => !o)}
        type="button"
      >
        <span style={toggleDotStyle(fingerprint.isActive)} />
        {fingerprint.isActive
          ? `Voice fingerprint active — ${fingerprint.sampleCount} samples · ${fingerprint.paragraphCount} paragraphs`
          : 'Add your writing samples → unlock the voice-match score'}
        <span style={styles.chevron}>{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div style={styles.panel}>
          {fingerprint.isActive ? (
            <div style={styles.activeState}>
              <p style={styles.activeMsg}>{fingerprint.message}</p>
              <p style={styles.activeSub}>
                Your voice fingerprint is built from paragraph-level embeddings averaged into a centroid,
                combined with a stylometric profile of your sentence rhythm and word habits.
                The Voice-match score compares each direction against both — 100 means it sounds like you.
              </p>
              <button style={styles.clearBtn} onClick={onClear} type="button">
                Clear fingerprint
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} style={styles.form}>
              <p style={styles.hint}>
                Paste 2–3 samples of your natural writing. These are used to build a voice fingerprint
                (embedding centroid) — never stored, computed per session.
              </p>
              {([
                { label: 'Sample 1 (required)', value: draft1, set: setDraft1 },
                { label: 'Sample 2 (required)', value: draft2, set: setDraft2 },
                { label: 'Sample 3 (optional)', value: draft3, set: setDraft3 },
              ] as { label: string; value: string; set: (v: string) => void }[]).map(({ label, value, set }) => (
                <div key={label} style={styles.field}>
                  <label style={styles.fieldLabel}>{label}</label>
                  <textarea
                    style={styles.textarea}
                    placeholder={PLACEHOLDER}
                    value={value}
                    onChange={e => set(e.target.value)}
                    rows={4}
                  />
                </div>
              ))}
              {error && <p style={styles.error}>{error}</p>}
              <button
                style={loading ? { ...styles.submitBtn, opacity: 0.6 } : styles.submitBtn}
                type="submit"
                disabled={loading}
              >
                {loading ? 'Building fingerprint…' : 'Build voice fingerprint'}
              </button>
            </form>
          )}
        </div>
      )}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  wrap: {
    width: '100%',
  },
  toggle: {
    width: '100%',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    background: '#1a1d27',
    border: '1px solid #2e3350',
    borderRadius: '8px',
    color: '#7c829e',
    fontSize: '12px',
    fontWeight: 600,
    padding: '10px 14px',
    textAlign: 'left',
  },
  toggleActive: {
    borderColor: '#3ecf8e',
    color: '#3ecf8e',
  },
  chevron: {
    marginLeft: 'auto',
    fontSize: '10px',
    color: '#7c829e',
  },
  panel: {
    background: '#1a1d27',
    border: '1px solid #2e3350',
    borderTop: 'none',
    borderRadius: '0 0 8px 8px',
    padding: '16px',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  hint: {
    fontSize: '12px',
    color: '#7c829e',
    lineHeight: 1.6,
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  fieldLabel: {
    fontSize: '11px',
    fontWeight: 700,
    color: '#7c829e',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  textarea: {
    background: '#0f1117',
    border: '1px solid #2e3350',
    borderRadius: '6px',
    color: '#e8eaf0',
    fontSize: '13px',
    lineHeight: 1.6,
    padding: '10px 12px',
    resize: 'vertical',
    outline: 'none',
  },
  error: {
    fontSize: '12px',
    color: '#e5534b',
  },
  submitBtn: {
    alignSelf: 'flex-start',
    background: '#6b74f8',
    border: 'none',
    borderRadius: '7px',
    color: '#fff',
    fontSize: '13px',
    fontWeight: 700,
    padding: '9px 18px',
  },
  activeState: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  activeMsg: {
    fontSize: '13px',
    color: '#3ecf8e',
    fontWeight: 600,
  },
  activeSub: {
    fontSize: '12px',
    color: '#7c829e',
    lineHeight: 1.6,
  },
  clearBtn: {
    alignSelf: 'flex-start',
    background: 'transparent',
    border: '1px solid #2e3350',
    borderRadius: '6px',
    color: '#7c829e',
    fontSize: '12px',
    padding: '6px 12px',
  },
}
