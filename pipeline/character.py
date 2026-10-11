"""Character hub — influence2's marketing/socials adapter for performer entities.

The SDK (brain) lives in prx0r/characters/sdk/character_sdk.py and is
imported here — this file never reimplements it. This hub owns what the
marketing hub owns:
  - identity profiles (slots/handles per character)
  - analytics FETCHING (yt cache via pipeline/yt_analytics) -> SDK snapshot
  - draft intake for the runtime (SDK drafts; runtime executes)

Graph ops (seed_state/record_instance/ingest_feedback/propose_post) are
re-exported for MCP/tools convenience. Source of truth stays the SDK.
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)
_SDK_DIR = "/root/characters/sdk"
if _SDK_DIR not in sys.path:
    sys.path.insert(0, _SDK_DIR)

import character_sdk as _sdk  # noqa: E402  (brain lives in characters repo)

# Re-exported SDK surface (single home: characters/sdk/character_sdk.py).
load_character = _sdk.load_character
save_character = _sdk.save_character
seed_state = _sdk.seed_state
record_instance = _sdk.record_instance
ingest_feedback = _sdk.ingest_feedback
propose_post = _sdk.propose_post
PLATFORMS_KNOWN = _sdk.PLATFORMS_KNOWN

IDENTITY_DIR = os.path.join(ROOT, "identities")


def load_profile(slug: str) -> dict:
    """Load an influence2 identity profile. Raises FileNotFoundError with a clear msg."""
    p = os.path.join(IDENTITY_DIR, slug, "identity.json")
    if not os.path.exists(p):
        raise FileNotFoundError(f"unknown identity slug {slug!r}")
    with open(p) as f:
        return json.load(f)


def branch_handle(character_id: str, platform: str) -> str | None:
    """Claimed handle for a character+platform from the graph profile (None if unclaimed)."""
    g = _sdk.load_character(character_id)
    for b in ((g.get("profile") or {}).get("branches") or []):
        if b.get("platform") == (platform or "").lower():
            return (b.get("account") or {}).get("handle")
    return None


def ingest_channel_analytics(character_id: str, platform: str) -> dict:
    """Marketing-hub fetch -> SDK record.

    YouTube: reads the pipeline/yt_analytics cache for the claimed handle
    (run yt.analyze first — never triggers network here), hands a snapshot
    to the SDK. Other platforms: honest not-wired error.
    """
    platform = (platform or "").lower()
    if platform not in PLATFORMS_KNOWN:
        return {"ok": False, "error": f"unknown platform {platform}"}
    if platform != "youtube":
        return {"ok": False, "error": f"{platform} adapter not wired yet — youtube only"}
    handle = branch_handle(character_id, platform)
    if not handle:
        return {"ok": False, "error": f"no {platform} handle claimed on {character_id}"}
    try:
        from pipeline import yt_analytics as _yt
    except Exception as e:
        return {"ok": False, "error": f"yt module unavailable: {e}"[:200]}
    d = _yt.load_analysis(_yt.slug_of(handle))
    if not d:
        return {"ok": False, "error": f"no cached analysis for {handle} — run yt.analyze first"}
    agg = d.get("aggregate") or {}
    return _sdk.ingest_analytics_snapshot(
        character_id, platform,
        {"handle": handle, "avg_wpm": agg.get("avg_wpm"),
         "analyzed_count": agg.get("analyzed_count")})
