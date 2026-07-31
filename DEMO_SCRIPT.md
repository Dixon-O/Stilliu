# Stilliu — 2:59 demo script

Voiceover script with timestamps, mapped to exactly what is on screen at each beat.

**Total runtime:** 2:59 (179 seconds)
**Narrated words:** 511 → **171 wpm**, which leaves ~8 seconds of slack for the pauses marked below. Most voice artists read 175–190 wpm, so this is a comfortable pace rather than a rushed one.

If your reader is slower than 170 wpm, cut the two sentences marked *optional* rather than speeding up — the 1:55 hold is what the video is for.

**The one line the whole pitch rests on.** It lands twice — at 0:20 and again at 2:52:

> Every AI writing tool can change your voice. None of them can tell you whether it worked.

---

## Structure

| Movement | Time | Job |
|---|---|---|
| 1. The problem nobody measures | 0:00–0:32 | Establish the gap, fast, with numbers |
| 2. The measurement | 0:32–1:20 | Show the score and why it is defensible |
| 3. The intervention and the proof | 1:20–2:20 | The money shot: delta per rewrite |
| 4. The engineering and the close | 2:20–2:59 | Show it holds up, land the line |

---

## 0:00–0:12 — Cold open on the problem

**On screen:** Stilliu's draft panel, a real paragraph already pasted. No dashboard tour, no logo animation. Start inside the product.

> "AI writing tools make every writer better, and every writer more alike. That's measured, not anecdotal — human text scores sixty-six percent higher on creativity than AI text, and the tuning that makes models helpful cuts it by a further thirty."

---

## 0:12–0:32 — Name the gap

**On screen:** Right column, **Style presets** tab. Slowly scroll the 18-preset library — the five group markers are colour-coded, so the range reads at a glance. Click one preset so its `avoid` list expands inside the row (it reveals on selection, not on hover).

> "Every tool here can change your style. Sudowrite, Jasper, the presets in every chat assistant — rich controls, and not one reports back. And every tool that *does* measure prose scores you on conformity to a norm: readability, house style. They reward you for sounding like everyone else.
>
> So you can change your voice, or be told how average you are. Nothing measures whether the change worked."

---

## 0:32–1:00 — The measurement

**On screen:** Click **Score draft** in the action bar. The two rails in the left column populate — Distinct fills, Voice stays locked. Hold on the distinctiveness number.

> "Stilliu asks IBM Granite to write the blandest possible version of your draft. That baseline is the anchor. Then it measures how far your prose sits from it — forty percent semantic distance from Granite embeddings, sixty percent stylometry across twelve features that ignore *what* you wrote and look only at *how*."

**Beat.** Then the line that separates this from a vibes score — *slow down here*:

> "Style carries the larger weight for a reason. Embeddings encode topic, not voice — two rewrites of the same subject sit close together however different the prose. Weight semantics higher and a bold rewrite scores as generic. That was a real bug here, and fixing it is the product."

---

## 1:00–1:20 — Voice, and what the tool refuses to guess

**On screen:** Left column, **Voice samples** tab. Paste two samples and validate. Switch back to **Draft** — the Voice rail has gone from “Needs your writing samples” to a live score. Make that transition visible; it is the tool refusing to guess, then measuring.

> "Add samples of your own writing and a second axis unlocks — how much this still sounds like you. Until you do, it stays locked rather than showing a guessed number.
>
> And there's no overall quality score in this tool, and no AI-detector verdict. Stilliu reports distances on named axes and lets you decide."

---

## 1:20–1:50 — The intervention

**On screen:** Select three presets from three different groups. Switch to the **Controls** tab, set divergence to **Recast**. Click **Write 3 directions**. All three cards land together in the middle column — no tab-switching, every result on screen at once.

> "Eighteen presets in five groups, named for a stance rather than an author — no 'write like Hemingway'. Each one carries a ban list, because positive-only style instructions drift straight back to model defaults.
>
> Divergence is three named notches, not a slider, because each one can state its effect: nudge, recast, break. Up to six directions, all generated at once."

---

## 1:50–2:20 — The proof (the money shot)

**On screen:** Start wide enough to show all three cards side by side, then push into one card's rails. The ghost tick and the fill, clearly apart. **Hold for three full seconds.** This is the shot the entire video exists for — do not cut away early.

> "Here's what no other tool shows you. That tick is your draft. The fill is the rewrite. The gap between them is the claim — on every card at once, so you're never comparing from memory.
>
> Distinctiveness up eighteen. Voice held. On-message seventy-two, so the meaning survived. Change one control and rewrite one direction — a single model call, still measured against the same anchors."

**On screen:** Point at a `refined` badge, then click a `check facts` badge — it expands the unsupported claims inline on the card.

> "This one was regenerated automatically before I saw it — it failed a threshold. This one had claims that aren't in my source, flagged rather than shipped. An earlier build invented a Wall Street Journal interview. Now it gets caught."

---

## 2:20–2:45 — Why it holds up

**On screen:** Terminal. `python -m pytest tests/ -v` → **136 passed**. Then back in the app, click the health pill in the top bar — the popover names all three resolved model roles.

> "A hundred and thirty-six tests, and the whole measurement core runs with no credentials and no network — the model registry never imports the SDK.
>
> And the baseline is never the same model family as the creative one — otherwise you're measuring distance from a colder version of yourself, which is nothing."

---

## 2:45–2:59 — Close

**On screen:** Back out to the full three-column instrument panel, one clean static shot. Hold to the end.

> "Granite embeddings compute every distance. A Granite model writes the anchor. Take Granite out and there is no measurement — which is the entire product.
>
> Every AI tool can change your voice. Stilliu is the one that tells you whether it worked."

---

## Notes for the recording

**Three places to slow down.** The "that was a real bug here" line at 0:52, the three-second rail hold at 1:55, and the final sentence. Everything else can move at pace.

**The one section that cannot be cut** is 1:50–2:20. It is the product claim. If timing runs long, trim the detector aside at 1:12 and the region-resolution line at 2:35 — both are credibility garnish, not the argument.

**Tone.** Measured and specific, not breathless. The numbers do the persuading; the delivery should not oversell them. No exclamation, no rising hype into the close — the last line works because it is flat and certain.

**Screen recording.** Shoot at 1920×1080 or higher, with the browser at a width that keeps all three columns visible (≥1200px viewport). Demo mode is fine for the recording and needs no credentials — but if you record in demo mode, do not say "live" anywhere in the voiceover.

**One continuous session.** Do not cut between a draft and its scores; the credibility of the delta depends on the viewer believing it came from the draft they just watched being measured.
