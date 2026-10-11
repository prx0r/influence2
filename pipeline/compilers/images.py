"""Etsy 5+1 image formulas — the machine-readable contract.

Source of truth for SHAPE: oddhobbies/etsy-pack/IMAGES.md + prompts/*.md.
Source of truth for FACTS: the pack (title/price/specs) + specs compiler.
This module merges them. Pure functions only — no network, no spend.

Slots are JOBS, not rigid templates (etsy-pack/AGENTS.md):
HOOK → PROOF → CONTEXT → JOURNEY → RANGE (+ CTA off-Etsy).
Each product instantiates differently; see examples/croc-jibbit.md,
examples/wrap-personal.md. Brackets are filled from the pack; anything
missing is a gap, never a guess.
"""
from __future__ import annotations

import os

ETSY_PACK_DIR = "/root/oddhobbies/etsy-pack"

# ── formulas ──────────────────────────────────────────────────────────
# etsy: True → upload to Etsy ranks 1-5. False → off-Etsy only (POLICY.md).
FORMULAS: dict[int, dict] = {
    1: {
        "role": "hero", "job": "HOOK", "etsy": True,
        "function": "Stop the scroll. Person + product, emotion, seasonal context.",
        "inputs": ["assets_now[0] (reference render/photo)", "occasion (seasonal bokeh)",
                   "scale_prompt (true size, slots 1-3)"],
        "prompt_file": "prompts/1-hero.md",
        "prompt_logic": ("reference attached + target person holding product in their "
                         "environment with profile-matched surroundings + inherited true-size scale. "
                         "NO text."),
        "size": (2000, 2000), "text": "NONE",
        "capability": "identity_transform", "provider": "cloudflare",
        "qc": ["face sharp", "product sharp", "no text", "no clutter", "140px legible"],
        "r2": "commerce/stores/{store}/assets/etsy/{sku}/1-hero.jpg",
    },
    2: {
        "role": "proof", "job": "PROOF", "etsy": True,
        "function": "Prove personalization works. Highest-trust image. Answers 'will it look like me/mine?'",
        "inputs": ["reference photo (left) + finished render (right)", "same scale/angle/light"],
        "prompt_file": "prompts/2-proof.md",
        "prompt_logic": ("seamless split white bg, left reference waist-up, right product "
                         "same framing. No arrows/circles/text/borders. Honest likeness."),
        "size": (2000, 2000), "text": "NONE",
        "capability": "identity_transform", "provider": "cloudflare",
        "qc": ["both sides sharp", "same light temperature", "no text", "honest likeness"],
        "r2": "commerce/stores/{store}/assets/etsy/{sku}/2-proof.jpg",
    },
    3: {
        "role": "scale", "job": "CONTEXT", "etsy": True,
        "function": "Kill size anxiety. Universal ruler (fingers/coin). Macro shows quality.",
        "inputs": ["product render macro or sample photo", "scale_prompt (coin/fingertip ref)"],
        "prompt_file": "prompts/3-scale.md",
        "prompt_logic": ("in-situ: product where its owner keeps it, profile-matched "
                         "surroundings, true-size reference at true relative size, macro on "
                         "key detail (never a coin, never text). NO text."),
        "size": (2000, 2000), "text": "NONE",
        "capability": "product_packshot", "provider": "cloudflare",
        "qc": ["product tack-sharp", "true proportions", "no text"],
        "r2": "commerce/stores/{store}/assets/etsy/{sku}/3-scale.jpg",
    },
    4: {
        "role": "howto", "job": "JOURNEY", "etsy": True,
        "function": "Answer everything in-image. 3 steps + spec strip. Kills 'how long / what size?' messages.",
        "inputs": ["product render (art half)", "spec_block (size/material/weight byte-for-byte)",
                   "3 step titles+subs (≤5 words each)"],
        "prompt_file": "prompts/4-howto.md",
        "prompt_logic": ("COMPOSED not generated: art left 45% (product_packshot, NO text) + "
                         "text right 55% (PIL composer, exact pack bytes). Icons photo/gear/truck. "
                         "One font, high contrast, seasonal frame matching rank 1."),
        "size": (2000, 2000), "text": "YES — steps + spec strip, spell-check twice",
        "capability": "product_packshot", "provider": "cloudflare",
        "qc": ["legible at 570px", "zero typos", "numbers == pack truth", "icons render"],
        "r2": "commerce/stores/{store}/assets/etsy/{sku}/4-howto.jpg",
    },
    5: {
        "role": "options", "job": "RANGE", "etsy": True,
        "function": "Show range + process + upsell. Self-projection ('mine could be the chef one'). Lifts AOV.",
        "inputs": ["variant list (4-6, consistent style)", "upsell price (specific number)",
                   "process strip 3-4 panels"],
        "prompt_file": "prompts/5-options.md",
        "prompt_logic": ("COMPOSED: header benefit+subline + process mini-panels with arrows + "
                         "variant grid labelled + one upsell callout + hero variant closer. "
                         "Seasonal frame matching 1+4."),
        "size": (2000, 2000), "text": "YES — labels, prices, steps, spell-check twice",
        "capability": "product_packshot", "provider": "cloudflare",
        "qc": ["labels legible", "prices == pack", "steps accurate", "zero typos"],
        "r2": "commerce/stores/{store}/assets/etsy/{sku}/5-options.jpg",
    },
    6: {
        "role": "cta", "job": "CTA", "etsy": False,
        "function": "Off-Etsy brand card. Pinterest/social/ads ONLY — NEVER upload to Etsy (POLICY.md: URLs/handles banned in listings).",
        "inputs": ["product hero render", "seasonal accents"],
        "prompt_file": "prompts/6-cta.md",
        "prompt_logic": ("cream #F7F3EE card, product centre, 'Customise yours on oddhobb.com' + "
                         "'First preview free'. Optional QR for Pinterest/print only."),
        "size": (2000, 2000), "text": "YES — URL + subline (off-Etsy only)",
        "capability": "product_packshot", "provider": "cloudflare",
        "qc": ["URL spelled correctly", "brand colours", "no Etsy context"],
        "r2": "commerce/stores/{store}/assets/etsy/{sku}/6-cta.jpg",
    },
}

SERIES_RULES = [
    "Same figure/outfit/colours across all 5",
    "Same background family (white base + seasonal accents)",
    "Ranks 4-5 share frame language with rank 1",
    "Text ONLY in ranks 4-5 (6 for off-Etsy). Ranks 1-3 pure image",
    "Rank 1 sets tone; ranks 2-5 deliver proof",
]


def _read_prompt(rel: str) -> str:
    try:
        with open(os.path.join(ETSY_PACK_DIR, rel)) as f:
            return f.read()
    except OSError:
        return ""


def _read_prompt(rel: str) -> str:
    try:
        with open(os.path.join(ETSY_PACK_DIR, rel)) as f:
            return f.read()
    except OSError:
        return ""


# ── variable resolution ───────────────────────────────────────────
# Catalog audience/geometry/manufacture preferred, oddhobbies listing
# fields fallback, generic default last. Every variable records its
# source; unresolvable → gap, never a guess.

# family → (environment, surrounding props). Environment = where the
# target person would actually keep/see this in their home.
ENV_MAP = {
    "mini-figure": ("warm living-room shelf, wooden shelf with books",
                    "books, small plant, framed photo"),
    "figure-with-pet": ("cosy living-room side table near a sofa",
                        "mug, folded throw, framed pet photo"),
    "croc-charm": ("bright entryway, clog on a shoe rack in daylight",
                   "shoe rack, sneakers, doormat"),
    "keychain": ("hallway hook beside a front door, keys hanging",
                 "keys, canvas tote, sunglasses"),
    "keycap": ("desk setup beside a mechanical keyboard",
               "keyboard, mug, notebook"),
    "ornament": ("Christmas tree branch in a warm living room",
                 "tree lights, ribbon, wrapped gifts below"),
    "card-rack": ("board-game table mid-game-night",
                  "cards, mugs, score pad"),
    "mahjong-reader": ("mahjong table beside a set tile wall",
                       "tiles, tea cup, score sticks"),
    "cribbage-pegs": ("cribbage board on a pub-style wooden table",
                      "board, pint glass, cards"),
    "dart-stand": ("wall beside a bristle dartboard in a games room",
                   "dartboard, darts, chalk scoreboard"),
    "golf-marker": ("golf bag pocket / clubhouse table",
                    "clubs, glove, scorecard"),
    "flat-print": ("wrapping station on a living-room floor",
                   "kraft paper, scissors, ribbon, gift tags"),
    "album": ("coffee table in a warm living room",
              "coffee cup, headphones, small vase"),
    "gift": ("warm living-room shelf, wooden shelf with books",
             "books, small plant, framed photo"),
}

# oddhobbies section keyword → family fallback (packs without catalog entry)
SECTION_FAMILY = [
    ("game", "card-rack"),
    ("stocking", "ornament"),
    ("christmas", "ornament"),
    ("wedding", "mini-figure"),
    ("couples", "mini-figure"),
    ("pet", "figure-with-pet"),
    ("card", "flat-print"),
    ("album", "album"),
]

# family → money detail (the close-up that proves quality)
DETAIL_MAP = {
    "mini-figure": "printed face, shirt texture, joint lines",
    "figure-with-pet": "both faces, fur texture, base rim text",
    "croc-charm": "face print at macro, pin stem on the back",
    "keychain": "face print, split-ring join, edge finish",
    "keycap": "legend print, stem fit, top texture",
    "ornament": "face print, ribbon loop, layer lines",
    "card-rack": "engraved name, magnet seat, tile fit",
    "mahjong-reader": "engraved name, edge finish, tile window",
    "cribbage-pegs": "engraved name/year, tip finish",
    "dart-stand": "engraved name, slot fit, surface finish",
    "golf-marker": "engraved motif, edge finish, weight feel",
    "flat-print": "print sharpness, paper sheen, cut edge",
    "album": "cover art, disc print, liner text",
    "gift": "face/detail finish, edge quality",
}


def _catalog_pack(sku: str) -> dict:
    try:
        import sys as _sys
        _sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        try:
            from catalog import load as _load
        except ImportError:
            from pipeline.catalog import load as _load
        return _load(sku)
    except Exception:
        return {}


def _family_of(pack: dict, cat: dict) -> tuple[str, str]:
    if cat.get("family"):
        return cat["family"], "catalog:family"
    section = " ".join(str(pack.get(k, "")) for k in
                       ("section", "shop_section_target", "design_class")).lower()
    for kw, fam in SECTION_FAMILY:
        if kw in section:
            return fam, f"listing:section→{kw}"
    return "gift", "default"


def resolve_vars(pack: dict, scale_prompt: str = "") -> dict:
    """Pack → named variables for the master prompts.

    Returns {"vars", "gaps", "sources"}. Pure. Missing → gap, never guess.
    """
    gaps: list[str] = []
    sources: dict[str, str] = {}
    sku = pack.get("sku", "?")
    cat = _catalog_pack(sku)
    aud = cat.get("audience") or {}
    geo = cat.get("geometry") or {}
    mfr = cat.get("manufacture") or {}
    listing = cat.get("listing") or {}

    product = (cat.get("name") or pack.get("etsy_title") or pack.get("sku", "")).strip()
    sources["PRODUCT"] = "catalog:name" if cat.get("name") else "listing:etsy_title"

    suits = aud.get("suits") or []
    if suits:
        person, psrc = suits[0], "catalog:audience.suits[0]"
    else:
        person = "gift buyer shopping for a personal present"
        psrc = "default"
        gaps.append(f"{sku}: no audience.suits — PERSON is generic (repair catalog pack)")
    sources["PERSON"] = psrc

    family, famsrc = _family_of(pack, cat)
    sources["FAMILY"] = famsrc
    env, props = ENV_MAP.get(family, ENV_MAP["gift"])
    sources["ENV"] = f"env_map:{family}"
    sources["PROPS"] = f"env_map:{family}"

    occasions = aud.get("occasions") or []
    if any("christmas" in str(o).lower() for o in occasions):
        seasonal = "Christmas tree bokeh edge, warm fairy lights"
        ssrc = "catalog:audience.occasions"
    elif " ".join(str(pack.get(k, "")) for k in ("section", "shop_section_target")).lower().find("christmas") >= 0:
        seasonal = "Christmas tree bokeh edge, warm fairy lights"
        ssrc = "listing:section"
    elif occasions:
        seasonal = f"{occasions[0]} accents, warm and understated"
        ssrc = "catalog:audience.occasions[0]"
    else:
        seasonal = "soft warm accents, no seasonal props"
        ssrc = "default"
    sources["SEASONAL"] = ssrc

    material = (mfr.get("material") or pack.get("material") or "").strip()
    if not material:
        gaps.append(f"{sku}: no material — slots 4-5 need pack truth")
    sources["MATERIAL"] = "catalog:manufacture.material" if mfr.get("material") else (
        "listing:material" if pack.get("material") else "missing")

    dims = geo.get("dims_mm") or []
    size = " × ".join(str(d) for d in dims) + " mm" if dims else ""
    if not size:
        gaps.append(f"{sku}: no dims_mm — scale renders need measurement")
    sources["SIZE"] = "catalog:geometry.dims_mm" if dims else "missing"

    if not scale_prompt:
        gaps.append(f"{sku}: no scale_prompt — run specs compiler first")
    sources["SCALE"] = "specs:scale_prompt" if scale_prompt else "missing"

    detail = DETAIL_MAP.get(family, DETAIL_MAP["gift"])
    sources["DETAIL"] = f"detail_map:{family}"

    ref = (pack.get("assets_now") or [""])[0]
    ref = ref if isinstance(ref, str) else ref.get("path_or_url", "")
    sources["REF"] = "listing:assets_now[0]" if ref else "missing"
    if not ref:
        gaps.append(f"{sku}: no reference image in assets_now — generation needs a ref")

    tone = ", ".join(aud.get("tone") or []) or "warm gift-brand"
    sources["TONE"] = "catalog:audience.tone" if aud.get("tone") else "default"

    return {
        "vars": {"PRODUCT": product[:120], "PERSON": person, "ENV": env,
                 "PROPS": props, "SEASONAL": seasonal, "MATERIAL": material or "?",
                 "SIZE": size or "?", "SCALE": scale_prompt, "DETAIL": detail,
                 "REF": ref, "TONE": tone, "FAMILY": family},
        "gaps": gaps, "sources": sources,
    }


def build_prompt(slot: int, pack: dict, scale_prompt: str = "") -> dict:
    """Formula + pack → render prompt. Returns {prompt, gaps, formula, vars}.

    One master prompt per slot: reference attached + product in the target
    person's environment + inherited true-size scale. Same logic every
    product; variables change per product. Pure — gaps, never guesses.
    """
    f = FORMULAS.get(slot)
    if not f:
        return {"prompt": "", "gaps": [f"unknown slot {slot}"], "formula": {}}
    r = resolve_vars(pack, scale_prompt)
    v = r["vars"]
    gaps = list(r["gaps"])
    if slot in (4, 5) and v["MATERIAL"] == "?":
        pass  # already gapped above
    if slot == 5 and not pack.get("variants") and not pack.get("addons"):
        gaps.append("slot 5: no variants/addons in pack — upsell needs a specific number")

    bodies = {
        1: (f"Warm lifestyle product photo, square crop. ATTACHED REFERENCE: {v['REF']} — "
            f"keep this exact product look, never reinvent it.\n"
            f"Subject: {v['PERSON']}, holding {v['PRODUCT']} at chest height, "
            f"pointing at it with the free hand, direct eye contact, genuine smile.\n"
            f"Setting: {v['ENV']}, surrounded by {v['PROPS']}. "
            f"Background keeps a clean cream base with {v['SEASONAL']}.\n"
            f"Scale truth: {v['SCALE'] or 'see pack dims'}. True relative size, no distortion.\n"
            f"Light: soft key, warm fill, gentle shadows. Face + product tack-sharp, "
            f"shallow depth on background only. Tone: {v['TONE']}.\n"
            f"NO text. NO watermark. NO clutter. NO other people. Readable at 140px thumbnail."),
        2: (f"Split-composition proof photo, square crop. ATTACHED REFERENCE: {v['REF']}.\n"
            f"LEFT: the customer's reference (person/pet/object from the order), waist-up, "
            f"neutral background. RIGHT: finished {v['PRODUCT']} ({v['MATERIAL']}), same scale, "
            f"same frontal angle, centred. Identical lighting both halves, seamless white-to-cream "
            f"join, no arrows, no circles, no text, no borders.\n"
            f"Scale truth: {v['SCALE'] or 'see pack dims'}. Honest likeness — do not beautify "
            f"either side. Tone: {v['TONE']}.\n"
            f"NO text. NO watermark."),
        3: (f"In-situ scale photo, square crop. ATTACHED REFERENCE: {v['REF']}.\n"
            f"Scene: {v['PRODUCT']} where its owner keeps it — {v['ENV']}, "
            f"surrounded by {v['PROPS']}, in the hands of {v['PERSON']} or resting naturally "
            f"in the scene.\n"
            f"Scale truth: {v['SCALE'] or 'see pack dims'} — the reference object appears at "
            f"true relative size beside the product. True proportions, no wide-angle distortion.\n"
            f"Macro focus on the key detail (never a coin, never text): {v['DETAIL']}. Studio-macro lighting, no harsh "
            f"shadows. Tone: {v['TONE']}.\n"
            f"NO text. NO watermark. NO extra props beyond the scene."),
        4: (f"INFOGRAPHIC, composed (art + exact text, never AI text). Square crop.\n"
            f"Art half (left 45%): {v['PRODUCT']} hero in {v['ENV']}, {v['SEASONAL']} frame edges, "
            f"white centre. Generate art only via product_packshot. NO text in art.\n"
            f"Text half (right 55%), exact pack bytes: header 'How it works'; 3 numbered steps "
            f"(photo upload → we custom-make → ship); spec strip: {v['SIZE']} | {v['MATERIAL']}. "
            f"Icons: photo / gear-or-hand / truck. One font, large, high contrast.\n"
            f"Audience: {v['PERSON']}. Tone: {v['TONE']}."),
        5: (f"VARIANTS BOARD, composed (art panels + exact text). Square crop.\n"
            f"Header: benefit line for {v['PRODUCT']}; subline photo → custom product.\n"
            f"Process strip (3-4 mini-panels with arrows): reference → isolate → choose style → "
            f"final, using {v['REF']} as panel 1.\n"
            f"Variant grid (4-6, consistent style, {v['MATERIAL']}, {v['ENV']} framing): labels from "
            f"pack variants. Upsell callout: exact pack price, specific number.\n"
            f"Closer: hero variant large, right side. {v['SEASONAL']} frame. Audience: {v['PERSON']}."),
        6: (f"Warm brand card, square crop, OddHobb cream #F7F3EE, soft light. OFF-ETSY ONLY.\n"
            f"Centre: {v['PRODUCT']} hero render in {v['ENV']}, seasonal accents. Below: "
            f"'Customise yours on oddhobb.com'. Subline: 'First preview free.'\n"
            f"Clean gift-brand feel. NOT an Etsy listing image."),
    }
    prompt = (f"[slot {slot} {f['role']} / {f['job']}] {f['prompt_logic']}\n\n"
              f"{bodies[slot]}\nTemplate ref: {f['prompt_file']}.")
    return {"prompt": prompt, "gaps": gaps, "formula": f, "vars": v,
            "sources": r["sources"]}


def plan_sku(pack: dict, scale_prompt: str = "", provider: str = "cloudflare") -> dict:
    """Whole 5+1 plan for one SKU. Pure — no network, no spend."""
    import sys as _sys
    _sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        from providers import preview as _pv
    except ImportError:
        from pipeline.providers import preview as _pv
    slots = []
    for slot in (1, 2, 3, 4, 5, 6):
        b = build_prompt(slot, pack, scale_prompt)
        pv = _pv(slot, b["prompt"], provider)
        slots.append({"slot": slot, "role": FORMULAS[slot]["role"],
                      "job": FORMULAS[slot]["job"], "etsy": FORMULAS[slot]["etsy"],
                      "size": FORMULAS[slot]["size"], "text": FORMULAS[slot]["text"],
                      "qc": FORMULAS[slot]["qc"], "gaps": b["gaps"],
                      "prompt_chars": len(b["prompt"]),
                      "capability": pv["capability"], "provider": pv["provider"],
                      "cost_usd": pv["request"].get("cost_usd", 0.0)
                      if pv["provider"] == "cloudflare" else None,
                      "r2": FORMULAS[slot]["r2"].format(
                          store=pack.get("store_id") or pack.get("store") or "oddhobb",
                          sku=pack.get("sku", "?"))})
    return {"sku": pack.get("sku", "?"), "slots": slots,
            "series_rules": SERIES_RULES,
            "note": "slots 1-5 → Etsy ranks 1-5. Slot 6 → Pinterest/social/ads ONLY."}


def etsy_checklist(pack: dict) -> dict:
    """Map pack assets to the 5+1. Returns {slots, missing, score}.

    Heuristic v1 (free, local): hero ← assets_now[0]; rest matched by
    role/label keywords in asset dicts (role, agent_blurb, asset_key).
    Unmatched → gap → generate. Additive alongside template.image_checklist.
    """
    assets = pack.get("assets_now") or []
    labels = pack.get("asset_labels") or []

    def _text(a) -> str:
        if isinstance(a, dict):
            return " ".join(str(a.get(k, "")) for k in ("role", "agent_blurb", "asset_key")).lower()
        return str(a).lower()

    keywords = {1: ["hero", "lifestyle", "holding"],
                2: ["proof", "before", "after", "side-by-side", "comparison"],
                3: ["scale", "coin", "finger", "hand", "macro", "detail"],
                4: ["how", "step", "infographic", "spec", "instruction"],
                5: ["option", "variant", "outfit", "grid", "upsell", "bundle"],
                6: ["cta", "oddhobb.com", "preview free", "brand card"]}
    out = []
    for slot in (1, 2, 3, 4, 5, 6):
        hit, src = False, ""
        if slot == 1 and assets:
            hit, src = True, (assets[0] if isinstance(assets[0], str)
                              else assets[0].get("path_or_url") or assets[0].get("asset_key", ""))
        else:
            pool = ([_text(a) for a in assets[1:]] if slot == 1 else
                    [_text(a) for a in assets] + [_text(a) for a in labels])
            for i, t in enumerate(pool):
                if any(k in t for k in keywords[slot]):
                    hit = True
                    src = (assets[i] if i < len(assets) else labels[i - len(assets)])
                    src = src if isinstance(src, str) else src.get("asset_key", str(src))[:60]
                    break
        out.append({"slot": slot, "role": FORMULAS[slot]["role"], "has": hit, "src": src,
                    "required": slot in (1, 2, 3)})
    have_etsy = sum(1 for s in out if s["has"] and s["slot"] <= 5)
    missing = [s["role"] for s in out if not s["has"] and s["slot"] <= 5]
    return {"slots": out, "missing": missing, "score": f"{have_etsy}/5",
            "ready": not [s for s in out if s["slot"] in (1,) and not s["has"]]}
