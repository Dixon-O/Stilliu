"""
runlog.py — persist the output of the live measurement scripts.

`calibrate.py` and `validate_pipeline.py` make real watsonx calls and then print
their findings to stdout, where they are lost the moment the terminal scrolls.
That is a problem for a measurement tool specifically: the numbers those scripts
produce are the evidence that the scoring works, so they need to survive the run
that produced them.

Every run is written twice:
  results/<kind>-<utc-timestamp>.json   the permanent record of that run
  results/<kind>-latest.json            the most recent, at a stable path

The timestamped file is what you compare against later — "did the score move
after I changed the weights?" is only answerable if the old numbers still exist.
The `latest` copy is for anything that wants to read the current state without
globbing for the newest file.

Results are gitignored: these are live model outputs, and generated prose is not
something to commit by reflex. Quote the numbers in the README by hand.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"


def save(kind: str, payload: dict) -> Path:
    """
    Write one run record. `kind` becomes the filename prefix ("calibration",
    "validation"). Returns the path of the timestamped file.
    """
    RESULTS_DIR.mkdir(exist_ok=True)

    stamped = datetime.now(timezone.utc)
    record = {
        "kind": kind,
        "recorded_at": stamped.isoformat(timespec="seconds"),
        **payload,
    }

    # ':' is illegal in Windows filenames, so the timestamp is compacted rather
    # than written in ISO form.
    slug = stamped.strftime("%Y%m%d-%H%M%S")
    path = RESULTS_DIR / f"{kind}-{slug}.json"
    body = json.dumps(record, indent=2, ensure_ascii=False)

    path.write_text(body, encoding="utf-8")
    (RESULTS_DIR / f"{kind}-latest.json").write_text(body, encoding="utf-8")

    return path


def announce(path: Path) -> None:
    """Tell the operator where the record went, in a copy-pasteable form."""
    try:
        shown = path.relative_to(Path.cwd())
    except ValueError:
        shown = path
    print(f"\nSaved to {shown}")
    print(f"Latest also at {path.parent.name}/{path.name.split('-')[0]}-latest.json")
