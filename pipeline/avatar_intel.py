"""Avatar market intelligence — structured for workflow consumption.

Source: avatarchannels.com/api/v1/export.json (681 channels, refreshed 2026-10-12).
Full analysis in session research. This module exposes the actionable cuts:
pricing norms, format norms, persona gaps, naming formulas, funnel patterns.

Used by: content_decide (channel positioning), release_gate (format checks),
character_direct (persona + product strategy).
"""
from __future__ import annotations

# Pricing norms (USD, from 469 offers across 281 sellers)
PRICING = {
    "ebook": {"median": 27.0, "range": [19.99, 37.0], "min": 7.99, "max": 47.0},
    "guide": {"median": 27.0, "range": [19.99, 37.0], "min": 7.0, "max": 67.0},
    "cookbook": {"median": 29.0, "range": [19.99, 39.0], "min": 9.99, "max": 44.0},
    "bundle": {"median": 47.0, "range": [37.0, 59.99], "min": 24.99, "max": 309.0},
    "membership": {"median": 9.90, "standard": 9.90, "note": "Circle is the farm standard"},
    "lead_magnet": {"median": 0.0, "note": "free chapter / 7-day challenge"},
}

# Format norms (farm playbook)
FORMATS = {
    "uploads_per_week": {"sellers_median": 4.9, "nonsellers_median": 3.0,
                         "playbook": "3-7/week", "minimum_viable": 3},
    "video_length_min": {"median": 17.8, "sellers_median": 19.1,
                         "sweet_spot": "15-20", "sleep_gap": "25-40 (only 233/681)",
                         "comedy_proof": "5-6 (Earl only)"},
    "structure": "numbered list/countdown, one-topic-per-video, mistake-correction hook",
}

# Persona gaps (emptiest cells = opportunity)
PERSONA_GAPS = {
    "mother": {"count": 5, "note": "only 2 sell"},
    "grandfather": {"count": 9, "note": "only 3 sell, owns the sole comedy channel"},
    "young_adult": {"count": 9, "note": "zero comedy"},
    "father": {"count": 1, "note": "single Spanish channel"},
    "cartoon_3d": {"count": 2, "note": "animation lane empty"},
}

# Underserved topics (zero dedicated channels)
TOPIC_GAPS = ["sleep", "relaxation", "ambient", "meditation", "music",
              "piano", "classical", "jazz", "theory", "comedy", "roast",
              "parody", "characters", "deconstruction"]

# Underserved languages (channels / sellers)
LANGUAGE_GAPS = {
    "portuguese": "BR 17 channels but pt 1 lang (mismatch = opportunity)",
    "german": "DE 1 country, de 2 lang",
    "french": "FR 2, no fr lang listed",
    "hindi": "<=2 channels, <=1 seller",
    "tagalog": "<=2 channels",
    "vietnamese": "<=2 channels",
    "arabic": "<=2 channels",
}

# Naming formulas (with examples)
NAMING = [
    {"formula": "First+Last person-name", "share": "77%",
     "example": "Aldo Bellini (@aldobellinii)", "use": "trust: expert/retired_prof"},
    {"formula": "[Name]'s [Topic]", "share": "58 channels",
     "example": "Bertha's Clean Home", "use": "grandmother/homemaker ownership"},
    {"formula": "[Topic] with [Name]", "share": "26 channels",
     "example": "Cats With Cathy", "use": "pets/faith/new topics, instantly legible"},
    {"formula": "[Honorific+Name]", "share": "20 channels",
     "example": "Chef Albert Finch", "use": "authority shortcut"},
    {"formula": "The [Method] brand", "share": "16 channels",
     "example": "The Japanese Method", "use": "premium/foreign-method, bundles $47-59"},
]

# Funnel patterns (329/681 mapped)
FUNNELS = {
    "canonical": "video → description → landing → checkout (142 channels)",
    "with_upsell": "video → description → landing → checkout → upsell (25)",
    "with_email": "video → description → landing → email → checkout (19, rare — do it)",
    "about_link": "video → landing → checkout (23, about-link only)",
    "cta_density": "sellers average 3.68 links/channel vs 1.55 non-sellers",
    "first_line": "sellers put store link in description first line (~60% of videos)",
}

# Platforms (offers / channels)
PLATFORMS = {
    "gumroad": {"offers": 218, "channels": 129, "use": "ebooks/guides default"},
    "custom": {"offers": 106, "channels": 80, "use": "own checkout"},
    "stripe_custom": {"offers": 55, "channels": 35, "use": "own site"},
    "payhip": {"offers": 28, "channels": 18, "use": "alternative to gumroad"},
    "shopify": {"offers": 18, "channels": 6, "use": "merch (Earl owns this)"},
}

# The sole comedy proof (copy what works)
EARL_PROOF = {
    "channel": "Earl and Ethel (@earlandethel)",
    "format": "5-6 min scripted, 3/week, trivia tentpole + rants + Q&A",
    "avatar": "3D animated old couple (only 3D avatar in 681)",
    "products": "Shopify 10 SKUs: $2.99 song, $11.99-12.99 merch, $49.99 plush",
    "funnel": "28/30 descriptions link store (93% CTA density)",
    "compliance": "only channel disclosing AI assets every upload",
    "engagement": "7-15% likes, 81-154 comments on trivia",
}


def channel_playbook(niche: str) -> dict:
    """Positioning playbook per niche. niche: sleep | comedy | music."""
    base = {"pricing": PRICING, "platforms": PLATFORMS, "funnels": FUNNELS}
    if niche == "sleep":
        return {**base,
                "persona": "grandmother/female/senior, soft realistic still",
                "naming": "[Name]'s Bedtime Stories or Sleep With [Name]",
                "format": "25-40 min (empty lane), 3-5/week, one tale + wind-down",
                "avatar": "warm lamp-lit bedroom, half-closed eyes, no yellow-arrow thumb",
                "product": "ebook/guide $27 + bundle $47-59 + $9.90/mo Circle + $2.99 audio loop",
                "competition": 0, "adjacent": "calm-wisdom (7-15/week, zero monetization)"}
    if niche == "comedy":
        return {**base,
                "persona": "grandfather/male/senior OR young_adult (both nearly empty)",
                "naming": "[Name] & [Name] or [Name]'s Porch",
                "format": "5-6 min scripted (Earl's lane), 3/week, weekly tentpole + twist + comment ask",
                "avatar": "3D/cartoon (not realistic), full-body porch set",
                "product": "Shopify merch ($2.99-$49.99) + $27 rant ebook",
                "competition": 1, "adjacent": "storytelling (20 channels, not comedy)"}
    if niche == "music":
        return {**base,
                "persona": "retired piano tuner / ex-bandleader as expert (sells 45% with guides)",
                "naming": "Deconstruct With [Name] or [Name] Breaks The Song",
                "format": "15-20 min (farm sweet spot), one song per video, hook + 5-7 parts",
                "avatar": "realistic at piano / record shelf, still image fine",
                "product": "guide $27 + bundle $47 + $9.90 Circle for stems/sheets",
                "competition": 0, "adjacent": "none (classifier has never seen music)"}
    return base
