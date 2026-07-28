import React, { useEffect, useMemo, useState } from 'react'
import {
  DIVERGENCE_NOTCHES,
  fetchStyles,
  type Divergence,
  type StyleLibrary,
  type WriterControls,
} from '@/api/client'

interface Props {
  controls: WriterControls
  onChange: (c: WriterControls) => void
  voiceActive: boolean
}

// ── Palette (matches the rest of the app) ─────────────────────────────────────
const C = {
  bg: '#0f1117',
  panel: '#1a1d27',
  border: '#2e3350',
  text: '#e8eaf0',
  dim: '#7c829e',
  accent: '#6b74f8',
  good: '#3ecf8e',
  warn: '#e0a94a',
  bad: '#e5534b',
}

const FORMATS: { value: WriterControls['fmt']; label: string }[] = [
  { value: 'prose', label: 'Prose' },
  { value: 'punchy', label: 'Punchy' },
  { value: 'bullets', label: 'Bullets' },
  { value: 'longform', label: 'Long-form' },
]

const LENGTHS: { value: WriterControls['length']; label: string }[] = [
  { value: 'shorter', label: 'Shorter' },
  { value: 'match', label: 'Match draft' },
  { value: 'longer', label: 'Longer' },
]

/** Two groups open on load; the rest collapse so the panel stays scannable. */
const OPEN_BY_DEFAULT = ['compression', 'counter_llm']

export default function ControlsPanel({ controls, onChange, voiceActive }: Props) {
  const [library, setLibrary] = useState<StyleLibrary | null>(null)
  const [libError, setLibError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [openGroups, setOpenGroups] = useState<string[]>(OPEN_BY_DEFAULT)
  const [showAdvanced, setShowAdvanced] = useState(false)

  // The library is served from styles.py, so adding a preset on the backend
  // makes it appear here with no frontend change.
  useEffect(() => {
    let cancelled = false
    fetchStyles()
      .then(lib => { if (!cancelled) setLibrary(lib) })
      .catch(err => {
        if (!cancelled) setLibError(err instanceof Error ? err.message : 'Failed to load styles')
      })
    return () => { cancelled = true }
  }, [])

  function set<K extends keyof WriterControls>(key: K, value: WriterControls[K]) {
    onChange({ ...controls, [key]: value })
  }

  // `personas === null` means "let the backend pick its defaults". We resolve it
  // to concrete names as soon as the user touches the picker.
  const selected: string[] = controls.personas ?? library?.defaults ?? []
  const maxSelected = library?.max_selected ?? 6
  const atLimit = selected.length >= maxSelected

  function toggleStyle(name: string) {
    const isOn = selected.includes(name)
    if (!isOn && atLimit) return
    const next = isOn ? selected.filter(n => n !== name) : [...selected, name]
    set('personas', next.length ? next : null)
  }

  function toggleGroup(id: string) {
    setOpenGroups(g => (g.includes(id) ? g.filter(x => x !== id) : [...g, id]))
  }

  // Searching flattens the grouping and auto-reveals every match.
  const needle = query.trim().toLowerCase()
  const searching = needle.length > 0

  const grouped = useMemo(() => {
    if (!library) return []
    return library.groups
      .map(g => ({
        group: g,
        items: library.styles.filter(
          s =>
            s.group === g.id &&
            (!searching ||
              s.name.toLowerCase().includes(needle) ||
              s.description.toLowerCase().includes(needle)),
        ),
      }))
      .filter(x => x.items.length > 0)
  }, [library, searching, needle])

  const totalStyles = library?.styles.length ?? 0

  return (
    <div style={S.wrap}>
      {/* ── Divergence ──────────────────────────────────────────────── */}
      <Section title="Divergence" note="How far a rewrite may travel from your draft">
        <div style={S.notchRow}>
          {DIVERGENCE_NOTCHES.map(n => {
            const active = controls.divergence === n.value
            return (
              <button
                key={n.value}
                type="button"
                title={n.hint}
                onClick={() => set('divergence', n.value as Divergence)}
                style={active ? { ...S.notch, ...S.notchActive } : S.notch}
              >
                {n.label}
              </button>
            )
          })}
        </div>
        <p style={S.hintLine}>
          {DIVERGENCE_NOTCHES.find(n => n.value === controls.divergence)?.hint}
        </p>
      </Section>

      {/* ── Style library ───────────────────────────────────────────── */}
      <Section
        title="Styles"
        note={
          library
            ? `${selected.length} of ${maxSelected} chosen · ${totalStyles} available · one direction per style`
            : 'Loading library…'
        }
      >
        {libError && (
          <p style={S.error}>
            Could not load the style library ({libError}). Check the backend is
            running on port 8000 — the defaults will still be used.
          </p>
        )}

        {library && (
          <>
            <input
              style={S.search}
              placeholder="Search styles — try 'metaphor', 'argument', 'AI'"
              value={query}
              onChange={e => setQuery(e.target.value)}
            />

            {atLimit && (
              <p style={S.limitNote}>
                At the {maxSelected}-style limit. Deselect one to add another —
                each style is its own model call.
              </p>
            )}

            {grouped.map(({ group, items }) => {
              const open = searching || openGroups.includes(group.id)
              const chosenHere = items.filter(i => selected.includes(i.name)).length
              return (
                <div key={group.id} style={S.group}>
                  <button
                    type="button"
                    style={S.groupHead}
                    onClick={() => { if (!searching) toggleGroup(group.id) }}
                  >
                    <span style={S.groupLabel}>{group.label}</span>
                    {chosenHere > 0 && <span style={S.groupCount}>{chosenHere}</span>}
                    <span style={S.chevron}>{open ? '▲' : '▼'}</span>
                  </button>

                  {open && (
                    <>
                      <p style={S.groupBlurb}>{group.blurb}</p>
                      <div style={S.styleList}>
                        {items.map(s => {
                          const on = selected.includes(s.name)
                          const disabled = !on && atLimit
                          return (
                            <button
                              key={s.name}
                              type="button"
                              disabled={disabled}
                              onClick={() => toggleStyle(s.name)}
                              style={{
                                ...S.styleItem,
                                ...(on ? S.styleItemOn : {}),
                                ...(disabled ? S.styleItemDisabled : {}),
                              }}
                            >
                              <span style={S.styleTop}>
                                <span style={on ? S.checkOn : S.checkOff}>{on ? '✓' : ''}</span>
                                <span style={S.styleName}>{s.name}</span>
                              </span>
                              <span style={S.styleDesc}>{s.description}</span>
                            </button>
                          )
                        })}
                      </div>
                    </>
                  )}
                </div>
              )
            })}

            {grouped.length === 0 && (
              <p style={S.emptyNote}>No styles match “{query}”.</p>
            )}
          </>
        )}
      </Section>

      {/* ── Custom style ────────────────────────────────────────────── */}
      <Section title="Your own style" note="Generated as an extra direction">
        <textarea
          style={S.textarea}
          rows={3}
          placeholder="Describe a style in your own words — e.g. 'clipped and unsentimental, like a case file, but every third sentence lands a joke'"
          value={controls.custom_persona}
          onChange={e => set('custom_persona', e.target.value)}
        />
      </Section>

      {/* ── Shape ───────────────────────────────────────────────────── */}
      <Section title="Shape">
        <div style={S.twoCol}>
          <Field label="Format">
            <select
              style={S.select}
              value={controls.fmt}
              onChange={e => set('fmt', e.target.value as WriterControls['fmt'])}
            >
              {FORMATS.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
            </select>
          </Field>
          <Field label="Length">
            <select
              style={S.select}
              value={controls.length}
              onChange={e => set('length', e.target.value as WriterControls['length'])}
            >
              {LENGTHS.map(l => <option key={l.value} value={l.value}>{l.label}</option>)}
            </select>
          </Field>
        </div>
      </Section>

      {/* ── Advanced ────────────────────────────────────────────────── */}
      <button type="button" style={S.advToggle} onClick={() => setShowAdvanced(a => !a)}>
        {showAdvanced ? '▲' : '▼'}  Tone, audience & guards
      </button>

      {showAdvanced && (
        <div style={S.advBody}>
          <Field label="Tone">
            <input
              style={S.input}
              placeholder="warm and candid · authoritative · wry"
              value={controls.tone}
              onChange={e => set('tone', e.target.value)}
            />
          </Field>

          <Field label="Audience">
            <input
              style={S.input}
              placeholder="busy executives · complete newcomers · fellow specialists"
              value={controls.audience}
              onChange={e => set('audience', e.target.value)}
            />
          </Field>

          <Field
            label={`Voice anchoring — ${voiceStrengthLabel(controls.voice_strength)}`}
            hint={
              voiceActive
                ? 'Higher hugs your voice more tightly, which trades off against distinctiveness.'
                : 'Add writing samples below to enable voice anchoring.'
            }
          >
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={controls.voice_strength}
              disabled={!voiceActive}
              onChange={e => set('voice_strength', Number(e.target.value))}
              style={{ ...S.range, opacity: voiceActive ? 1 : 0.4 }}
            />
          </Field>

          <Toggle
            checked={controls.avoid_ai_cadence}
            onChange={v => set('avoid_ai_cadence', v)}
            label="Strip AI cadence"
            hint="Bans tricolons, 'not just X but Y', em-dash asides, summarising closers, and the over-represented LLM lexicon."
          />

          <Toggle
            checked={controls.preserve_facts}
            onChange={v => set('preserve_facts', v)}
            label="Preserve facts"
            hint="Directions may not introduce facts absent from your draft. Enables the faithfulness guard."
          />
        </div>
      )}
    </div>
  )
}

// ── Building blocks ───────────────────────────────────────────────────────────

function voiceStrengthLabel(v: number): string {
  if (v <= 0.05) return 'off'
  if (v < 0.33) return 'light echo'
  if (v < 0.66) return 'balanced'
  return 'hug tightly'
}

function Section({
  title, note, children,
}: { title: string; note?: string; children: React.ReactNode }) {
  return (
    <div style={S.section}>
      <div style={S.sectionHead}>
        <span style={S.sectionTitle}>{title}</span>
        {note && <span style={S.sectionNote}>{note}</span>}
      </div>
      {children}
    </div>
  )
}

function Field({
  label, hint, children,
}: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div style={S.field}>
      <label style={S.fieldLabel}>{label}</label>
      {children}
      {hint && <span style={S.fieldHint}>{hint}</span>}
    </div>
  )
}

function Toggle({
  checked, onChange, label, hint,
}: { checked: boolean; onChange: (v: boolean) => void; label: string; hint: string }) {
  return (
    <button type="button" style={S.toggleRow} onClick={() => onChange(!checked)}>
      <span style={checked ? { ...S.box, ...S.boxOn } : S.box}>{checked ? '✓' : ''}</span>
      <span style={S.toggleText}>
        <span style={S.toggleLabel}>{label}</span>
        <span style={S.toggleHint}>{hint}</span>
      </span>
    </button>
  )
}

// ── Styles ────────────────────────────────────────────────────────────────────

const S: Record<string, React.CSSProperties> = {
  wrap: {
    display: 'flex', flexDirection: 'column', gap: '14px',
    background: C.panel, border: `1px solid ${C.border}`,
    borderRadius: '10px', padding: '16px', width: '100%',
  },
  section: { display: 'flex', flexDirection: 'column', gap: '8px' },
  sectionHead: { display: 'flex', alignItems: 'baseline', gap: '8px', flexWrap: 'wrap' },
  sectionTitle: {
    fontSize: '11px', fontWeight: 700, color: C.text,
    textTransform: 'uppercase', letterSpacing: '0.6px',
  },
  sectionNote: { fontSize: '11px', color: C.dim },

  notchRow: { display: 'flex', gap: '6px' },
  notch: {
    flex: 1, background: C.bg, border: `1px solid ${C.border}`, borderRadius: '7px',
    color: C.dim, fontSize: '12px', fontWeight: 700, padding: '8px 6px', cursor: 'pointer',
  },
  notchActive: { borderColor: C.accent, color: '#fff', background: C.accent },
  hintLine: { fontSize: '11px', color: C.dim, lineHeight: 1.5, margin: 0 },

  search: {
    background: C.bg, border: `1px solid ${C.border}`, borderRadius: '6px',
    color: C.text, fontSize: '12px', padding: '8px 10px', outline: 'none', width: '100%',
  },
  limitNote: {
    fontSize: '11px', color: C.warn, lineHeight: 1.5, margin: 0,
    background: 'rgba(224,169,74,0.08)', border: '1px solid rgba(224,169,74,0.25)',
    borderRadius: '6px', padding: '7px 9px',
  },
  emptyNote: { fontSize: '12px', color: C.dim, margin: 0 },

  group: { display: 'flex', flexDirection: 'column', gap: '6px' },
  groupHead: {
    display: 'flex', alignItems: 'center', gap: '8px', width: '100%',
    background: 'transparent', border: 'none', borderBottom: `1px solid ${C.border}`,
    color: C.text, fontSize: '11px', fontWeight: 700, padding: '6px 0',
    textAlign: 'left', cursor: 'pointer', textTransform: 'uppercase', letterSpacing: '0.5px',
  },
  groupLabel: { flex: 1 },
  groupCount: {
    background: C.accent, color: '#fff', borderRadius: '10px',
    fontSize: '10px', fontWeight: 700, padding: '1px 7px',
  },
  chevron: { fontSize: '9px', color: C.dim },
  groupBlurb: { fontSize: '11px', color: C.dim, lineHeight: 1.5, margin: 0 },
  styleList: { display: 'flex', flexDirection: 'column', gap: '5px' },
  styleItem: {
    display: 'flex', flexDirection: 'column', gap: '3px',
    background: C.bg, border: `1px solid ${C.border}`, borderRadius: '7px',
    padding: '9px 10px', textAlign: 'left', cursor: 'pointer', width: '100%',
  },
  styleItemOn: { borderColor: C.accent, background: 'rgba(107,116,248,0.10)' },
  styleItemDisabled: { opacity: 0.35, cursor: 'not-allowed' },
  styleTop: { display: 'flex', alignItems: 'center', gap: '7px' },
  checkOff: {
    width: '13px', height: '13px', borderRadius: '3px',
    border: `1px solid ${C.border}`, flexShrink: 0,
  },
  checkOn: {
    width: '13px', height: '13px', borderRadius: '3px', background: C.accent,
    color: '#fff', fontSize: '9px', lineHeight: '13px', textAlign: 'center', flexShrink: 0,
  },
  styleName: { fontSize: '12.5px', fontWeight: 700, color: C.text },
  styleDesc: { fontSize: '11px', color: C.dim, lineHeight: 1.5, paddingLeft: '20px' },

  twoCol: { display: 'flex', gap: '10px' },
  field: { display: 'flex', flexDirection: 'column', gap: '5px', flex: 1 },
  fieldLabel: {
    fontSize: '10.5px', fontWeight: 700, color: C.dim,
    textTransform: 'uppercase', letterSpacing: '0.5px',
  },
  fieldHint: { fontSize: '10.5px', color: C.dim, lineHeight: 1.5 },
  select: {
    background: C.bg, border: `1px solid ${C.border}`, borderRadius: '6px',
    color: C.text, fontSize: '12px', padding: '7px 8px', outline: 'none', width: '100%',
  },
  input: {
    background: C.bg, border: `1px solid ${C.border}`, borderRadius: '6px',
    color: C.text, fontSize: '12px', padding: '7px 9px', outline: 'none', width: '100%',
  },
  textarea: {
    background: C.bg, border: `1px solid ${C.border}`, borderRadius: '6px',
    color: C.text, fontSize: '12px', lineHeight: 1.6, padding: '9px 10px',
    outline: 'none', resize: 'vertical', width: '100%',
  },
  range: { width: '100%', accentColor: C.accent },

  advToggle: {
    background: 'transparent', border: `1px solid ${C.border}`, borderRadius: '7px',
    color: C.dim, fontSize: '11px', fontWeight: 700, padding: '8px 10px',
    textAlign: 'left', cursor: 'pointer', width: '100%',
  },
  advBody: { display: 'flex', flexDirection: 'column', gap: '12px' },

  toggleRow: {
    display: 'flex', alignItems: 'flex-start', gap: '9px', background: 'transparent',
    border: 'none', padding: 0, textAlign: 'left', cursor: 'pointer', width: '100%',
  },
  box: {
    width: '15px', height: '15px', borderRadius: '4px', border: `1px solid ${C.border}`,
    flexShrink: 0, marginTop: '2px',
  },
  boxOn: {
    background: C.good, borderColor: C.good, color: C.bg,
    fontSize: '10px', lineHeight: '15px', textAlign: 'center', fontWeight: 700,
  },
  toggleText: { display: 'flex', flexDirection: 'column', gap: '2px' },
  toggleLabel: { fontSize: '12px', fontWeight: 700, color: C.text },
  toggleHint: { fontSize: '10.5px', color: C.dim, lineHeight: 1.5 },

  error: { fontSize: '11px', color: C.bad, lineHeight: 1.5, margin: 0 },
}
