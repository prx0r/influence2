"""Tests for market intel, archetypes, character validation, commerce.

Pure functions only — no network, no vault. Avatar export.json required
for archetype mining (4MB snapshot in data/avatarintel/).
"""
import json
import os

from pipeline import avatar_intel as ai
from pipeline import character_commerce as cc
from pipeline import character_market as cm

EXPORT = "/root/influence2/data/avatarintel/export.json"


def test_pricing_norms():
    assert ai.PRICING["ebook"]["median"] == 27.0
    assert ai.PRICING["bundle"]["median"] == 47.0
    assert ai.PRICING["membership"]["standard"] == 9.90


def test_channel_playbooks():
    for niche in ("sleep", "comedy", "music"):
        p = ai.channel_playbook(niche)
        assert p["competition"] in (0, 1)
        assert "format" in p and "product" in p
    assert ai.channel_playbook("unknown")["pricing"] == ai.PRICING


def test_persona_saturation_ordering():
    expert = cm.check_persona_saturation("expert")
    father = cm.check_persona_saturation("father")
    assert expert["score"] < father["score"]
    assert expert["verdict"] in ("saturated", "crowded")
    assert father["verdict"] in ("blue_ocean", "open")


def test_format_viability():
    ok = cm.check_format_viability("comedy", 6, 3)
    assert ok["passed"] == ok["total"]
    bad = cm.check_format_viability("comedy", 120, 0.5)
    assert bad["passed"] < bad["total"]


def test_naming_formulas():
    assert cm.check_naming("Aldo Bellini", "@aldobellini")["pass"] is True
    assert cm.check_naming("Bertha's Clean Home")["pass"] is True
    # single char name + junk handle = no formulas at all
    r = cm.check_naming("x", "@___junk___handle___123456789")
    assert r["pass"] is False


def test_monetization_scoring():
    none_m = cm.check_monetization("comedy", [])
    assert none_m["score"] == 0
    assert none_m["pass"] is False
    good = cm.check_monetization("comedy", [
        {"type": "ebook", "price_usd": 27},
        {"type": "membership", "price_usd": 9.9}])
    assert good["score"] >= 80
    assert good["pass"] is True


def test_validate_earl_beats_nolan():
    earl = {"name": "Earl and Ethel", "handle": "@earlandethel",
            "persona": "grandfather", "niche": "comedy",
            "video_length_min": 5.5, "uploads_per_week": 3,
            "products": [{"type": "merch", "price_usd": 12.99},
                         {"type": "ebook", "price_usd": 27}]}
    nolan = {"name": "No-Nose Nolan", "handle": "@nonosenolan",
             "persona": "grandfather", "niche": "comedy",
             "video_length_min": 6, "uploads_per_week": 3,
             "products": []}
    re_earl = cm.validate_character(earl)
    re_nolan = cm.validate_character(nolan)
    assert re_earl["total"] > re_nolan["total"]
    assert re_earl["verdict"] == "READY"
    assert re_nolan["verdict"] in ("NEEDS_WORK", "NOT_READY")


def test_archetype_match_boost():
    arch = cm.match_archetype("homemaker", 15, 4)
    # homemaker cleaning is validated (or falls back to fresh mine)
    assert "prior_boost" in arch
    assert -10 <= arch["prior_boost"] <= 15
    # unknown combo → no boost, flagged
    no = cm.match_archetype("father", 90, 0.5)
    assert no["matched"] is False
    assert no["prior_boost"] == 0


def test_commerce_asset_mapping():
    # nude functions: propose known SKUs with Earl-norm pricing
    assert "poster_a4" in str(cc.ASSET_PRODUCTS)
    assert "tee_basic" in str(cc.ASSET_PRODUCTS)
    # stores list degrades gracefully (no crash if dirs missing)
    stores = cc.oddhobb_stores()
    assert isinstance(stores, list)


def test_commerce_propose_no_dupes():
    # propose_products should never return duplicate prodigi_skus
    props = cc.propose_products("nonexistent_character_xyz", "Test")
    skus = [p.get("prodigi_sku", "") for p in props.get("products", [])]
    assert len(skus) == len(set(skus))


def test_archetype_mining_smoke():
    if not os.path.exists(EXPORT):
        return  # export snapshot required
    from pipeline import archetypes as arch
    mined = arch.mine_archetypes(min_n=8)
    assert len(mined) > 0
    top = mined[0]
    assert top["sell_rate"] >= 0.5
    assert top["n"] >= 8
    # lift: daily posters should outrank rare posters
    lift = arch.seller_vs_nonseller()
    cl = lift.get("cadence", {}).get("lift", {})
    if "daily7+" in cl and "rare<1" in cl:
        assert cl["daily7+"] > cl["rare<1"]


def test_gap_archetypes_empty_niches():
    if not os.path.exists(EXPORT):
        return
    from pipeline import archetypes as arch
    gaps = {g["niche"]: g for g in arch.gap_archetypes()}
    # truly zero: no tags at all
    for niche in ("music", "roast", "piano", "parody"):
        assert gaps[niche]["verdict"] == "empty", f"{niche} should be empty"
    # incidental mentions only (false positives, not dedicated channels)
    assert gaps["sleep"]["tag_hits"] <= 5
    assert gaps["comedy"]["tag_hits"] <= 5
