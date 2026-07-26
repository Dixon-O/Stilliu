"""
integration_test.py — Live end-to-end test against the running FastAPI backend.

Start the backend first:
  uvicorn app.main:app --port 8000

Then run:
  python integration_test.py
"""
import json
import urllib.request
import urllib.error

BASE = "http://localhost:8000"

TEST_DRAFT = (
    "Nobody warned me the hardest part of starting a company is the silence. "
    "Not the rejections — the silence between them. "
    "Three weeks without a single email and you start wondering if you imagined the whole thing."
)

TEST_VOICE_SAMPLES = [
    "The thing about Lagos traffic is it teaches you patience or it breaks you. There's no middle. "
    "I've watched men sob quietly in gridlock at 9am on a Tuesday. I've been that man.",
    "Every city has its particular cruelty. London's is the weather pretending it might improve. "
    "You pack an umbrella and it mocks you with sun.",
]


def post(path: str, data: dict) -> dict:
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def get(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=10) as resp:
        return json.loads(resp.read())


def section(title: str):
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


# ── Health ────────────────────────────────────────────────────────────────────
section("1. HEALTH CHECK")
h = get("/health")
print(f"  status:      {h['status']}")
print(f"  demo_mode:   {h['demo_mode']}")
print(f"  embed_model: {h.get('embed_model', '—')}")
print(f"  gen_model:   {h.get('gen_model', '—')}")
assert h["status"] == "ok", "Health check failed"

# ── Score only (fast path) ────────────────────────────────────────────────────
section("2. /api/score  (fast path — scores only)")
print(f"  Draft: \"{TEST_DRAFT[:80]}...\"")
print("  Calling /api/score (may take ~10–20s live)...")

score_res = post("/api/score", {"draft": TEST_DRAFT})
scores = score_res["scores"]
print(f"\n  generic_distance:  {scores['generic_distance']} / 100")
print(f"  generic_raw:       {scores['generic_raw']}")
print(f"  voice_distance:    {scores['voice_distance']} (None — no samples sent)")
print(f"  baseline_preview:  \"{score_res.get('baseline_preview', '')[:80]}\"")
print(f"  demo_mode:         {score_res['demo_mode']}")

assert 0 <= scores["generic_distance"] <= 100, "Generic score out of range"
assert scores["voice_distance"] is None, "Expected no voice score without samples"

# ── Score with voice samples ──────────────────────────────────────────────────
section("3. /api/score  (with voice fingerprint)")
print("  Calling /api/score with 2 voice samples...")
score_voice_res = post("/api/score", {
    "draft": TEST_DRAFT,
    "voice_samples": TEST_VOICE_SAMPLES,
})
sv = score_voice_res["scores"]
print(f"\n  generic_distance:  {sv['generic_distance']} / 100")
print(f"  voice_distance:    {sv['voice_distance']} / 100  ← unlocked")
print(f"  voice_raw:         {sv['voice_raw']}")

assert sv["voice_distance"] is not None, "Expected voice score with samples"
assert 0 <= sv["voice_distance"] <= 100, "Voice score out of range"

# ── Full analyze ──────────────────────────────────────────────────────────────
section("4. /api/analyze  (full — scores + directions)")
print("  Calling /api/analyze (may take ~30–60s live)...")
full_res = post("/api/analyze", {"draft": TEST_DRAFT})
print(f"\n  generic_distance:  {full_res['scores']['generic_distance']} / 100")
print(f"  Directions returned: {len(full_res['directions'])}")
for card in full_res["directions"]:
    print(f"\n  [{card['persona']}]  score={card['generic_distance']}/100")
    print(f"  {card['text'][:120]}...")

assert len(full_res["directions"]) == 3, "Expected 3 direction cards"

section("ALL INTEGRATION TESTS PASSED")
