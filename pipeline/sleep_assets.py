"""Sleep channel digital assets — what each playlist becomes as products.

Maps easy playlist content types → specific digital SKUs with Earl/farm pricing.
Digital only (no print/ship): PDFs, audio, collections, courses, memberships.

Pricing (farm norms):
  guide $27 | bundle $47-59 | circle $9.90/mo | audio loop $2.99 | collection $19.99
"""
from __future__ import annotations

# Content type → digital product ladder
PRODUCT_LADDERS = {
    "stories": [
        {"sku": "tale-collection-vol1", "name": "{channel}: Volume I — {sub} Tales",
         "type": "ebook", "price_usd": 27.0,
         "why": "Curated + illustrated tale solos, bedtime-ready formatting"},
        {"sku": "complete-library", "name": "{channel}: Complete Library ({n} Volumes)",
         "type": "bundle", "price_usd": 59.0,
         "why": "All sub-group collections + future volumes"},
        {"sku": "audio-tales", "name": "{channel}: Sleep Tales Audio ({hours}h)",
         "type": "audio", "price_usd": 9.99,
         "why": "TTS-narrated tales for offline sleep listening"},
        {"sku": "sleep-circle", "name": "{channel} Sleep Circle",
         "type": "membership", "price_usd": 9.90,
         "why": "Monthly: new tales + live read-aloud + community"},
    ],
    "readable": [  # laws, manuals, menus, specs, policies
        {"sku": "annotated-guide", "name": "{channel}: Annotated Guide",
         "type": "guide", "price_usd": 27.0,
         "why": "Source text + plain-English margin notes + index"},
        {"sku": "complete-archive", "name": "{channel}: Complete Archive",
         "type": "bundle", "price_usd": 47.0,
         "why": "All readouts in searchable PDF + audio bundle"},
        {"sku": "cheat-sheets", "name": "{channel}: Quick Reference Cards",
         "type": "lead_magnet", "price_usd": 0.0,
         "why": "Free one-pagers → email capture → guide upsell"},
    ],
    "learning": [  # electrician, codes, educational
        {"sku": "course-notes", "name": "{channel}: Course Notes + Diagrams",
         "type": "guide", "price_usd": 27.0,
         "why": "Structured learning path from readouts + visual aids"},
        {"sku": "cert-prep", "name": "{channel}: Exam Prep Pack",
         "type": "bundle", "price_usd": 59.0,
         "why": "Practice questions + code references + audio review"},
        {"sku": "study-circle", "name": "{channel} Study Circle",
         "type": "membership", "price_usd": 9.90,
         "why": "Monthly: new modules + Q&A + peer study"},
    ],
    "ambient": [  # silent channels: black screen, places, typing
        {"sku": "audio-loop-8h", "name": "{channel}: 8-Hour Sleep Loop",
         "type": "audio", "price_usd": 2.99,
         "why": "Seamless looped ambience for all-night play"},
        {"sku": "loop-library", "name": "{channel}: Complete Loop Library",
         "type": "bundle", "price_usd": 19.99,
         "why": "All room-tones + seasonal variants, downloadable"},
        {"sku": "sleep-circle", "name": "{channel} All-Night Circle",
         "type": "membership", "price_usd": 9.90,
         "why": "Monthly: new loops + request line + ad-free streams"},
    ],
    "reference": [  # timetables, product-lists, labels, patents
        {"sku": "nostalgia-collection", "name": "{channel}: Nostalgia Collection",
         "type": "ebook", "price_usd": 19.99,
         "why": "Curated + annotated nostalgia archive with context essays"},
        {"sku": "complete-archive", "name": "{channel}: Complete Archive",
         "type": "bundle", "price_usd": 39.0,
         "why": "Every readout + high-res scans + searchable index"},
    ],
}

# Playlist slug → content type
PLAYLIST_TYPES = {
    "folk-and-fable": "stories",
    "fine-print": "readable",
    "game-rules": "readable",
    "sleepy-uk": "readable",
    "sleepy-usa": "readable",
    "sleepy-world": "readable",
    "patents": "reference",
    "spec-sheets": "readable",
    "firearm-specs": "reference",
    "menus": "readable",
    "labels": "reference",
    "manuals": "readable",
    "product-lists": "reference",
    "timetables": "reference",
    "sleepy-electrician": "learning",
    "black-screen-community": "ambient",
    "black-screen-contemplations": "ambient",
    "ceiling-2am": "ambient",
    "driveway": "ambient",
    "typing": "ambient",
}


def assets_for_playlist(slug: str, channel_name: str = "",
                        video_count: int = 10,
                        hours_ready: float = 0) -> dict:
    """Propose digital assets for one playlist."""
    ctype = PLAYLIST_TYPES.get(slug, "readable")
    ladder = PRODUCT_LADDERS[ctype]
    name = channel_name or slug.replace("-", " ").title()
    products = []
    for tpl in ladder:
        pname = tpl["name"].format(channel=name, sub="Collected",
                                   n=max(2, video_count // 5),
                                   hours=int(hours_ready) or 8)
        products.append({**tpl, "name": pname})
    # revenue estimate: conservative (1% of 1000 monthly viewers buy guide)
    monthly_viewers = 1000  # placeholder — replace with real analytics
    est = sum(p["price_usd"] * monthly_viewers * 0.01
              for p in products if p["price_usd"] > 0)
    # membership recurring (0.5% convert, $9.90/mo)
    mrr = next((p for p in products if p["type"] == "membership"), None)
    mrr_est = monthly_viewers * 0.005 * 9.90 if mrr else 0
    return {"slug": slug, "channel": name, "content_type": ctype,
            "products": products,
            "est_monthly_one_time": round(est, 2),
            "est_mrr": round(mrr_est, 2),
            "est_total_monthly": round(est + mrr_est, 2)}


def all_playlists_assets(playlists: list[dict]) -> list[dict]:
    """Assets for every playlist. playlists: [{slug, name, videos, hours}]."""
    out = []
    for p in playlists:
        out.append(assets_for_playlist(
            p.get("slug", ""), p.get("name", ""),
            p.get("videos", 10), p.get("hours_ready", 0)))
    out.sort(key=lambda x: x["est_total_monthly"], reverse=True)
    return out
