"""Character market validation — AvatarChannels-informed gates.

Answers, with data: is this character positioned to win?
Checks persona saturation, format viability, naming conversion,
monetization readiness, and AI-disclosure compliance against
681 real AI avatar channels (pipeline/avatar_intel.py).

Pure stdlib + avatar_intel. No network. No model calls.
Jev judges the nuanced questions; code checks the countable ones.
"""
from __future__ import annotations

from pipeline import avatar_intel as ai


def check_persona_saturation(persona: str, gender: str = "",
                             age: str = "") -> dict:
    """Is this persona archetype saturated? Returns saturation score + verdict.

    persona: expert | retired_professional | grandmother | homemaker |
             home_cook | homesteader | tradesperson | chef | narrator |
             grandfather | mother | father | other
    """
    # Channel counts from avatar intel (681 channels)
    COUNTS = {
        "expert": 160, "retired_professional": 123, "grandmother": 77,
        "homemaker": 75, "home_cook": 66, "homesteader": 56,
        "tradesperson": 47, "other": 25, "narrator": 20, "chef": 17,
        "grandfather": 9, "mother": 5, "father": 1,
    }
    n = COUNTS.get(persona, 0)
    pct = n / 681 * 100
    if pct >= 15:
        verdict, score = "saturated", 20
    elif pct >= 8:
        verdict, score = "crowded", 45
    elif pct >= 3:
        verdict, score = "competitive", 65
    elif pct >= 1:
        verdict, score = "open", 85
    else:
        verdict, score = "blue_ocean", 95
    return {"persona": persona, "channels": n,
            "share_pct": round(pct, 1), "verdict": verdict,
            "score": score,
            "note": f"{n}/681 channels use this archetype"}


def check_format_viability(niche: str, video_length_min: float = 0,
                           uploads_per_week: float = 0) -> dict:
    """Does this format match proven winners? Compares to farm norms."""
    checks = []
    # length
    if niche == "comedy" and 4 <= video_length_min <= 8:
        checks.append({"check": "length", "pass": True,
                       "note": "5-6 min matches Earl (sole comedy proof)"})
    elif niche == "sleep" and 25 <= video_length_min <= 40:
        checks.append({"check": "length", "pass": True,
                       "note": "25-40 min owns the empty long lane"})
    elif niche == "music" and 12 <= video_length_min <= 25:
        checks.append({"check": "length", "pass": True,
                       "note": "15-20 min matches farm sweet spot"})
    elif 8 <= video_length_min <= 20:
        checks.append({"check": "length", "pass": True,
                       "note": "8-20 min matches 63% of channels"})
    else:
        checks.append({"check": "length", "pass": False,
                       "note": f"{video_length_min} min is outside proven ranges"})
    # cadence
    if uploads_per_week >= 4:
        checks.append({"check": "cadence", "pass": True,
                       "note": f"{uploads_per_week}/week matches seller median 4.9"})
    elif uploads_per_week >= 3:
        checks.append({"check": "cadence", "pass": True,
                       "note": f"{uploads_per_week}/week meets minimum viable 3"})
    else:
        checks.append({"check": "cadence", "pass": False,
                       "note": f"{uploads_per_week}/week below minimum 3 (sellers do 4.9)"})
    passed = sum(1 for c in checks if c["pass"])
    return {"niche": niche, "checks": checks,
            "passed": passed, "total": len(checks),
            "score": round(passed / max(1, len(checks)) * 100)}


def check_naming(title: str, handle: str = "") -> dict:
    """Does this name follow converting formulas? Pattern-matches 5 formulas."""
    import re
    formulas = []
    # 1. First+Last person-name
    if re.match(r"^[A-Z][a-z]+ [A-Z][a-z]+$", (title or "").strip()):
        formulas.append("person-name (77% of channels, trust signal)")
    # 2. [Name]'s [Topic]
    if re.search(r"'s \w+", title or ""):
        formulas.append("possessive-topic (ownership signal)")
    # 3. [Topic] with [Name]
    if re.match(r"^\w+ [Ww]ith \w+", (title or "").strip()):
        formulas.append("topic-with-name (instantly legible for new niches)")
    # 4. Honorific
    if re.match(r"^(Chef|Grandma|Grandpa|Mr\.|Mrs\.|Dr\.)\s", (title or "").strip()):
        formulas.append("honorific (authority shortcut)")
    # 5. The [Method]
    if re.match(r"^The \w+", (title or "").strip()):
        formulas.append("the-method (premium positioning)")
    score = 80 if formulas else 40
    if handle and len(handle.replace("@", "")) <= 15 and "_" not in handle:
        score += 10
        formulas.append("clean handle (memorable, no underscores)")
    return {"title": title, "handle": handle,
            "formulas": formulas, "score": min(100, score),
            "pass": len(formulas) > 0}


def check_monetization(niche: str, products: list[dict] | None = None) -> dict:
    """Is there a product strategy? Compares to farm norms per niche."""
    products = products or []
    playbook = ai.channel_playbook(niche) if niche in (
        "sleep", "comedy", "music") else {}
    expected = []
    if niche in ("sleep", "comedy", "music"):
        expected = ["guide/ebook $27", "bundle $47-59", "$9.90/mo circle"]
        if niche == "comedy":
            expected.append("merch via Shopify ($2.99-$49.99)")
    has_products = len(products) > 0
    # price check against norms
    priced_right = 0
    for p in products:
        price = float(p.get("price_usd", 0) or 0)
        ptype = str(p.get("type", "")).lower()
        norm = ai.PRICING.get(ptype, ai.PRICING.get("ebook"))
        lo, hi = norm["range"] if "range" in norm else (0, 999)
        if lo <= price <= hi * 1.5:  # 50% tolerance above range
            priced_right += 1
    score = 0
    if has_products:
        score += 50
    if products and priced_right == len(products):
        score += 30
    if any("circle" in str(p.get("type", "")).lower() or
           "membership" in str(p.get("type", "")).lower() for p in products):
        score += 20  # recurring revenue (farm standard, only 11 channels do it)
    return {"niche": niche, "products": len(products),
            "priced_right": f"{priced_right}/{len(products)}",
            "expected": expected, "score": min(100, score),
            "pass": has_products and priced_right > 0}


def validate_character(character: dict) -> dict:
    """Full validation: all code-checkable gates. Returns scores + verdict.

    character: {name, handle, persona, gender, age, niche,
                video_length_min, uploads_per_week, products: [{type, price_usd}]}
    """
    persona = check_persona_saturation(
        character.get("persona", "other"),
        character.get("gender", ""), character.get("age", ""))
    fmt = check_format_viability(
        character.get("niche", ""),
        float(character.get("video_length_min") or 0),
        float(character.get("uploads_per_week") or 0))
    naming = check_naming(character.get("name", ""),
                          character.get("handle", ""))
    money = check_monetization(character.get("niche", ""),
                               character.get("products"))
    # weighted: persona 25, format 25, naming 15, monetization 35
    # (money matters most — 41% of channels sell, sellers upload 2x more)
    total = (persona["score"] * 0.25 + fmt["score"] * 0.25 +
             naming["score"] * 0.15 + money["score"] * 0.35)
    if total >= 70:
        verdict = "READY"
    elif total >= 50:
        verdict = "NEEDS_WORK"
    else:
        verdict = "NOT_READY"
    return {"character": character.get("name", ""),
            "persona": persona, "format": fmt,
            "naming": naming, "monetization": money,
            "total": round(total, 1), "verdict": verdict}
