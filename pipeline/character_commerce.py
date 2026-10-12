"""Character → commerce bridge — creative output becomes physical products.

Thesis: characters produce art/music/comedy. Fans buy the artifact.
OddHobb network (Etsy + Prodigi print) fulfills. Revenue feeds direction.

Asset types per character:
  portrait    — DiceBear SVG / vibe JPG → poster, tee, mug, sticker (Prodigi print)
  catchphrase — signature lines from winning sets → text merch (tee, mug, card)
  audio       — TTS set WAV → digital album, QR-code vinyl insert, ringtone
  lore        — backstory/world bible → zine, art book, lore cards

Product mapping (Prodigi SKUs + Earl pricing norms):
  poster_a4       — portrait art → $19.99 (print)
  tee_basic       — portrait or catchphrase → $24.99 (apparel)
  mug_11oz        — catchphrase → $14.99 (drinkware)
  sticker_pack    — portrait chibi → $9.99 (sticky)
  art_print_a3    — vibe art → $29.99 (premium print)
  album_digital   — best sets compilation → $9.99 (digital)
  zine_24pg       — lore + portraits → $14.99 (booklet)

Pure stdlib. No network. Asset discovery reads local files.
Listing creation goes through OddHobb pipeline (grant-gated).
"""
from __future__ import annotations

import glob
import json
import os

CHARACTERS_DIR = "/root/characters"
ODDHOBB_DIR = "/root/oddhobbies"

# Prodigi-printable mapping: asset type → product SKUs
ASSET_PRODUCTS = {
    "portrait": [
        {"sku": "poster_a4", "name": "{character} Portrait Poster (A4)",
         "price_usd": 19.99, "prodigi": True},
        {"sku": "tee_basic", "name": "{character} Portrait Tee",
         "price_usd": 24.99, "prodigi": True},
        {"sku": "mug_11oz", "name": "{character} Mug",
         "price_usd": 14.99, "prodigi": True},
        {"sku": "sticker_pack", "name": "{character} Sticker Pack",
         "price_usd": 9.99, "prodigi": True},
    ],
    "catchphrase": [
        {"sku": "tee_basic", "name": '"{line}" Tee',
         "price_usd": 24.99, "prodigi": True},
        {"sku": "mug_11oz", "name": '"{line}" Mug',
         "price_usd": 14.99, "prodigi": True},
        {"sku": "card_a6", "name": '"{line}" Greetings Card',
         "price_usd": 4.99, "prodigi": True},
    ],
    "audio": [
        {"sku": "album_digital", "name": "{character}: Greatest Sets (Digital)",
         "price_usd": 9.99, "prodigi": False},
        {"sku": "art_print_a4", "name": "{character} Album Art Print (A4)",
         "price_usd": 19.99, "prodigi": True},
    ],
    "lore": [
        {"sku": "zine_24pg", "name": "{character} Lore Zine (24pg)",
         "price_usd": 14.99, "prodigi": True},
        {"sku": "art_print_a3", "name": "{character} World Art (A3)",
         "price_usd": 29.99, "prodigi": True},
    ],
}


def catalog_assets(character_id: str) -> dict:
    """Find all sellable assets for a character on local disk."""
    assets: dict[str, list[dict]] = {
        "portrait": [], "catchphrase": [], "audio": [], "lore": []}
    # portraits: static/portraits + vibes
    for pat in [f"{CHARACTERS_DIR}/audition/static/portraits/*.jpg",
                f"{CHARACTERS_DIR}/audition/static/portraits/*.png",
                f"{CHARACTERS_DIR}/audition/static/vibes/*.jpg"]:
        for p in glob.glob(pat):
            base = os.path.basename(p).lower()
            if character_id.split("_")[0] in base or character_id in base:
                assets["portrait"].append({"path": p, "kind": "image"})
    # also check freaks dir for character-specific art
    for p in glob.glob(f"{CHARACTERS_DIR}/freaks/*{character_id}*/*.png") + \
             glob.glob(f"{CHARACTERS_DIR}/freaks/*{character_id}*/*.jpg"):
        assets["portrait"].append({"path": p, "kind": "image"})
    # audio: freak sets (WAV)
    for p in glob.glob(f"{CHARACTERS_DIR}/freaks/*{character_id}*/set.wav") + \
             glob.glob(f"{CHARACTERS_DIR}/freaks/*{character_id}*/set.mp3"):
        assets["audio"].append({"path": p, "kind": "audio"})
    # catchphrases: from graph battle winners (instance texts)
    try:
        import sys
        sys.path.insert(0, "/root/characters/sdk")
        import character_sdk as sdk
        g = sdk.load_character(character_id)
        for inst in g.get("instances", []):
            bs = inst.get("battle_score") or 0
            if bs >= 0.7:  # winners only
                assets["catchphrase"].append({
                    "instance_id": inst.get("instance_id", ""),
                    "modulator": inst.get("modulator", ""),
                    "battle_score": bs,
                    "kind": "text",
                })
    except (FileNotFoundError, ImportError):
        pass
    # lore: canon entries
    for p in glob.glob(f"{CHARACTERS_DIR}/canon/*{character_id}*/*.json"):
        assets["lore"].append({"path": p, "kind": "canon"})
    counts = {k: len(v) for k, v in assets.items()}
    return {"character_id": character_id, "assets": assets,
            "counts": counts,
            "total": sum(counts.values())}


def propose_products(character_id: str, character_name: str = "",
                     max_products: int = 5) -> dict:
    """Map assets → product proposals with Earl-norm pricing.

    Prioritizes: catchphrases from winners (proven) > portraits (visual)
    > audio (compilation) > lore (deep fans). Caps at max_products.
    """
    cat = catalog_assets(character_id)
    name = character_name or character_id.replace("_", " ").title()
    products = []
    # 1. catchphrases (proven lines sell best — Earl precedent)
    for cp in cat["assets"]["catchphrase"][:2]:
        for tpl in ASSET_PRODUCTS["catchphrase"][:2]:  # tee + mug
            products.append({
                "name": tpl["name"].format(
                    line=f"{name} ({cp['modulator']})"),
                "type": tpl["sku"].split("_")[0],
                "price_usd": tpl["price_usd"],
                "prodigi_sku": tpl["sku"],
                "prodigi": tpl["prodigi"],
                "source": f"battle winner {cp['instance_id']} "
                          f"(score {cp['battle_score']})",
                "why": f"Proven line (battle {cp['battle_score']}) "
                       f"in {cp['modulator']} voice",
            })
            if len(products) >= max_products:
                break
        if len(products) >= max_products:
            break
    # 2. portraits (one product per SKU type — no duplicates)
    seen_skus: set[str] = {p.get("prodigi_sku", "") for p in products}
    for i, pt in enumerate(cat["assets"]["portrait"]):
        if len(products) >= max_products:
            break
        # cycle through portrait SKUs: poster → tee → mug → sticker
        tpl = ASSET_PRODUCTS["portrait"][i % len(ASSET_PRODUCTS["portrait"])]
        if tpl["sku"] in seen_skus:
            continue
        seen_skus.add(tpl["sku"])
        products.append({
            "name": tpl["name"].format(character=name),
            "type": tpl["sku"].split("_")[0],
            "price_usd": tpl["price_usd"],
            "prodigi_sku": tpl["sku"],
            "prodigi": tpl["prodigi"],
            "source": pt["path"],
            "why": "Character portrait " + tpl["sku"].replace("_", " "),
        })
    # 3. audio compilation (if sets exist)
    if cat["assets"]["audio"] and len(products) < max_products:
        tpl = ASSET_PRODUCTS["audio"][0]
        products.append({
            "name": tpl["name"].format(character=name),
            "type": "album",
            "price_usd": tpl["price_usd"],
            "prodigi_sku": tpl["sku"],
            "prodigi": tpl["prodigi"],
            "source": f"{len(cat['assets']['audio'])} set recordings",
            "why": "Greatest sets compilation (digital)",
        })
    return {"character_id": character_id, "character_name": name,
            "asset_counts": cat["counts"],
            "products": products[:max_products],
            "fulfillment": "oddhobb-etsy + prodigi-print"}


def oddhobb_stores() -> list[dict]:
    """List OddHobb-network stores that can carry character merch."""
    stores = []
    for slug in ("oddhobb", "pogtown", "grimoirer", "stonedoorway"):
        p = os.path.join(ODDHOBB_DIR, "stores", slug, "store.json")
        if os.path.exists(p):
            try:
                with open(p) as f:
                    s = json.load(f)
                stores.append({"slug": slug,
                               "name": s.get("store_name", slug),
                               "status": s.get("status", "unknown"),
                               "currency": s.get("currency", "USD")})
            except (json.JSONDecodeError, OSError):
                pass
    return stores
