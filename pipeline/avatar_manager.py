"""Avatar manager — multi-avatar dashboard data + service operations.

The service model: creators bring characters, we manage everything.
  Store: OddHobb/Etsy listings + Prodigi fulfillment (no Shopify needed)
  Content: direction, release gates, analytics (no strategy needed)
  Advice: market positioning, product strategy, launch plans
  Publishing: pipeline handles it, human approves

This module aggregates per-avatar health across all managed avatars
for dashboard display + prioritization (who needs attention?).
"""
from __future__ import annotations

import glob
import json
import os
import sqlite3

from pipeline import avatar_intel as ai
from pipeline import character_market as cm

GRAPH_DIR = os.environ.get("CHARACTER_GRAPH_DIR",
                           "/root/bgraph2/registry/characters")
IDENTITIES_DIR = "/root/influence2/identities"


def list_managed_avatars() -> list[dict]:
    """All avatars under management (have identity dirs)."""
    out = []
    for path in sorted(glob.glob(os.path.join(IDENTITIES_DIR, "*/identity.json"))):
        try:
            with open(path) as f:
                ident = json.load(f)
            slug = ident.get("slug", os.path.basename(os.path.dirname(path)))
            out.append({
                "slug": slug,
                "name": ident.get("name", slug),
                "category": ident.get("category", "unknown"),
                "character_id": ident.get("character_id", ""),
                "slots": {k: v.get("status", "unknown")
                          for k, v in (ident.get("slots") or {}).items()},
            })
        except (json.JSONDecodeError, OSError):
            continue
    return out


def avatar_health(slug: str) -> dict:
    """Health snapshot for one avatar: graph + learn + validation.

    Returns {slug, character, validation, content, revenue_signals}.
    Never raises — missing data degrades to unknown, not errors.
    """
    out: dict = {"slug": slug, "status": "unknown"}
    # identity
    ident_path = os.path.join(IDENTITIES_DIR, slug, "identity.json")
    try:
        with open(ident_path) as f:
            ident = json.load(f)
        out["name"] = ident.get("name", slug)
        out["character_id"] = ident.get("character_id", "")
        out["slots"] = {k: v.get("status", "?")
                        for k, v in (ident.get("slots") or {}).items()}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        out["name"] = slug
        out["character_id"] = ""
        out["slots"] = {}
    cid = out.get("character_id", "")
    # graph: instances, edges, directed (management) activity
    if cid:
        try:
            with open(os.path.join(GRAPH_DIR, f"{cid}.json")) as f:
                g = json.load(f)
            insts = g.get("instances", [])
            edges = g.get("edges", [])
            directed = [e for e in edges if e.get("rel") == "directed"]
            scores = [i.get("battle_score") for i in insts
                      if i.get("battle_score") is not None]
            out["graph"] = {
                "instances": len(insts),
                "edges": len(edges),
                "directions": len(directed),
                "avg_battle": round(sum(scores) / len(scores), 2) if scores else None,
                "status": g.get("status", "?"),
            }
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            out["graph"] = {"instances": 0, "edges": 0, "directions": 0}
    else:
        out["graph"] = {"instances": 0, "edges": 0, "directions": 0}
    # learn: content items + snapshots for this slug
    try:
        from pipeline import learn as _learn
        db = sqlite3.connect(_learn.DB_PATH, timeout=10)
        try:
            items = db.execute(
                "SELECT COUNT(*), COALESCE(SUM(s.views),0) FROM content_items i "
                "LEFT JOIN performance_snapshots s ON s.item_id=i.id "
                "WHERE i.brand_slug=?", (slug,)).fetchone()
            out["content"] = {"items": items[0] or 0,
                              "total_views": items[1] or 0}
        finally:
            db.close()
    except Exception:
        out["content"] = {"items": 0, "total_views": 0}
    # attention flag: who needs the manager?
    needs = []
    g = out.get("graph", {})
    c = out.get("content", {})
    if g.get("instances", 0) == 0 and c.get("items", 0) == 0:
        needs.append("no_content: nothing published yet")
        out["status"] = "new"
    elif g.get("directions", 0) == 0 and (g.get("instances", 0) or 0) > 3:
        needs.append("no_direction: performing without management")
        out["status"] = "unmanaged"
    else:
        out["status"] = "active"
    out["needs_attention"] = needs
    return out


def manager_overview() -> dict:
    """All avatars, ranked by attention needed. For dashboard + cron."""
    avatars = list_managed_avatars()
    health = [avatar_health(a["slug"]) for a in avatars]
    # unmanaged + new first
    order = {"unmanaged": 0, "new": 1, "active": 2}
    health.sort(key=lambda h: order.get(h.get("status", "?"), 3))
    return {"avatars": health,
            "count": len(health),
            "need_attention": [h["slug"] for h in health
                               if h.get("needs_attention")]}
