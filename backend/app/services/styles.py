"""
styles.py — Stilliu's style preset library.

Single source of truth for every named style Stilliu can write in. The API
exposes this via GET /api/styles so the frontend never hardcodes the list.

DESIGN RULES (each one is deliberate — see README "Why these presets"):

 1. Every preset is defined by *operationalisable* levers — sentence-length
    distribution, clause depth, concreteness, figurative density, dialogue
    ratio, function-word profile. That means the scorer can actually verify the
    rewrite moved, instead of us taking the model's word for it.

 2. Presets are named for a *stance*, never for an author. Naming a preset
    "Hemingway" invites impersonation problems and, worse, pushes every user
    toward the same small set of canonical voices — the "cookie-cutter" trap
    that comparative tools like AutoCrit get criticised for.

 3. Presets are GROUPED, and the groups are shown in the UI. Naming the
    dimensions of a design space measurably reduces fixation (Luminate,
    CHI 2024) — users explore an axis rather than picking the first chip.

 4. Each preset carries `avoid` — explicit negative constraints. Positive-only
    style prompts drift back to the model's defaults; the bans are what create
    measurable divergence.

Groups: compression · sensory · argument · voice · counter_llm
"""
from __future__ import annotations

# ── Group metadata (drives the UI section headers) ───────────────────────────

GROUPS: list[dict] = [
    {
        "id": "compression",
        "label": "Compression",
        "blurb": "How much the prose withholds. Travel along this axis to change density.",
    },
    {
        "id": "sensory",
        "label": "Sensory & Figurative",
        "blurb": "How much the prose renders. Abstraction at one end, physical detail at the other.",
    },
    {
        "id": "argument",
        "label": "Argument & Rhetoric",
        "blurb": "How much the prose presses. Changes the shape of the reasoning, not just the words.",
    },
    {
        "id": "voice",
        "label": "Voice & Persona",
        "blurb": "Who is speaking. Shifts the narrator's stance toward the reader and the material.",
    },
    {
        "id": "counter_llm",
        "label": "Counter-LLM",
        "blurb": "Direct antidotes to default AI cadence. Highest distinctiveness gain, highest risk.",
    },
]


# ── The library ───────────────────────────────────────────────────────────────
# `instruction` is prepended to the prompt. `avoid` becomes an explicit ban list.

STYLES: list[dict] = [
    # ── Compression ──────────────────────────────────────────────────────────
    {
        "name": "Sparse Minimalist",
        "group": "compression",
        "description": "Short sentences. Nothing decorative. Meaning carried by what is left out.",
        "instruction": (
            "Style: Sparse Minimalist. Short declarative sentences only. "
            "Strip every adjective that does not change meaning. Carry the point by "
            "omission — trust the reader to supply what you leave unsaid."
        ),
        "avoid": "adjective stacking, metaphor, rhetorical questions, filler phrases, subordinate clauses",
    },
    {
        "name": "Telegraphic",
        "group": "compression",
        "description": "Fragments. Dropped articles. Maximum information per syllable.",
        "instruction": (
            "Style: Telegraphic. Write in fragments. Drop articles and copulas where "
            "sense survives without them. Clipped noun phrases. Maximum information "
            "per syllable, as though every word costs money."
        ),
        "avoid": "complete grammatical sentences throughout, connective tissue, restatement",
    },
    {
        "name": "Long-Breath Cumulative",
        "group": "compression",
        "description": "One long sentence accreting clause on clause, gathering momentum.",
        "instruction": (
            "Style: Long-Breath Cumulative. Build long sentences by right-branching "
            "accretion — each clause adding to the last, comma after comma, so the "
            "sentence gathers momentum rather than stopping. Use few full stops."
        ),
        "avoid": "short sentences, staccato rhythm, bullet structure, frequent full stops",
    },
    {
        "name": "Plainspoken Reportorial",
        "group": "compression",
        "description": "Concrete nouns, past tense, verifiable detail only. Zero interiority.",
        "instruction": (
            "Style: Plainspoken Reportorial. Concrete nouns and past-tense verbs. "
            "Report only what could be verified by an observer in the room. No "
            "interpretation, no interiority, no editorialising."
        ),
        "avoid": "interiority, speculation about motives, abstraction, lyricism, adverbs of judgement",
    },

    # ── Sensory & Figurative ─────────────────────────────────────────────────
    {
        "name": "Sensory-Led",
        "group": "sensory",
        "description": "Grounds ideas in physical sensation, texture, and concrete scene.",
        "instruction": (
            "Style: Sensory-Led. Open on a concrete sensory detail — something seen, "
            "heard, felt, tasted or smelled. Ground every abstract idea in a physical "
            "object or a specific moment before moving on from it."
        ),
        "avoid": "opening on an abstract claim or statistic, the words 'important', 'significant', 'interesting'",
    },
    {
        "name": "Metaphor-Dense",
        "group": "sensory",
        "description": "One live figure per beat, all drawn from a single controlling domain.",
        "instruction": (
            "Style: Metaphor-Dense. Choose ONE controlling domain of imagery (weather, "
            "machinery, water, debt, surgery — pick one and commit) and draw every "
            "figure from it. One live metaphor per beat. Sustain the domain to the end."
        ),
        "avoid": "dead metaphors, mixed or scattered imagery, cliché figures, literal-only passages",
    },
    {
        "name": "Object-Anchored",
        "group": "sensory",
        "description": "Told through physical props and how they're handled. Emotion inferred.",
        "instruction": (
            "Style: Object-Anchored. Tell it through physical objects and how people "
            "handle them. Let emotion be inferred from what hands do with things. "
            "Never name the feeling — show the prop."
        ),
        "avoid": "naming emotions directly, abstract nouns as subjects, explanatory summary",
    },
    {
        "name": "Synaesthetic / Estranged",
        "group": "sensory",
        "description": "Deliberate category-crossing. Defamiliarises the ordinary.",
        "instruction": (
            "Style: Synaesthetic and Estranged. Cross sensory categories deliberately — "
            "sounds have texture, colours have temperature. Describe the familiar as "
            "though encountering it for the first time, without a name for it."
        ),
        "avoid": "conventional collocations, expected adjective-noun pairings, explanatory glosses",
    },

    # ── Argument & Rhetoric ──────────────────────────────────────────────────
    {
        "name": "The Arguer",
        "group": "argument",
        "description": "Leads with a bold claim. Builds a case. Answers the strongest objection.",
        "instruction": (
            "Style: The Arguer. Open with a bold, direct claim. Build the case step by "
            "step, making each warrant explicit. Then state the strongest objection and "
            "refute it."
        ),
        "avoid": "hedging ('perhaps', 'might', 'some people think'), opening with a question, both-sidesing",
    },
    {
        "name": "Socratic Interrogator",
        "group": "argument",
        "description": "Advances entirely by questions. Withholds every assertion.",
        "instruction": (
            "Style: Socratic Interrogator. Advance the thinking through questions alone. "
            "Each question should narrow the ground the previous one opened. Withhold "
            "your conclusion — let the sequence imply it."
        ),
        "avoid": "declarative conclusions, answering your own questions, rhetorical questions used as assertions",
    },
    {
        "name": "Aphorist",
        "group": "argument",
        "description": "Short freestanding propositions. Parallelism, antithesis, no scaffolding.",
        "instruction": (
            "Style: Aphorist. Write short freestanding propositions that could each be "
            "quoted alone. Use parallelism and antithesis. Remove all connective "
            "scaffolding between them — no 'therefore', no 'because', no transitions."
        ),
        "avoid": "transitions, connectives, worked examples, qualifying clauses",
    },
    {
        "name": "Steelman-then-Break",
        "group": "argument",
        "description": "States the opposing case in genuine good faith at length, then dismantles it.",
        "instruction": (
            "Style: Steelman-then-Break. Spend the first half stating the opposing case "
            "in genuine good faith — strong enough that its holders would endorse your "
            "version. Then dismantle it on the precise point where it fails."
        ),
        "avoid": "strawmanning, sarcasm in the steelman half, conceding nothing, hedged conclusions",
    },

    # ── Voice & Persona ──────────────────────────────────────────────────────
    {
        "name": "Confiding Second Person",
        "group": "voice",
        "description": "Direct address, present tense, conspiratorial register.",
        "instruction": (
            "Style: Confiding Second Person. Address the reader directly as 'you', in "
            "present tense. Conspiratorial register — as though telling them something "
            "slightly indiscreet, just between you."
        ),
        "avoid": "third-person distance, past tense, formal register, generic 'one'",
    },
    {
        "name": "Deadpan Ironist",
        "group": "voice",
        "description": "Flat affect over high-stakes content. Understatement, no signposted jokes.",
        "instruction": (
            "Style: Deadpan Ironist. Keep the affect flat and the register level while "
            "the content escalates. Understate the significant. Let the gap between "
            "tone and stakes do the work."
        ),
        "avoid": "signposted jokes, exclamation marks, explicit irony markers, emotive adjectives",
    },
    {
        "name": "Unreliable Close-Third",
        "group": "voice",
        "description": "Free indirect discourse with visible self-deception.",
        "instruction": (
            "Style: Unreliable Close-Third. Narrate in free indirect discourse, close "
            "inside one perspective. Let the narration quietly contradict the evidence "
            "of the scene, so the reader sees past the narrator."
        ),
        "avoid": "omniscient correction, reliable summary, explicit signalling of the unreliability",
    },
    {
        "name": "Bureaucratic Uncanny",
        "group": "voice",
        "description": "Procedural, passive, register-flattened prose over loaded material.",
        "instruction": (
            "Style: Bureaucratic Uncanny. Use procedural, passive, register-flattened "
            "administrative prose — and apply it to emotionally loaded material without "
            "ever acknowledging the mismatch."
        ),
        "avoid": "emotive language, first-person feeling, acknowledging the absurdity, warmth",
    },

    # ── Counter-LLM ──────────────────────────────────────────────────────────
    {
        "name": "Anti-Cadence",
        "group": "counter_llm",
        "description": "Strips the structural tells of default AI prose. Highest distinctiveness gain.",
        "instruction": (
            "Style: Anti-Cadence. Actively defeat default AI prose rhythm. Vary "
            "paragraph length unpredictably. Let sentence openings differ from one "
            "another. End on a specific, concrete detail rather than a summary."
        ),
        "avoid": (
            "tricolons and three-item lists, the 'not just X but Y' construction, "
            "em-dash asides, symmetrical paragraph shapes, summarising final sentences, "
            "'delve', 'leverage', 'tapestry', 'realm', 'testament', 'landscape', "
            "'navigate', 'underscore', 'crucial', 'multifaceted'"
        ),
    },
    {
        "name": "Rough Draft Energy",
        "group": "counter_llm",
        "description": "Uneven, digressive, unresolved. Sounds like a person thinking, not a model concluding.",
        "instruction": (
            "Style: Rough Draft Energy. Write like a sharp person thinking on the page. "
            "Uneven paragraph lengths. Take exactly one genuine digression and come back "
            "from it. Leave one thread deliberately unresolved. Do not tie it up."
        ),
        "avoid": "summarising conclusions, balanced structure, 'in conclusion', tidy resolution, even paragraph lengths",
    },
]


# ── Lookups & helpers ─────────────────────────────────────────────────────────

STYLES_BY_NAME: dict[str, dict] = {s["name"]: s for s in STYLES}

#: Shown when the writer hasn't picked anything — one from each of three groups
#: so the very first result already demonstrates the spread of the axes.
DEFAULT_STYLE_NAMES: list[str] = ["Sparse Minimalist", "The Arguer", "Sensory-Led"]

#: Hard ceiling on how many directions one request may generate. Each is a
#: parallel LLM call, so this bounds both latency and token spend.
MAX_SELECTED_STYLES = 6

#: Label for the direction built from the writer's own free-text brief. It is
#: not in STYLES (it has no fixed instruction), but the UI needs to name its tab
#: and POST /api/direction needs to accept it, so both read it from here rather
#: than hardcoding the string in two places.
CUSTOM_STYLE_NAME = "Your Custom Direction"


def custom_style(brief: str) -> dict:
    """Build a one-off style from the writer's free-text brief."""
    brief = brief.strip()
    return {
        "name": CUSTOM_STYLE_NAME,
        "group": "custom",
        "description": brief[:80],
        "instruction": f"Style brief from the writer, follow it precisely: {brief}",
        "avoid": "",
    }


def group_label(group_id: str) -> str:
    for g in GROUPS:
        if g["id"] == group_id:
            return str(g["label"])
    return group_id


def styles_payload() -> dict:
    """Shape returned by GET /api/styles — the frontend renders straight from this."""
    return {
        "groups": GROUPS,
        "styles": [
            {
                "name": s["name"],
                "group": s["group"],
                "group_label": group_label(s["group"]),
                "description": s["description"],
            }
            for s in STYLES
        ],
        "defaults": DEFAULT_STYLE_NAMES,
        "max_selected": MAX_SELECTED_STYLES,
        "custom_style_name": CUSTOM_STYLE_NAME,
    }


def build_instruction(style: dict) -> str:
    """Compose the positive instruction and the ban list into one prompt clause."""
    text = f"Rewrite the text below. {style['instruction']}"
    avoid = style.get("avoid", "")
    if avoid:
        text += f" Do not use: {avoid}."
    return text


# ── Backwards compatibility ───────────────────────────────────────────────────
# generation.py and the tests originally imported PERSONAS/PERSONAS_BY_NAME.
# Keep those names bound to the new library so nothing breaks.
PERSONAS = STYLES
PERSONAS_BY_NAME = STYLES_BY_NAME
