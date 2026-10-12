"""Rank sleepintel 244-channel registry by monetizability.

Adapts rank_sleep_channels scoring to registry fields:
readiness (ready > intake > draft) + effort (lower = cheaper) +
shelf/engine (proven combos) + avatar-intel gaps (empty niches).

Run: python3 scripts/rank_sleepintel.py [--json] [--top N]
"""
from __future__ import annotations

import json
import sys

REGISTRY = "/root/sleepintel/registry/channels.yaml"

# Shelf → product fit (from avatar intel + sleep asset ladders)
SHELF_SCORE = {
    "STORY": 20,      # tales → $27 ebook + $59 bundle (Folk & Fable proven)
    "MIND": 20,       # readable → $27 guide + $47 bundle (farm-adjacent)
    "MUSIC": 18,      # loops + guides (zero comps, sleep playlists love it)
    "SPIRITUAL": 16,  # ritual → tarot $35 + journal $29 (Grimoire model)
    "ESOTERIC": 16,   # same as spiritual, narrower audience
    "PLACE": 8,       # ambient only ($2.99 loops, hard to productize)
    "FRESH": 10,      # unproven (needs format proof)
}

# Engine → readiness multiplier (E2 reading + E5 talk are built)
ENGINE_SCORE = {
    "E2": 15,   # reading: BUILT + 26 pilots
    "E5": 15,   # talk: BUILT + running
    "E1": 12,   # hosted music: needs host
    "E3": 10,   # guided: scripts only
    "E4": 5,    # ambience: UNBUILT (cheapest to build, nothing exists)
    "E6": 5,    # freshness: UNBUILT
}


def load_registry() -> list[dict]:
    try:
        import yaml
        with open(REGISTRY) as f:
            d = yaml.safe_load(f)
        return d.get("channels", [])
    except ImportError:
        pass
    # minimal fallback parse
    channels, cur = [], {}
    with open(REGISTRY) as f:
        for line in f:
            s = line.strip()
            if s.startswith("- id:"):
                if cur:
                    channels.append(cur)
                cur = {"id": s.split(":", 1)[1].strip()}
            elif cur is not None and ":" in s and not s.startswith("-"):
                k, v = s.split(":", 1)
                cur[k.strip()] = v.strip().strip("'\"")
    if cur:
        channels.append(cur)
    return channels


def score_channel(ch: dict) -> dict:
    scores: dict = {}
    reasons: list[str] = []
    # 1. Readiness (30): ready > intake > draft/compile
    r = str(ch.get("readiness", "")).lower()
    if r == "ready":
        scores["readiness"] = 30
        reasons.append("ready to build")
    elif r == "intake":
        scores["readiness"] = 18
        reasons.append("in intake")
    elif r in ("draft", "compile"):
        scores["readiness"] = 8
        reasons.append(f"status: {r}")
    else:
        scores["readiness"] = 5
        reasons.append(f"status unclear: {r or '?'}")
    # 2. Effort inverse (20): lower effort = cheaper to launch
    try:
        effort = int(ch.get("effort", 5) or 5)
    except (ValueError, TypeError):
        effort = 5
    if effort <= 2:
        scores["effort"] = 20
        reasons.append(f"effort {effort} (cheap)")
    elif effort <= 4:
        scores["effort"] = 14
        reasons.append(f"effort {effort} (moderate)")
    else:
        scores["effort"] = 6
        reasons.append(f"effort {effort} (expensive)")
    # 3. Shelf product fit (25)
    shelf = str(ch.get("shelf", "")).upper()
    scores["shelf"] = SHELF_SCORE.get(shelf, 10)
    reasons.append(f"shelf {shelf or '?'}")
    # 4. Engine built (15)
    engines = ch.get("engines", [])
    if isinstance(engines, str):
        engines = [engines]
    best = max([ENGINE_SCORE.get(str(e).strip(), 0) for e in engines] or [0])
    scores["engine"] = best
    reasons.append(f"engines {engines or '?'}")
    # 5. Avatar gap bonus (10): sleep/music/esoteric topics score higher
    # (0 avatar comps in 681) vs saturated farm topics
    tags = str(ch.get("tags", "")).lower()
    pitch = str(ch.get("pitch", "")).lower()
    dept = str(ch.get("dept", "")).lower()
    text = f"{tags} {pitch} {dept}"
    if any(k in text for k in ["sleep", "bedtime", "dream", "night"]):
        scores["gap"] = 10
        reasons.append("sleep-direct (0 avatar comps)")
    elif any(k in text for k in ["music", "piano", "ambient", "soundscape"]):
        scores["gap"] = 10
        reasons.append("music/ambient (0 avatar comps)")
    elif any(k in text for k in ["ritual", "spell", "tarot", "esoteric",
                                  "dream-work", "occult"]):
        scores["gap"] = 10
        reasons.append("esoteric (0 avatar comps)")
    elif any(k in text for k in ["story", "tale", "myth", "fable", "history"]):
        scores["gap"] = 8
        reasons.append("story (proven shelf, no avatar comps)")
    else:
        scores["gap"] = 5
        reasons.append("niche unclear vs avatar data")
    total = sum(scores.values())
    if total >= 75:
        verdict = "LAUNCH_READY"
    elif total >= 55:
        verdict = "PROMISING"
    elif total >= 35:
        verdict = "NEEDS_WORK"
    else:
        verdict = "EARLY"
    return {"id": ch.get("id", "?"), "name": ch.get("name", "?"),
            "scores": scores, "total": total, "verdict": verdict,
            "reasons": reasons, "shelf": shelf,
            "readiness": r, "effort": effort}


def main():
    channels = load_registry()
    ranked = sorted((score_channel(c) for c in channels),
                    key=lambda r: r["total"], reverse=True)
    args = sys.argv[1:]
    if "--json" in args:
        print(json.dumps(ranked, indent=2))
        return
    top = 30
    for a in args:
        if a.startswith("--top"):
            try:
                top = int(a.split("=")[1] if "=" in a else args[args.index(a) + 1])
            except (ValueError, IndexError):
                pass
    # summary counts
    from collections import Counter
    print(f"=== {len(ranked)} channels ranked ===")
    print(Counter(r["verdict"] for r in ranked))
    print()
    for r in ranked[:top]:
        print(f"{r['total']:3d} [{r['verdict']:12s}] #{r['id']} {r['name']}")
        print(f"       shelf={r['shelf']} readiness={r['readiness']} | "
              + " | ".join(r["reasons"][:3]))


if __name__ == "__main__":
    main()
