#!/usr/bin/env python3
"""influence2 autonomous tick — scheduled feedback collection + analytics.

Runs feedback_collect (all signals, all characters) + analytics_review
(LongHauls channel) on cron. Read-only + snapshot writes. Never publishes,
never spends, never auto-approves. Human gates stay human.

Usage:
  python3 scripts/autonomous_tick.py           # full tick
  python3 scripts/autonomous_tick.py --dry-run # validate only, no runs
  python3 scripts/autonomous_tick.py --character no_nose_nolan  # single character

Cron: hourly feedback_collect, daily analytics_review (see systemd units).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time

HERE = "/root/influence2"
RUN_MJS = f"{HERE}/workflows/run.mjs"

# Characters under management (character_id, brand, handle, channel_id)
# channel_id "test-*" reads seeded tables; real IDs hit YouTube API.
MANAGED = [
    {"character_id": "no_nose_nolan", "brand": "long-hauls",
     "handle": "@longhauls", "channel_id": "UCrntJs4IgQNEPUszDgDoXBg"},
]

CHANNELS = [
    {"brand": "long-hauls", "handle": "@longhauls",
     "channel_id": "UCrntJs4IgQNEPUszDgDoXBg"},
]


def run_workflow(name: str, input_data: dict) -> dict:
    """Run a workflow via run.mjs, return parsed result."""
    r = subprocess.run(
        ["node", "--env-file=.env", RUN_MJS, name, json.dumps(input_data)],
        capture_output=True, text=True, timeout=300, cwd=HERE)
    out = (r.stdout or "").strip()
    # find JSON (stdout has "running workflow:" prefix on stderr, JSON on stdout)
    try:
        # output may have non-JSON prefix — find first { or [
        idx = next(i for i, c in enumerate(out) if c in "{[")
        return json.loads(out[idx:])
    except (StopIteration, json.JSONDecodeError):
        return {"status": "error", "raw": (out + r.stderr)[-500:]}


def tick(dry_run: bool = False, only_character: str = "") -> dict:
    """Run the autonomous tick. Returns summary receipt."""
    started = time.time()
    results: dict = {"tick_at": time.time(), "dry_run": dry_run,
                     "feedback": [], "analytics": []}
    if dry_run:
        # validate only
        for wf in ("feedback_collect", "analytics_review",
                   "character_direct", "content_decide", "release_gate"):
            r = subprocess.run(
                ["node", f"{HERE}/workflows/run.mjs", "--validate", wf],
                capture_output=True, text=True, timeout=30)
            results["feedback"].append({wf: "valid" if '"ok":true' in
                                       r.stdout.replace(" ", "") else "INVALID"})
        return results
    # 1. feedback_collect per managed character (fuses all signals)
    for m in MANAGED:
        if only_character and m["character_id"] != only_character:
            continue
        r = run_workflow("feedback_collect", {
            "character_id": m["character_id"], "brand": m["brand"],
            "handle": m["handle"], "channel_id": m["channel_id"]})
        results["feedback"].append({
            "character": m["character_id"],
            "status": r.get("status"),
            "hint": ((r.get("output") or {}).get("direction_hint")),
        })
    # 2. analytics_review per channel (digest + Phoenix scores)
    for c in CHANNELS:
        r = run_workflow("analytics_review", c)
        results["analytics"].append({
            "brand": c["brand"], "status": r.get("status"),
            "health": ((r.get("output") or {}).get("phoenix_health")),
            "severity": ((r.get("output") or {}).get("severity")),
        })
    results["elapsed_s"] = round(time.time() - started, 1)
    # receipt to dash log
    with open(f"{HERE}/dash/receipts.jsonl", "a") as f:
        f.write(json.dumps({"ts": time.time(), "kind": "autonomous_tick",
                            **results}) + "\n")
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--character", default="")
    a = ap.parse_args()
    print(json.dumps(tick(a.dry_run, a.character), indent=2))
