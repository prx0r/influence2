"""Channel graph — entities with branches, linked to characters/products/analytics.

Like sleepintel/bgraph want to be: one graph where channels, characters,
products, and performance connect. Stored as JSON (git-friendly),
queried by workflows, visualized by dash.

Schema: channel-graph.v1
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

GRAPH_PATH = "/root/influence2/data/channels/graph.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def blank_graph() -> dict:
    return {"schema_version": "channel-graph.v1",
            "updated_at": _now()[:10],
            "channels": {}, "links": []}


def load_graph() -> dict:
    if os.path.exists(GRAPH_PATH):
        with open(GRAPH_PATH) as f:
            return json.load(f)
    return blank_graph()


def save_graph(g: dict) -> None:
    g["updated_at"] = _now()[:10]
    os.makedirs(os.path.dirname(GRAPH_PATH), exist_ok=True)
    with open(GRAPH_PATH, "w") as f:
        json.dump(g, f, indent=2, ensure_ascii=False)


def upsert_channel(channel_id: str, spec: dict) -> dict:
    """Add/update a channel entity. spec: full channel plan fields."""
    g = load_graph()
    ch = g["channels"].get(channel_id, {"channel_id": channel_id})
    ch.update({
        "name": spec.get("name", ch.get("name", channel_id)),
        "handle": spec.get("handle", ch.get("handle", "")),
        "niche": spec.get("niche", ch.get("niche", "")),
        "persona": spec.get("persona", ch.get("persona", "")),
        "avatar": spec.get("avatar", ch.get("avatar", "")),
        "format": spec.get("format", ch.get("format", {})),
        "cadence": spec.get("cadence", ch.get("cadence", "")),
        "products": spec.get("products", ch.get("products", [])),
        "funnel": spec.get("funnel", ch.get("funnel", "")),
        "status": spec.get("status", ch.get("status", "planned")),
        "competition": spec.get("competition", ch.get("competition")),
        "archetype": spec.get("archetype", ch.get("archetype", "")),
        "launch_gate": spec.get("launch_gate", ch.get("launch_gate", "")),
    })
    g["channels"][channel_id] = ch
    save_graph(g)
    return ch


def link(frm: str, rel: str, to: str, evidence: str = "") -> dict:
    """Add edge: channel→character, channel→channel (cross-promo),
    channel→product, character→channel (appears_on)."""
    g = load_graph()
    edge = {"from": frm, "rel": rel, "to": to, "evidence": evidence[:500],
            "at": _now()[:10]}
    # dedupe same from/rel/to
    g["links"] = [e for e in g.get("links", [])
                  if not (e["from"] == frm and e["rel"] == rel
                          and e["to"] == to)]
    g["links"].append(edge)
    save_graph(g)
    return edge


def record_metrics(channel_id: str, metrics: dict) -> dict:
    """Write performance snapshot to channel node."""
    g = load_graph()
    ch = g["channels"].get(channel_id, {"channel_id": channel_id})
    snaps = ch.get("snapshots", [])
    snaps.append({"at": _now(), **metrics})
    ch["snapshots"] = snaps[-30:]  # keep last 30
    # update rolling health
    views = [s.get("views", 0) for s in snaps if s.get("views")]
    if views:
        ch["total_views"] = sum(views)
        ch["latest_views"] = views[-1]
    g["channels"][channel_id] = ch
    save_graph(g)
    return ch


def get_channel(channel_id: str) -> dict | None:
    return load_graph()["channels"].get(channel_id)


def list_channels(status: str = "") -> list[dict]:
    chs = load_graph()["channels"]
    out = list(chs.values())
    if status:
        out = [c for c in out if c.get("status") == status]
    return out


def neighbors(channel_id: str, rel: str = "") -> list[dict]:
    """All edges from/to a channel (optionally filtered by rel)."""
    g = load_graph()
    return [e for e in g.get("links", [])
            if (e["from"] == channel_id or e["to"] == channel_id)
            and (not rel or e["rel"] == rel)]
