"""Unified feedback harness — all performer signals, one schema, one fusion.

Symbiotic design: characters perform, platforms + audiences respond,
harness collects every signal, fuses them into per-content and
per-character reads, directs the next round. Nobody auto-publishes.

Signal sources (collectors run on their own cadence):
  youtube.stats   — Data API: views/likes/comments/subs per video (hourly) [LIVE]
  youtube.deep    — yt_analytics: transcripts/WPM/humor (weekly) [PARTIAL: captions IP-blocked]
  instagram.stats — Graph API metrics [STUB: needs token]
  tiktok.stats    — Content Posting API [STUB: needs app]
  x.stats         — X API v2 metrics [STUB: needs dev keys]
  arena.votes     — characters DB: Elo, Wilson, theories [LIVE when app runs]
  battle.scores   — graph instances: battle_score, judge_rating [LIVE]
  watch.retention — characters DB short_views [LIVE when app runs]
  pogs            — characters DB laugh events [LIVE when app runs]
  feedbacks       — characters DB ratings 0-3 + room_reaction [LIVE when app runs]
  performance.dials — theory/*.performance.v1.json [LIVE for Ari sets]
  rewards         — core/rewards.py laugh-rate [BUILT, no producers yet]

Each collector returns list[FeedbackSignal]. Fusion combines them.
Pure stdlib except where noted. No network except youtube.stats.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import dataclass, field

CHARACTERS_DB = "/root/characters/audition/auditions.db"
GRAPH_DIR = os.environ.get("CHARACTER_GRAPH_DIR", "/root/bgraph2/registry/characters")
THEORY_DIR = "/root/characters/theory"

# Source weights for fusion. Audience wallet-votes (subs, arena) outrank
# passive signals (views). Ordered by revealed-preference strength.
# Tunable: weights sum to 1.0 across active sources per content item.
SOURCE_WEIGHTS = {
    "arena.votes": 0.25,      # blind A/B, Elo+Wilson — gold standard preference
    "pogs": 0.20,             # laugh events — ground truth laughter
    "watch.retention": 0.15,  # completion rate — attention revealed
    "feedbacks": 0.12,        # 0-3 ratings + room reaction
    "youtube.stats": 0.10,    # views/likes/comments/subs
    "battle.scores": 0.08,    # model + gates score (not audience)
    "performance.dials": 0.05,  # body/voice quality markers
    "youtube.deep": 0.03,     # transcript quality signals
    "rewards": 0.02,          # laugh-rate aggregates
    "instagram.stats": 0.0,   # stub
    "tiktok.stats": 0.0,      # stub
    "x.stats": 0.0,           # stub
}


@dataclass
class FeedbackSignal:
    """One normalized signal about one piece of content."""
    source: str             # e.g. "youtube.stats", "arena.votes"
    content_id: str         # video ID, audition ID, post ID
    character_id: str       # "" if not character-attributed
    score_0_100: float      # normalized 0-100 (higher = better)
    metrics: dict = field(default_factory=dict)  # raw numbers
    weight: float = 0.0     # filled by fusion from SOURCE_WEIGHTS
    at: float = field(default_factory=time.time)


def _characters_db() -> sqlite3.Connection | None:
    try:
        db = sqlite3.connect(CHARACTERS_DB, timeout=10)
        db.row_factory = sqlite3.Row
        return db
    except Exception:
        return None


def _tables(db: sqlite3.Connection) -> set[str]:
    try:
        return {r[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    except Exception:
        return set()


# ── collectors ────────────────────────────────────────────────────

def collect_pogs(character_id: str = "") -> list[FeedbackSignal]:
    """Laugh events → POG rate per audition. More POGs + certain = funnier."""
    db = _characters_db()
    if not db:
        return []
    try:
        if "pogs" not in _tables(db):
            return []
        q = ("SELECT audition_id, COUNT(*) as n, "
             "SUM(CASE WHEN uncertain=0 THEN 1 ELSE 0 END) as certain "
             "FROM pogs GROUP BY audition_id")
        out = []
        for r in db.execute(q).fetchall():
            n, certain = r["n"], r["certain"] or 0
            # score: certain POGs matter most, cap at 100
            score = min(100.0, certain * 20.0 + (n - certain) * 5.0)
            out.append(FeedbackSignal(
                source="pogs", content_id=r["audition_id"],
                character_id=character_id, score_0_100=score,
                metrics={"pogs": n, "certain": certain}))
        return out
    except Exception:
        return []
    finally:
        db.close()


def collect_feedbacks(character_id: str = "") -> list[FeedbackSignal]:
    """0-3 ratings + room reactions → per-audition score."""
    ROOM_SCORE = {"silence": 0, "light": 25, "moderate": 50,
                  "big_laughs": 75, "roaring": 100}
    db = _characters_db()
    if not db:
        return []
    try:
        if "feedbacks" not in _tables(db):
            return []
        out = []
        for r in db.execute(
                "SELECT audition_id, rating, room_reaction FROM feedbacks").fetchall():
            rating_score = (r["rating"] or 0) / 3.0 * 100
            room_score = ROOM_SCORE.get(r["room_reaction"] or "", 50)
            score = rating_score * 0.6 + room_score * 0.4
            out.append(FeedbackSignal(
                source="feedbacks", content_id=r["audition_id"],
                character_id=character_id, score_0_100=round(score, 1),
                metrics={"rating": r["rating"],
                         "room": r["room_reaction"] or ""}))
        return out
    except Exception:
        return []
    finally:
        db.close()


def collect_retention(character_id: str = "") -> list[FeedbackSignal]:
    """Watch retention: completion rate + decision mix per audition."""
    DECISION_SCORE = {"complete": 100, "replay": 90, "like": 75,
                      "comment": 85, "skip": 10}
    db = _characters_db()
    if not db:
        return []
    try:
        if "short_views" not in _tables(db):
            return []
        out = []
        for r in db.execute(
            "SELECT audition_id, "
            "AVG(CAST(watch_ms AS FLOAT) / MAX(duration_ms,1)) as retention, "
            "COUNT(*) as views FROM short_views GROUP BY audition_id"
        ).fetchall():
            retention = min(1.0, r["retention"] or 0)
            views = r["views"] or 0
            # retention is the signal; views are the confidence
            score = retention * 100
            out.append(FeedbackSignal(
                source="watch.retention", content_id=r["audition_id"],
                character_id=character_id, score_0_100=round(score, 1),
                metrics={"retention": round(retention, 3), "views": views}))
        return out
    except Exception:
        return []
    finally:
        db.close()


def collect_arena(character_id: str = "") -> list[FeedbackSignal]:
    """Arena Elo + Wilson → per-contender score. Blind votes = gold standard."""
    db = _characters_db()
    if not db:
        return []
    try:
        tables = _tables(db)
        if "arena_contenders" not in tables:
            return []
        out = []
        for r in db.execute(
                "SELECT id, elo, wins, bouts FROM arena_contenders").fetchall():
            bouts = r["bouts"] or 0
            # Elo centered on 1200; convert to 0-100 with confidence scaling
            elo_score = max(0.0, min(100.0, (r["elo"] - 800) / 8.0))
            # low bouts = low confidence → regress to 50
            conf = min(1.0, bouts / 30.0)
            score = elo_score * conf + 50 * (1 - conf)
            out.append(FeedbackSignal(
                source="arena.votes", content_id=r["id"],
                character_id=character_id, score_0_100=round(score, 1),
                metrics={"elo": r["elo"], "wins": r["wins"], "bouts": bouts}))
        return out
    except Exception:
        return []
    finally:
        db.close()


def collect_battles(character_id: str) -> list[FeedbackSignal]:
    """Graph instances: battle_score + judge_rating per instance."""
    if not character_id:
        return []
    try:
        with open(os.path.join(GRAPH_DIR, f"{character_id}.json")) as f:
            g = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    out = []
    for i in g.get("instances", []):
        bs = i.get("battle_score")
        jr = i.get("judge_rating")
        parts = []
        if bs is not None:
            parts.append(float(bs) * 100)
        if jr is not None:
            parts.append(float(jr) * 10)  # 0-10 → 0-100
        if not parts:
            continue
        score = sum(parts) / len(parts)
        out.append(FeedbackSignal(
            source="battle.scores", content_id=i.get("instance_id", ""),
            character_id=character_id, score_0_100=round(score, 1),
            metrics={"battle_score": bs, "judge_rating": jr,
                     "modulator": i.get("modulator", ""),
                     "operator": i.get("operator", ""),
                     "scenario": i.get("scenario_id", "")}))
    return out


def collect_performance_dials() -> list[FeedbackSignal]:
    """MediaPipe + ASR performance markers → quality signals per set.

    Reads theory/killtony-minutes/*.performance.v1.json when present.
    Scores on energy arc coherence + peak body engagement.
    """
    import glob
    out = []
    for p in glob.glob(os.path.join(
            THEORY_DIR, "killtony-minutes", "*.performance.v1.json")):
        try:
            with open(p) as f:
                d = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        stem = os.path.basename(p).replace(".performance.v1.json", "")
        # score from available markers — degrades gracefully
        score = 50.0
        metrics: dict = {}
        if isinstance(d, dict):
            arc = d.get("energy_arc", "")
            # coherent arcs score higher than flat
            if arc in ("cold_then_hot", "build", "escalating"):
                score += 15
                metrics["energy_arc"] = arc
            elif arc in ("flat", "flat_build"):
                score -= 5
                metrics["energy_arc"] = arc
            peaks = d.get("peak_windows") or d.get("peaks") or []
            if peaks:
                score += min(20, len(peaks) * 5)
                metrics["peaks"] = len(peaks)
            anger = d.get("anger_present")
            if anger is True:
                # performative anger is a strong vehicle (per anger model)
                score += 10
                metrics["anger"] = d.get("anger_type", "present")
        out.append(FeedbackSignal(
            source="performance.dials", content_id=stem,
            character_id="", score_0_100=round(max(0, min(100, score)), 1),
            metrics=metrics))
    return out


def collect_youtube_stats(videos: list[dict],
                          character_id: str = "") -> list[FeedbackSignal]:
    """YouTube metrics → per-video score via Phoenix-weighted scorer.

    videos: [{id, views, likes, comments, ...}] — from API or learn tables.
    Uses pipeline/content_score.py (X-algo weights remapped to YouTube).
    """
    try:
        import sys
        sys.path.insert(0, "/root/influence2")
        from pipeline import content_score as _cs
    except ImportError:
        return []
    out = []
    for v in videos:
        try:
            s = _cs.engagement_score(v)
        except Exception:
            continue
        out.append(FeedbackSignal(
            source="youtube.stats", content_id=v.get("id", ""),
            character_id=character_id,
            score_0_100=round(max(0, min(100, s["score"] * 10)), 1),
            metrics={"phoenix_score": s["score"],
                     "retention": s.get("retention"),
                     "views": v.get("views", 0)}))
    return out


# ── fusion ────────────────────────────────────────────────────────

def fuse(signals: list[FeedbackSignal]) -> dict:
    """Combine all signals per content_id into a fused read.

    Weighted average by SOURCE_WEIGHTS, renormalized over active sources.
    Returns {content_id: {score, verdict, signals: {source: score}}}.
    """
    by_content: dict[str, list[FeedbackSignal]] = {}
    for s in signals:
        s.weight = SOURCE_WEIGHTS.get(s.source, 0.0)
        if s.weight > 0:
            by_content.setdefault(s.content_id, []).append(s)
    out = {}
    for cid, sigs in by_content.items():
        total_w = sum(s.weight for s in sigs)
        if total_w <= 0:
            continue
        score = sum(s.score_0_100 * s.weight for s in sigs) / total_w
        if score >= 70:
            verdict = "hot"
        elif score >= 55:
            verdict = "growing"
        elif score >= 40:
            verdict = "steady"
        elif score >= 25:
            verdict = "cooling"
        else:
            verdict = "cold"
        out[cid] = {
            "score": round(score, 1), "verdict": verdict,
            "character_id": sigs[0].character_id,
            "signals": {s.source: {"score": s.score_0_100,
                                   "weight": s.weight,
                                   "metrics": s.metrics} for s in sigs},
        }
    return out


def fuse_character(signals: list[FeedbackSignal],
                   character_id: str) -> dict:
    """Per-character read: group fused content by modulator/operator/scenario.

    Returns what the manager needs for direction:
    {by_modulator, by_operator, by_scenario, top_content, bottom_content,
     direction_hint}
    """
    fused = {cid: f for cid, f in fuse(signals).items()
             if f["character_id"] == character_id or not f["character_id"]}
    # pull battle metadata for grouping
    groups: dict[str, dict[str, list[float]]] = {
        "modulator": {}, "operator": {}, "scenario": {}}
    for sig in signals:
        if sig.source != "battle.scores":
            continue
        if character_id and sig.character_id != character_id:
            continue
        m = sig.metrics
        for dim in ("modulator", "operator", "scenario"):
            key = str(m.get(dim) or "unknown")
            groups[dim].setdefault(key, []).append(sig.score_0_100)
    summary = {}
    for dim, vals in groups.items():
        summary[dim] = {k: round(sum(v) / len(v), 1)
                        for k, v in sorted(vals.items(),
                                           key=lambda kv: sum(kv[1]) / len(kv[1]),
                                           reverse=True)}
    ranked = sorted(fused.items(), key=lambda kv: kv[1]["score"], reverse=True)
    scores = [f["score"] for _, f in ranked]
    if not scores:
        hint = "hold"
    elif max(scores) >= 70 and len([s for s in scores if s >= 55]) >= 2:
        hint = "double_down"
    elif max(scores) < 30:
        hint = "pivot"
    elif len(scores) >= 3:
        hint = "experiment"
    else:
        hint = "hold"
    return {"character_id": character_id,
            "content_count": len(ranked),
            "by_modulator": summary.get("modulator", {}),
            "by_operator": summary.get("operator", {}),
            "by_scenario": summary.get("scenario", {}),
            "top_content": [dict(id=cid, **f) for cid, f in ranked[:3]],
            "bottom_content": [dict(id=cid, **f) for cid, f in ranked[-2:]],
            "direction_hint": hint}


def collect_all(character_id: str = "",
                youtube_videos: list[dict] | None = None) -> dict:
    """Run every available collector, return signals + fused reads.

    Graceful: missing DBs, missing tables, and stub sources all return [].
    Never raises — a broken source degrades, never kills the harness.
    """
    signals: list[FeedbackSignal] = []
    collectors = [
        ("pogs", lambda: collect_pogs(character_id)),
        ("feedbacks", lambda: collect_feedbacks(character_id)),
        ("watch.retention", lambda: collect_retention(character_id)),
        ("arena.votes", lambda: collect_arena(character_id)),
        ("battle.scores", lambda: collect_battles(character_id)),
        ("performance.dials", collect_performance_dials),
    ]
    if youtube_videos:
        collectors.append(
            ("youtube.stats",
             lambda: collect_youtube_stats(youtube_videos, character_id)))
    active: list[str] = []
    for name, fn in collectors:
        try:
            sigs = fn()
            if sigs:
                active.append(f"{name}:{len(sigs)}")
            signals.extend(sigs)
        except Exception:
            continue
    return {"signals": [{"source": s.source, "content_id": s.content_id,
                         "score": s.score_0_100, "metrics": s.metrics}
                        for s in signals],
            "active_sources": active,
            "fused": fuse(signals),
            "character": fuse_character(signals, character_id)}
