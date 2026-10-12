"""Seed sample data for testing the manager→performer loop.

Creates realistic history so workflows have signal to work with:
  1. Character instances (battle history with scores/modulators) → bgraph2 graph
  2. YouTube videos with views/likes (simulated channel with content) → yt cache + learn tables
  3. Feedback edges (judged ratings) → graph

Usage:
  python3 scripts/seed_test_data.py --character no_nose_nolan --scenario winners
  python3 scripts/seed_test_data.py --character no_nose_nolan --scenario mixed
  python3 scripts/seed_test_data.py --clear  (remove all seeded test data)

Scenarios:
  winners — condescending/paranoid modulators winning, bureaucratic themes performing
  mixed   — no clear pattern (tests hold/experiment path)
  losers  — everything underperforming (tests pivot path)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, "/root/characters/sdk")
sys.path.insert(0, "/root/influence2")

import character_sdk as sdk
from pipeline import learn as learn

GRAPH_DIR = "/root/bgraph2/registry/characters"

# Sample battle history — 5 instances with realistic scores
SAMPLE_INSTANCES = {
    "winners": [
        {"instance_id": "test-inst-001", "seed_id": "seed-overlay-v1", "scenario_id": "evidence-room-audit",
         "modulator": "condescending", "operator": "rigidify", "battle_score": 0.82, "judge_rating": 8.0},
        {"instance_id": "test-inst-002", "seed_id": "seed-overlay-v1", "scenario_id": "promotion-review",
         "modulator": "paranoid", "operator": "escalate", "battle_score": 0.78, "judge_rating": 7.5},
        {"instance_id": "test-inst-003", "seed_id": "seed-overlay-v1", "scenario_id": "evidence-room-audit",
         "modulator": "condescending", "operator": "misdirect", "battle_score": 0.85, "judge_rating": 8.5},
        {"instance_id": "test-inst-004", "seed_id": "seed-overlay-v1", "scenario_id": "parking-dispute",
         "modulator": "exhausted", "operator": "deflect", "battle_score": 0.45, "judge_rating": 4.0},
        {"instance_id": "test-inst-005", "seed_id": "seed-overlay-v1", "scenario_id": "promotion-review",
         "modulator": "smug", "operator": "reframe", "battle_score": 0.51, "judge_rating": 5.0},
    ],
    "mixed": [
        {"instance_id": "test-inst-001", "seed_id": "seed-overlay-v1", "scenario_id": "evidence-room-audit",
         "modulator": "condescending", "operator": "rigidify", "battle_score": 0.55, "judge_rating": 5.5},
        {"instance_id": "test-inst-002", "seed_id": "seed-overlay-v1", "scenario_id": "promotion-review",
         "modulator": "paranoid", "operator": "escalate", "battle_score": 0.58, "judge_rating": 6.0},
        {"instance_id": "test-inst-003", "seed_id": "seed-overlay-v1", "scenario_id": "parking-dispute",
         "modulator": "exhausted", "operator": "deflect", "battle_score": 0.52, "judge_rating": 5.0},
        {"instance_id": "test-inst-004", "seed_id": "seed-overlay-v1", "scenario_id": "coffee-machine",
         "modulator": "smug", "operator": "misdirect", "battle_score": 0.57, "judge_rating": 5.5},
        {"instance_id": "test-inst-005", "seed_id": "seed-overlay-v1", "scenario_id": "fire-drill",
         "modulator": "angry", "operator": "escalate", "battle_score": 0.54, "judge_rating": 5.0},
    ],
    "losers": [
        {"instance_id": "test-inst-001", "seed_id": "seed-overlay-v1", "scenario_id": "evidence-room-audit",
         "modulator": "condescending", "operator": "rigidify", "battle_score": 0.32, "judge_rating": 3.0},
        {"instance_id": "test-inst-002", "seed_id": "seed-overlay-v1", "scenario_id": "promotion-review",
         "modulator": "paranoid", "operator": "escalate", "battle_score": 0.28, "judge_rating": 2.5},
        {"instance_id": "test-inst-003", "seed_id": "seed-overlay-v1", "scenario_id": "parking-dispute",
         "modulator": "exhausted", "operator": "deflect", "battle_score": 0.35, "judge_rating": 3.5},
        {"instance_id": "test-inst-004", "seed_id": "seed-overlay-v1", "scenario_id": "coffee-machine",
         "modulator": "smug", "operator": "misdirect", "battle_score": 0.30, "judge_rating": 3.0},
        {"instance_id": "test-inst-005", "seed_id": "seed-overlay-v1", "scenario_id": "fire-drill",
         "modulator": "angry", "operator": "escalate", "battle_score": 0.25, "judge_rating": 2.0},
    ],
}

# Sample YouTube videos with realistic metrics
SAMPLE_VIDEOS = {
    "winners": [
        {"id": "test-vid-001", "title": "Nolan Audits the Evidence Room (GONE WRONG)",
         "views": 12500, "likes": 890, "comments": 134, "published": "2026-10-05T10:00:00Z"},
        {"id": "test-vid-002", "title": "Performance Review: Nolan Rates Your Productivity",
         "views": 9800, "likes": 720, "comments": 98, "published": "2026-10-07T10:00:00Z"},
        {"id": "test-vid-003", "title": "Nolan Explains Why Your Parking Is Non-Compliant",
         "views": 2100, "likes": 120, "comments": 15, "published": "2026-10-09T10:00:00Z"},
        {"id": "test-vid-004", "title": "Coffee Machine Incident Report #47",
         "views": 1800, "likes": 95, "comments": 11, "published": "2026-10-10T10:00:00Z"},
        {"id": "test-vid-005", "title": "Fire Drill Compliance Audit (LIVE)",
         "views": 3200, "likes": 210, "comments": 28, "published": "2026-10-11T10:00:00Z"},
    ],
    "mixed": [
        {"id": "test-vid-001", "title": "Nolan Audits the Evidence Room",
         "views": 3200, "likes": 180, "comments": 22, "published": "2026-10-05T10:00:00Z"},
        {"id": "test-vid-002", "title": "Performance Review Basics",
         "views": 3100, "likes": 175, "comments": 20, "published": "2026-10-07T10:00:00Z"},
        {"id": "test-vid-003", "title": "Parking Compliance Update",
         "views": 2900, "likes": 160, "comments": 18, "published": "2026-10-09T10:00:00Z"},
        {"id": "test-vid-004", "title": "Coffee Machine Rules",
         "views": 3300, "likes": 190, "comments": 24, "published": "2026-10-10T10:00:00Z"},
        {"id": "test-vid-005", "title": "Fire Drill Procedures",
         "views": 3000, "likes": 170, "comments": 19, "published": "2026-10-11T10:00:00Z"},
    ],
    "losers": [
        {"id": "test-vid-001", "title": "Nolan Audits the Evidence Room",
         "views": 180, "likes": 8, "comments": 1, "published": "2026-10-05T10:00:00Z"},
        {"id": "test-vid-002", "title": "Performance Review Basics",
         "views": 150, "likes": 6, "comments": 0, "published": "2026-10-07T10:00:00Z"},
        {"id": "test-vid-003", "title": "Parking Compliance Update",
         "views": 120, "likes": 5, "comments": 1, "published": "2026-10-09T10:00:00Z"},
        {"id": "test-vid-004", "title": "Coffee Machine Rules",
         "views": 95, "likes": 3, "comments": 0, "published": "2026-10-10T10:00:00Z"},
        {"id": "test-vid-005", "title": "Fire Drill Procedures",
         "views": 110, "likes": 4, "comments": 0, "published": "2026-10-11T10:00:00Z"},
    ],
}


def seed_character(character_id: str, scenario: str) -> dict:
    """Write sample instances + feedback edges to the character graph."""
    g = sdk.load_character(character_id)
    # remove any prior test instances
    g["instances"] = [i for i in g.get("instances", [])
                      if not (i.get("instance_id") or "").startswith("test-inst-")]
    g["edges"] = [e for e in g.get("edges", [])
                  if not (e.get("from") or "").startswith("test-inst-")
                  and e.get("rel") != "directed"]
    sdk.save_character(character_id, g)
    for inst in SAMPLE_INSTANCES[scenario]:
        r = sdk.record_instance(character_id, {
            "instance_id": inst["instance_id"],
            "seed_id": inst["seed_id"],
            "scenario_id": inst["scenario_id"],
            "modulator": inst["modulator"],
            "operator": inst["operator"],
            "battle_score": inst["battle_score"],
        })
        # judge rating as feedback edge (SDK stores rating, not battle_score)
        sdk.ingest_feedback(character_id, inst["instance_id"],
                            inst["judge_rating"],
                            f"test seed ({scenario}): battle={inst['battle_score']}")
    g = sdk.load_character(character_id)
    return {"instances": len(g["instances"]), "edges": len(g["edges"])}


def seed_videos(brand: str, handle: str, scenario: str) -> dict:
    """Write sample videos to learn tables (content_items + snapshots)."""
    ids = []
    for v in SAMPLE_VIDEOS[scenario]:
        ext = f"yt:{v['id']}"
        iid = learn.ensure_item(
            channel="youtube", account=handle, external_id=ext,
            title=v["title"],
            url=f"https://www.youtube.com/watch?v={v['id']}",
            brand_slug=brand, kind="video")
        learn.record_snapshot(iid, window="7d", views=v["views"],
                              likes=v["likes"], comments=v["comments"])
        ids.append(iid)
    return {"items": ids, "count": len(ids)}


def clear_test_data(character_id: str) -> dict:
    """Remove all test-seeded data from graph + learn tables."""
    out = {}
    try:
        g = sdk.load_character(character_id)
        before_i = len(g.get("instances", []))
        before_e = len(g.get("edges", []))
        g["instances"] = [i for i in g.get("instances", [])
                          if not (i.get("instance_id") or "").startswith("test-inst-")]
        g["edges"] = [e for e in g.get("edges", [])
                      if not (e.get("from") or "").startswith("test-inst-")
                      and e.get("rel") != "directed"]
        sdk.save_character(character_id, g)
        out["graph"] = {"removed_instances": before_i - len(g["instances"]),
                        "removed_edges": before_e - len(g["edges"])}
    except FileNotFoundError:
        out["graph"] = {"error": "unknown character"}
    import sqlite3
    db = sqlite3.connect(learn.DB_PATH, timeout=30)
    try:
        rows = db.execute(
            "SELECT id FROM content_items WHERE external_id LIKE 'yt:test-vid-%'"
        ).fetchall()
        for (iid,) in rows:
            db.execute("DELETE FROM performance_snapshots WHERE item_id=?", (iid,))
            db.execute("DELETE FROM content_features WHERE item_id=?", (iid,))
            db.execute("DELETE FROM content_items WHERE id=?", (iid,))
        db.commit()
        out["learn"] = {"removed_items": len(rows)}
    finally:
        db.close()
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--character", default="no_nose_nolan")
    ap.add_argument("--brand", default="long-hauls")
    ap.add_argument("--handle", default="@longhauls")
    ap.add_argument("--scenario", default="winners",
                    choices=["winners", "mixed", "losers"])
    ap.add_argument("--clear", action="store_true")
    a = ap.parse_args()
    if a.clear:
        print(json.dumps(clear_test_data(a.character), indent=2))
    else:
        c = seed_character(a.character, a.scenario)
        v = seed_videos(a.brand, a.handle, a.scenario)
        print(json.dumps({"character": c, "videos": v,
                          "scenario": a.scenario}, indent=2))
