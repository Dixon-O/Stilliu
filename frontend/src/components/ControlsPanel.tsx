import React, { useMemo, useState } from 'react'
import {
  DEFAULT_CONTROLS,
  DIVERGENCE_NOTCHES,
  FORMAT_OPTIONS,
  LENGTH_OPTIONS,
  OPENING_OPTIONS,
  POV_OPTIONS,
  RHYTHM_OPTIONS,
  VOCABULARY_OPTIONS,
  TENSE_OPTIONS,
  type Option,
  type StyleLibrary,
  type WriterControls,
} from '@/api/client'
import type { VoiceFingerprint } from '@/hooks/useVoiceFingerprint'
import VoiceOnboarding from './VoiceOnboarding'

/**
 * ControlsPanel — every lever, in five tabs.
 *
 * The panel used to be one long scroll with a collapsed "advanced" drawer at the
 * bottom, which meant half the controls were below the fold and the writer had
 * to remember they existed. Tabs put every group one click from the surface at a
 * fixed height, and each tab carries a count of how many of its controls the
 * writer has moved off default — so nothing is hidden without a trace.
 *
 * The panel is deliberately stateless about the *selection*: it renders the
 * `selected` array it is given and reports intent upward. That is what keeps the
 * "cleared on purpose" state intact — see App's toggleStyle.
 */

type TabId = 'styles' | 'shape' | 'register' | 'guards' | 'voice'

const TABS: { id: TabId; label: string }[] = [
  { id: 'styles',   label: 'Styles' },
  { id: 'shape',    label: 'Shape' },
  { id: 'register', label: 'Register' },
  { id: 'guards',   label: 'Guards' },
  { id: 'voice',    label: 'Voice' },
]

/** Which controls live behind which tab — drives the "moved off default" counts. */
const TAB_KEYS: Record<TabId, (keyof WriterControls)[]> = {
  styles:   ['custom_persona'],
  shape:    ['divergence', 'fmt', 'length', 'opening', 'rhythm'],
  register: ['pov', 'tense', 'vocabulary', 'tone', 'audience'],
  guards:   ['preserve_facts', 'avoid_ai_cadence', 'banned_words', 'keep_phrases'],
  voice:    ['voice_strength'],
}

/** Two groups open on load; the rest collapse so the picker stays scannable. */
const OPEN_BY_DEFAULT = ['compression', 'counter_llm']

interface Props {
  controls: WriterControls
  onChange: (c: WriterControls) => void
  library: StyleLibrary | null
  libError: string | null
  /** Resolved selection, owned by App. */
  selected: string[]
  onToggleStyle: (name: string) => void
  onClearStyles: () => void
  onRestoreDefaults: () => void
  voiceActive: boolean
  fingerprint: VoiceFingerprint
  onAddSamples: (samples: string[]) => Promise<void>
  onClearVoice: () => void
  voiceLoading: boolean
  voiceError: string | null
}

export default function ControlsPanel({
  controls,
  onChange,
  library,
  libError,
  selected,
  onToggleStyle,
  onClearStyles,
  onRestoreDefaults,
  voiceActive,
  fingerprint,
  onAddSamples,
  onClearVoice,
  voiceLoading,
  voiceError,
}: Props) {
  const [tab, setTab] = useState<TabId>('styles')
  const [query, setQuery] = useState('')
  const [openGroups, setOpenGroups] = useState<string[]>(OPEN_BY_DEFAULT)

  function set<K extends keyof WriterControls>(key: K, value: WriterControls[K]) {
    onChange({ ...controls, [key]: value })
  }

  const maxSelected = library?.max_selected ?? 6
  const hasCustom = controls.custom_persona.trim().length > 0
  // Each direction is one model call, so the backend caps the batch — and a
  // custom brief takes one of those slots. Mirroring that here is what keeps the
  // picker from letting you choose a style that would then be dropped silently.
  const room = Math.max(hasCustom ? maxSelected - 1 : maxSelected, 0)
  const atLimit = selected.length >= room
  const dropped = Math.max(selected.length - room, 0)

  // Searching flattens the grouping and auto-reveals every match.
  const needle = query.trim().toLowerCase()
  const searching = needle.length > 0

  const grouped = useMemo(() => {
    if (!library) return []
    return library.groups
      .map((g) => ({
        group: g,
        items: library.styles.filter(
          (s) =>
            s.group === g.id &&
            (!searching ||
              s.name.toLowerCase().includes(needle) ||
              s.description.toLowerCase().includes(needle)),
        ),
      }))
      .filter((x) => x.items.length > 0)
  }, [library, searching, needle])

  const badges = useMemo(() => {
    const out = {} as Record<TabId, number>
    for (const t of TABS) {
      out[t.id] =
        t.id === 'styles'
          ? selected.length
          : TAB_KEYS[t.id].filter((k) => controls[k] !== DEFAULT_CONTROLS[k]).length
    }
    return out
  }, [controls, selected])

  return (
    <section className="card card--flex" style={S.card} aria-label="Writer controls">
      <div className="tabs" role="tablist" aria-label="Control groups">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            type="button"
            className="tab"
            id={`ctl-tab-${t.id}`}
            aria-controls="ctl-panel"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
          >
            {t.label}
            {badges[t.id] > 0 && <span className="tab__count">{badges[t.id]}</span>}
          </button>
        ))}
      </div>

      <div
        className="scroll"
        role="tabpanel"
        id="ctl-panel"
        aria-labelledby={`ctl-tab-${tab}`}
        style={S.body}
      >
        {/* ── Styles ──────────────────────────────────────────────────────── */}
        {tab === 'styles' && (
          <>
            {libError && (
              <p className="callout callout--err">
                Could not load the style library ({libError}). Check the backend is running
                on port 8000.
              </p>
            )}

            {/* Count, actions and search stay in view while the list scrolls —
                they are what you reach for *during* browsing, not before it. */}
            <div className="sticky-head">
              <div style={S.selRow}>
                <span className="note">
                  {selected.length} of {room} chosen
                  {hasCustom ? ' · brief takes a slot' : ''}
                  {library ? ` · ${library.styles.length} available` : ''}
                </span>
                <span style={S.spacer} />
                <button
                  className="btn btn--quiet btn--sm"
                  type="button"
                  onClick={onClearStyles}
                  disabled={selected.length === 0}
                >
                  Clear all
                </button>
                <button
                  className="btn btn--quiet btn--sm"
                  type="button"
                  onClick={onRestoreDefaults}
                  disabled={!library}
                >
                  Restore defaults
                </button>
              </div>

              {library && (
                <input
                  className="input"
                  placeholder="Search styles — try 'metaphor', 'argument', 'AI'"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              )}
            </div>

            {selected.length === 0 && !hasCustom && (
              <p className="callout callout--warn">
                Nothing selected, so there is nothing to generate. Pick a style, or write
                your own brief at the bottom of this tab.
              </p>
            )}

            {dropped > 0 ? (
              <p className="callout callout--warn">
                Your brief takes one of the {maxSelected} slots, so the last{' '}
                {dropped === 1 ? 'style you picked' : `${dropped} styles you picked`} will sit
                this one out. Deselect {dropped === 1 ? 'one' : `${dropped}`} to choose which.
              </p>
            ) : (
              atLimit && (
                <p className="callout callout--info">
                  At the {maxSelected}-direction limit. Each one is its own model call, so
                  deselect a style to add another.
                </p>
              )
            )}

            {library && (
              <>
                {grouped.map(({ group, items }) => {
                  const open = searching || openGroups.includes(group.id)
                  const chosenHere = items.filter((i) => selected.includes(i.name)).length
                  return (
                    <div key={group.id} style={S.group}>
                      <button
                        type="button"
                        className="group-head"
                        aria-expanded={open}
                        onClick={() => {
                          if (!searching) {
                            setOpenGroups((g) =>
                              g.includes(group.id) ? g.filter((x) => x !== group.id) : [...g, group.id],
                            )
                          }
                        }}
                      >
                        <span style={S.spacer}>{group.label}</span>
                        {chosenHere > 0 && <span className="tab__count">{chosenHere}</span>}
                        <span style={S.chevron}>{open ? '▲' : '▼'}</span>
                      </button>

                      {open && (
                        <>
                          <p className="field__hint">{group.blurb}</p>
                          <div style={S.styleList}>
                            {items.map((s) => {
                              const on = selected.includes(s.name)
                              return (
                                <button
                                  key={s.name}
                                  type="button"
                                  className="style"
                                  aria-pressed={on}
                                  disabled={!on && atLimit}
                                  onClick={() => onToggleStyle(s.name)}
                                >
                                  <span className="style__box">{on ? '✓' : ''}</span>
                                  <span style={S.styleText}>
                                    <span className="style__name">{s.name}</span>
                                    <span className="style__desc">{s.description}</span>
                                  </span>
                                </button>
                              )
                            })}
                          </div>
                        </>
                      )}
                    </div>
                  )
                })}

                {grouped.length === 0 && <p className="note">No styles match “{query}”.</p>}
              </>
            )}

            <div className="field">
              <label className="field__label">Your own style</label>
              <textarea
                className="textarea"
                rows={3}
                placeholder="Describe a style in your own words — e.g. 'clipped and unsentimental, like a case file, but every third sentence lands a joke'"
                value={controls.custom_persona}
                onChange={(e) => set('custom_persona', e.target.value)}
              />
              <span className="field__hint">
                Runs as its own direction alongside the presets, and takes one of the{' '}
                {maxSelected} slots. It works with no preset selected at all.
              </span>
            </div>
          </>
        )}

        {/* ── Shape ───────────────────────────────────────────────────────── */}
        {tab === 'shape' && (
          <>
            <Choice
              label="Divergence"
              options={DIVERGENCE_NOTCHES}
              value={controls.divergence}
              onPick={(v) => set('divergence', v)}
            />
            <Choice
              label="Format"
              options={FORMAT_OPTIONS}
              value={controls.fmt}
              onPick={(v) => set('fmt', v)}
            />
            <Choice
              label="Length"
              options={LENGTH_OPTIONS}
              value={controls.length}
              onPick={(v) => set('length', v)}
            />
            <Choice
              label="Opening"
              options={OPENING_OPTIONS}
              value={controls.opening}
              onPick={(v) => set('opening', v)}
            />
            <Choice
              label="Sentence rhythm"
              options={RHYTHM_OPTIONS}
              value={controls.rhythm}
              onPick={(v) => set('rhythm', v)}
              hint="Rhythm is one of the twelve markers the distinctiveness score measures, so a change here usually shows up on the meter."
            />
          </>
        )}

        {/* ── Register ────────────────────────────────────────────────────── */}
        {tab === 'register' && (
          <>
            <Choice
              label="Person"
              options={POV_OPTIONS}
              value={controls.pov}
              onPick={(v) => set('pov', v)}
            />
            <Choice
              label="Tense"
              options={TENSE_OPTIONS}
              value={controls.tense}
              onPick={(v) => set('tense', v)}
            />
            <Choice
              label="Diction"
              options={VOCABULARY_OPTIONS}
              value={controls.vocabulary}
              onPick={(v) => set('vocabulary', v)}
            />
            <div className="field">
              <label className="field__label">Tone</label>
              <input
                className="input"
                placeholder="warm and candid · authoritative · wry"
                value={controls.tone}
                onChange={(e) => set('tone', e.target.value)}
              />
            </div>
            <div className="field">
              <label className="field__label">Audience</label>
              <input
                className="input"
                placeholder="busy executives · complete newcomers · fellow specialists"
                value={controls.audience}
                onChange={(e) => set('audience', e.target.value)}
              />
            </div>
          </>
        )}

        {/* ── Guards ──────────────────────────────────────────────────────── */}
        {tab === 'guards' && (
          <>
            <Toggle
              checked={controls.preserve_facts}
              onChange={(v) => set('preserve_facts', v)}
              label="Preserve facts"
              hint="Directions may not introduce anything absent from your draft. Turns on the faithfulness check and lists any unsupported claim."
            />
            <Toggle
              checked={controls.avoid_ai_cadence}
              onChange={(v) => set('avoid_ai_cadence', v)}
              label="Strip AI cadence"
              hint="Bans tricolons, 'not just X but Y', em-dash asides, summarising closers, and the over-represented LLM lexicon — across every style."
            />
            <div className="field">
              <label className="field__label">Never use these words</label>
              <textarea
                className="textarea"
                rows={2}
                placeholder="delve, tapestry, at the end of the day"
                value={controls.banned_words}
                onChange={(e) => set('banned_words', e.target.value)}
              />
              <span className="field__hint">
                Comma- or line-separated. Applied on top of each style's own ban list.
              </span>
            </div>
            <div className="field">
              <label className="field__label">Keep these exactly</label>
              <textarea
                className="textarea"
                rows={2}
                placeholder="the line you already like, word for word"
                value={controls.keep_phrases}
                onChange={(e) => set('keep_phrases', e.target.value)}
              />
              <span className="field__hint">
                Every direction must carry these through verbatim. Use it to protect a
                sentence you don't want rewritten.
              </span>
            </div>
          </>
        )}

        {/* ── Voice ───────────────────────────────────────────────────────── */}
        {tab === 'voice' && (
          <>
            <div className="field">
              <label className="field__label">
                Voice anchoring — {voiceStrengthLabel(controls.voice_strength)}
              </label>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={controls.voice_strength}
                disabled={!voiceActive}
                onChange={(e) => set('voice_strength', Number(e.target.value))}
                style={{ opacity: voiceActive ? 1 : 0.4 }}
              />
              <span className="field__hint">
                {voiceActive
                  ? 'Higher hugs your voice more tightly, which trades off against distinctiveness.'
                  : 'Add samples below to enable voice anchoring and the voice-match axis.'}
              </span>
            </div>

            <hr style={S.rule} />

            <VoiceOnboarding
              fingerprint={fingerprint}
              onAddSamples={onAddSamples}
              onClear={onClearVoice}
              loading={voiceLoading}
              error={voiceError}
            />
          </>
        )}
      </div>
    </section>
  )
}

// ── Building blocks ───────────────────────────────────────────────────────────

/**
 * One choice among a small set.
 *
 * Three options or fewer get a segmented control, because side-by-side is the
 * fastest thing to read and to hit. Four or more get a select, because segments
 * that narrow stop being legible in a 400px column. Either way the chosen
 * option's explanation is shown underneath, so nothing depends on a hover.
 */
function Choice<T extends string>({
  label,
  options,
  value,
  onPick,
  hint,
}: {
  label: string
  options: Option<T>[]
  value: T
  onPick: (v: T) => void
  hint?: string
}) {
  const active = options.find((o) => o.value === value)
  return (
    <div className="field">
      <label className="field__label">{label}</label>
      {options.length <= 3 ? (
        <div className="seg" role="group" aria-label={label}>
          {options.map((o) => (
            <button
              key={o.value}
              type="button"
              aria-pressed={o.value === value}
              title={o.hint}
              onClick={() => onPick(o.value)}
            >
              {o.label}
            </button>
          ))}
        </div>
      ) : (
        <select
          className="select"
          value={value}
          aria-label={label}
          onChange={(e) => onPick(e.target.value as T)}
        >
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      )}
      {active?.hint && <span className="field__hint">{active.hint}</span>}
      {hint && <span className="field__hint">{hint}</span>}
    </div>
  )
}

function Toggle({
  checked,
  onChange,
  label,
  hint,
}: {
  checked: boolean
  onChange: (v: boolean) => void
  label: string
  hint: string
}) {
  return (
    <button
      type="button"
      className="toggle"
      aria-pressed={checked}
      onClick={() => onChange(!checked)}
    >
      <span className="toggle__box">{checked ? '✓' : ''}</span>
      <span style={S.toggleText}>
        <span className="toggle__label">{label}</span>
        <span className="toggle__hint">{hint}</span>
      </span>
    </button>
  )
}

function voiceStrengthLabel(v: number): string {
  if (v <= 0.05) return 'off'
  if (v < 0.33) return 'light echo'
  if (v < 0.66) return 'balanced'
  return 'hug tightly'
}

// ── Layout-only styles (everything visual lives in index.css) ─────────────────

const S: Record<string, React.CSSProperties> = {
  card: { flex: 1, minHeight: 0 },
  /* Roomier than the rest of the chrome on purpose: this is the panel you sit in
     and work, so rows get space to be hit and read rather than being packed.
     The 14px top padding is what `.sticky-head`'s offset cancels. */
  body: { display: 'flex', flexDirection: 'column', gap: 14, padding: '14px 15px', flex: 1 },
  selRow: { display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap' },
  spacer: { flex: 1 },
  group: { display: 'flex', flexDirection: 'column', gap: 7 },
  chevron: { fontSize: 8 },
  styleList: { display: 'flex', flexDirection: 'column', gap: 6 },
  styleText: { display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 },
  toggleText: { display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 },
  rule: { border: 'none', borderTop: '1px solid var(--rule)', margin: '2px 0' },
}
