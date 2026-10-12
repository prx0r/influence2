"""Sleep channel monetizability ranker — score easy + sleepintel against our formulas.

Uses: 7 farm patterns (pattern_check), archetype priors (character_market),
pricing norms (avatar_intel), plus sleep-specific signals (script readiness,
voice assigned, source tiers, word-gate pass).

Run: python3 scripts/rank_sleep_channels.py [--json]
"""
from __future__ import annotations

import glob
import json
import os
import sys

sys.path.insert(0, "/root/influence2")
from pipeline import pattern_check as pc

EASY_DIR = "/root/easy"


def load_easy_playlists() -> list[dict]:
    """Load all easy playlists with channel.yaml + video meta."""
    out = []
    for ch_yaml in sorted(glob.glob(f"{EASY_DIR}/*/channel.yaml")):
        slug = os.path.basename(os.path.dirname(ch_yaml))
        try:
            import yaml
        except ImportError:
            yaml = None
        ch: dict = {"slug": slug}
        if yaml:
            try:
                with open(ch_yaml) as f:
                    ch.update(yaml.safe_load(f) or {})
            except Exception:
                pass
        else:
            # minimal parse without pyyaml
            with open(ch_yaml) as f:
                for line in f:
                    if ":" in line and not line.strip().startswith("#"):
                        k, v = line.split(":", 1)
                        ch[k.strip()] = v.strip().strip('"')
        # count videos + scripted
        vdir = os.path.dirname(ch_yaml)
        videos = [d for d in glob.glob(f"{vdir}/*/meta.json")]
        scripted = 0
        total_words = 0
        for m in videos:
            try:
                with open(m) as f:
                    meta = json.load(f)
                words = int(meta.get("words") or 0)
                if words > 0:
                    scripted += 1
                    total_words += words
            except (json.JSONDecodeError, OSError, ValueError):
                pass
        ch["videos"] = len(videos)
        ch["scripted"] = scripted
        ch["total_words"] = total_words
        ch["hours_ready"] = round(total_words / (115 * 60), 1)
        out.append(ch)
    return out


def score_playlist(pl: dict) -> dict:
    """Score one playlist on monetizability (0-100)."""
    scores: dict = {}
    reasons: list[str] = []
    # 1. Content readiness (30 pts): scripted videos + hours
    scripted = pl.get("scripted", 0)
    hours = pl.get("hours_ready", 0)
    if scripted >= 5 and hours >= 5:
        scores["readiness"] = 30
        reasons.append(f"{scripted} scripted, {hours}h ready")
    elif scripted >= 3:
        scores["readiness"] = 20
        reasons.append(f"{scripted} scripted (partial)")
    elif scripted >= 1:
        scores["readiness"] = 10
        reasons.append("1+ scripted (early)")
    else:
        scores["readiness"] = 0
        reasons.append("no scripts yet")
    # 2. Voice assigned (15 pts): voiced beats silent for monetization
    # (silent = no TTS product, harder to differentiate)
    voice = str(pl.get("voice", "none"))
    if voice and voice.lower() != "none":
        scores["voice"] = 15
        reasons.append(f"voice {voice} assigned")
    else:
        scores["voice"] = 5
        reasons.append("silent (no voice product)")
    # 3. Niche gap (20 pts): sleep/relaxation = empty in 681 channels
    pitch = str(pl.get("pitch", "")).lower()
    name = str(pl.get("name", "")).lower()
    text = f"{pitch} {name}"
    # funny-boring readable content scores highest (proven farm-adjacent)
    if any(k in text for k in ["law", "statute", "manual", "menu",
                               "timetable", "patent", "spec", "policy",
                               "rulebook", "catalogue", "list"]):
        scores["niche"] = 20
        reasons.append("funny-boring readable (farm-adjacent, zero avatar comps)")
    elif any(k in text for k in ["fairy", "fable", "myth", "story",
                                  "tale", "folklore"]):
        scores["niche"] = 18
        reasons.append("story sleep (proven STORY shelf, no avatar comps)")
    elif any(k in text for k in ["sleep", "bedtime", "night", "calm",
                                  "silence", "permission", "contemplat"]):
        scores["niche"] = 15
        reasons.append("direct sleep (empty lane, needs format proof)")
    else:
        scores["niche"] = 10
        reasons.append("niche unclear")
    # 4. Product fit (20 pts): can this become $27 guide + $47 bundle?
    # Readable content → guide-able. Stories → collectible. Silent → hard.
    shelf = str(pl.get("shelf", ""))
    engine = str(pl.get("engine", ""))
    if engine in ("E5c", "E2") or shelf in ("STORY", "MIND"):
        scores["product"] = 20
        reasons.append("guide-able content ($27 digital + $47 bundle)")
    elif shelf == "PLACE" or engine == "silent":
        scores["product"] = 8
        reasons.append("ambient only (hard to productize beyond audio loop)")
    else:
        scores["product"] = 12
        reasons.append("product path unclear")
    # 5. Scale (15 pts): video count = series potential
    count = int(pl.get("count", 0) or 0)
    videos = pl.get("videos", 0)
    n = max(count, videos)
    if n >= 20:
        scores["scale"] = 15
        reasons.append(f"{n} videos (series depth)")
    elif n >= 10:
        scores["scale"] = 12
        reasons.append(f"{n} videos (solid series)")
    elif n >= 5:
        scores["scale"] = 8
        reasons.append(f"{n} videos (starter)")
    else:
        scores["scale"] = 4
        reasons.append(f"{n} videos (thin)")
    total = sum(scores.values())
    if total >= 75:
        verdict = "LAUNCH_READY"
    elif total >= 55:
        verdict = "PROMISING"
    elif total >= 35:
        verdict = "NEEDS_WORK"
    else:
        verdict = "EARLY"
    return {"slug": pl.get("slug", ""), "name": pl.get("name", ""),
            "scores": scores, "total": total, "verdict": verdict,
            "reasons": reasons, "voice": voice,
            "videos": videos, "scripted": scripted,
            "hours": hours}


def rank_all() -> list[dict]:
    pls = load_easy_playlists()
    ranked = [score_playlist(p) for p in pls]
    ranked.sort(key=lambda r: r["total"], reverse=True)
    return ranked


if __name__ == "__main__":
    ranked = rank_all()
    if "--json" in sys.argv:
        print(json.dumps(ranked, indent=2))
    else:
        for r in ranked:
            print(f"{r['total']:3d} [{r['verdict']:12s}] {r['name']} "
                  f"({r['videos']}v/{r['scripted']}s/{r['hours']}h, {r['voice']})")
            for reason in r["reasons"]:
                print(f"       - {reason}")
