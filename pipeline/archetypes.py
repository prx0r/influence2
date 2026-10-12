"""Archetype mining — what patterns actually work across 681 avatar channels.

Mines export.json for reusable archetypes: persona × format × monetization
combos with evidence. Code finds correlations, Jev validates which are
real vs coincidence, archetypes become priors for character_validate
and avatar_onboard.

An archetype is a named, reusable pattern:
  {name, persona, format, monetization, evidence: {n, sell_rate, examples}}

Pure stdlib. Reads data/avatarintel/export.json (refreshed daily).
"""
from __future__ import annotations

import json
import os
from collections import Counter, defaultdict

EXPORT_PATH = "/root/influence2/data/avatarintel/export.json"


def load_channels() -> list[dict]:
    with open(EXPORT_PATH) as f:
        d = json.load(f)
    return d.get("data", [])


def _persona_key(c: dict) -> str:
    p = (c.get("analysis") or {}).get("persona") or {}
    arch = p.get("archetype") or "unknown"
    gender = p.get("gender") or "?"
    age = p.get("age_band") or "?"
    return f"{arch}/{gender}/{age}"


def _sells(c: dict) -> bool:
    return (c.get("offer_summary") or {}).get("sells") == "yes"


def _length_bucket(c: dict) -> str:
    sched = c.get("schedule") or {}
    secs = sched.get("median_length_seconds") or 0
    mins = secs / 60
    if mins < 8:
        return "short<8"
    if mins < 20:
        return "mid8-20"
    if mins < 40:
        return "long20-40"
    return "epic40+"


def _cadence_bucket(c: dict) -> str:
    sched = c.get("schedule") or {}
    upw = sched.get("uploads_per_week") or 0
    if upw < 1:
        return "rare<1"
    if upw < 3:
        return "steady1-3"
    if upw < 7:
        return "active3-7"
    return "daily7+"


def mine_archetypes(min_n: int = 5) -> list[dict]:
    """Group by persona × length × cadence → sell rate. Returns ranked archetypes."""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for c in load_channels():
        key = (_persona_key(c), _length_bucket(c), _cadence_bucket(c))
        groups[key].append(c)
    archetypes = []
    for (persona, length, cadence), members in groups.items():
        if len(members) < min_n:
            continue
        sellers = sum(1 for m in members if _sells(m))
        rate = sellers / len(members)
        # common niche tags in this group
        tags = Counter()
        for m in members:
            for t in ((m.get("analysis") or {}).get("niche_tags") or []):
                tags[t] += 1
        # common offer types + median price among sellers
        otypes = Counter()
        prices: list[float] = []
        for m in members:
            if _sells(m):
                for o in (m.get("offers") or []):
                    if not isinstance(o, dict):
                        continue
                    if o.get("offer_type"):
                        otypes[o["offer_type"]] += 1
                    cents = (o.get("price") or {}).get("amount_cents") or 0
                    if cents > 0:
                        prices.append(cents / 100)
        prices.sort()
        median_price = prices[len(prices) // 2] if prices else None
        archetypes.append({
            "persona": persona, "length": length, "cadence": cadence,
            "n": len(members), "sellers": sellers,
            "sell_rate": round(rate, 3),
            "median_price_usd": median_price,
            "top_tags": [t for t, _ in tags.most_common(5)],
            "top_offers": [t for t, _ in otypes.most_common(3)],
            "examples": [m.get("handle", "?") for m in members[:3]],
        })
    archetypes.sort(key=lambda a: (a["sell_rate"], a["n"]), reverse=True)
    return archetypes


def seller_vs_nonseller() -> dict:
    """What distinguishes sellers from non-sellers? Feature-by-feature."""
    channels = load_channels()
    sellers = [c for c in channels if _sells(c)]
    nons = [c for c in channels
            if (c.get("offer_summary") or {}).get("sells") == "unknown"]
    def dist(cs, fn):
        return Counter(fn(c) for c in cs)
    out = {"sellers": len(sellers), "nonsellers": len(nons)}
    for label, fn in [("length", _length_bucket),
                      ("cadence", _cadence_bucket),
                      ("persona", _persona_key)]:
        sd, nd = dist(sellers, fn), dist(nons, fn)
        # lift: seller share / nonseller share per value
        lift = {}
        for val in set(list(sd) + list(nd)):
            s = sd.get(val, 0) / max(1, len(sellers))
            n = nd.get(val, 0) / max(1, len(nons))
            if n > 0:
                lift[val] = round(s / n, 2)
        out[label] = {"sellers": dict(sd.most_common(8)),
                      "nonsellers": dict(nd.most_common(8)),
                      "lift": dict(sorted(lift.items(),
                                          key=lambda kv: kv[1], reverse=True)[:8])}
    return out


def gap_archetypes() -> list[dict]:
    """Persona × topic cells with zero channels. Opportunity map."""
    # topics from niche_tags (proxy — export has no single topic field per channel)
    all_tags = Counter()
    for c in load_channels():
        for t in ((c.get("analysis") or {}).get("niche_tags") or []):
            all_tags[t.lower()] += 1
    # check specific opportunity niches
    targets = ["sleep", "bedtime", "insomnia", "meditation", "ambient",
               "asmr", "relax", "calm", "music", "piano", "jazz",
               "classical", "comedy", "roast", "parody", "character"]
    gaps = []
    for t in targets:
        hits = sum(1 for tag, n in all_tags.items() if t in tag)
        gaps.append({"niche": t, "tag_hits": hits,
                     "verdict": "empty" if hits == 0 else f"{hits} tag mentions"})
    return gaps
