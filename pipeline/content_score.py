"""Content scoring — Phoenix-style weighted engagement scorer, adapted for YouTube.

Source: xai-org/x-algorithm (Apache 2.0) via marcusdavidc/x-open-source-algorithm-skill.
Phoenix predicts 19 engagement probabilities; a weighted scorer combines them.
Exact X weights are private — we use the observed 2026 hierarchy, remapped
from X actions to YouTube actions.

X → YouTube mapping:
  favorite/like (+30)      → like (+30)
  reply (+13.5, +75 w/ author) → comment (+13.5, +75 if creator replies)
  repost (+20)             → share (+20)
  video_quality_view       → high-retention view (avg_view_duration > 50%)
  dwell / dwell_time        → avg_view_duration seconds (depth signal)
  follow_author (strongest) → subscribe (+50, strongest authority signal)
  profile_click (curiosity) → channel_page_click (not in YT API — estimated from subs gained)
  not_interested/block/mute/report (negative) → dislike / low retention (penalty)

Plus X pipeline concepts we adopt:
  - Recency decay (X AgeFilter drops >48h; we decay, not drop)
  - Author diversity (penalize same-format runs — novelty matters)
  - Multi-signal (never rank on views alone)

Pure stdlib. No network. No model calls.
"""
from __future__ import annotations

import math

# Observed 2026 X weights, remapped to YouTube. Tunable via tune().
WEIGHTS = {
    "like": 30.0,
    "comment": 13.5,
    "comment_with_creator_reply": 75.0,   # X: reply with author response
    "share": 20.0,
    "subscribe": 50.0,                     # X: follow_author (strongest)
    "high_retention_view": 15.0,           # X: video_quality_view
    "dwell_second": 0.5,                   # X: CONT_DWELL_TIME_WEIGHT
    "dislike": -15.0,                      # X: negative signals
    "low_retention_penalty": -25.0,        # retention < 20% = passive rejection
}

# Recency: X drops posts >48h from For You. We decay instead of dropping.
# half_life_days=7 → a week-old video scores ~50% of fresh.
HALF_LIFE_DAYS = 7.0

# Diversity: X penalizes repeat authors per session. We penalize repeat
# formats/topics per channel (prevents "same video 5x" death).
DIVERSITY_DECAY = 0.85  # each same-format recent video multiplies by this
DIVERSITY_WINDOW = 5    # look at last N videos for format repeats


def engagement_score(video: dict, weights: dict | None = None) -> dict:
    """Score a single video from its metrics.

    video: {views, likes, comments, shares?, subs_gained?, avg_view_duration?,
            duration?, dislikes?, creator_replied?, age_days?}
    Returns {score, parts} where parts shows each signal contribution.
    """
    w = weights or WEIGHTS
    views = max(1, int(video.get("views") or 0))
    likes = int(video.get("likes") or 0)
    comments = int(video.get("comments") or 0)
    shares = int(video.get("shares") or 0)
    subs = int(video.get("subs_gained") or 0)
    avd = float(video.get("avg_view_duration") or 0)
    dur = max(1, float(video.get("duration") or 60))
    dislikes = int(video.get("dislikes") or 0)
    creator_replied = bool(video.get("creator_replied"))

    retention = min(1.0, avd / dur)

    # rates (per-view, so big and small channels compare fairly)
    like_rate = likes / views
    comment_rate = comments / views
    share_rate = shares / views
    sub_rate = subs / views

    parts = {}
    # X: likes are the primary distribution signal
    parts["likes"] = like_rate * 100 * w["like"] / 30.0
    # X: comments, with huge bonus if creator engages back
    comment_base = comment_rate * 100 * w["comment"] / 13.5
    if creator_replied and comments > 0:
        comment_base += w["comment_with_creator_reply"] / 10.0
    parts["comments"] = comment_base
    # X: shares = high-intent distribution
    parts["shares"] = share_rate * 100 * w["share"] / 20.0
    # X: follow is the strongest authority signal
    parts["subs"] = sub_rate * 100 * w["subscribe"] / 50.0
    # X: quality view + dwell depth
    if retention >= 0.5:
        parts["retention"] = w["high_retention_view"] / 10.0
    elif retention < 0.2 and views > 100:
        parts["retention"] = w["low_retention_penalty"] / 10.0
    else:
        parts["retention"] = (retention - 0.2) * 10.0
    parts["dwell"] = min(10.0, avd * w["dwell_second"] / 10.0)
    # X: negative signals penalize
    parts["dislikes"] = -(dislikes / views) * 100 * abs(w["dislike"]) / 15.0

    raw = sum(parts.values())

    # recency decay (X AgeFilter philosophy: fresh matters)
    age = float(video.get("age_days") or 0)
    decay = 0.5 ** (age / HALF_LIFE_DAYS) if age > 0 else 1.0
    parts["recency_decay"] = decay

    score = raw * decay
    return {"score": round(score, 2), "parts": {k: round(v, 2) for k, v in parts.items()},
            "retention": round(retention, 3)}


def rank_videos(videos: list[dict], weights: dict | None = None) -> list[dict]:
    """Score + rank a list of videos, applying diversity penalty.

    Diversity: X's author_diversity_scorer penalizes repeat authors.
    We penalize repeat formats/topics: each video in the same format
    as a higher-ranked recent video gets DIVERSITY_DECAY multiplier.
    """
    scored = []
    for v in videos:
        s = engagement_score(v, weights)
        scored.append({**v, **s})
    scored.sort(key=lambda x: x["score"], reverse=True)

    # diversity pass: penalize format runs
    seen_formats: dict[str, int] = {}
    for v in scored:
        fmt = str(v.get("format") or v.get("category") or "unknown")
        n = seen_formats.get(fmt, 0)
        if n > 0:
            v["diversity_penalty"] = round(DIVERSITY_DECAY ** n, 3)
            v["score"] = round(v["score"] * v["diversity_penalty"], 2)
        seen_formats[fmt] = n + 1
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def channel_health(videos: list[dict]) -> dict:
    """Aggregate channel-level health from scored videos."""
    if not videos:
        return {"videos": 0, "avg_score": 0, "top_format": None, "verdict": "no_data"}
    scored = rank_videos(videos)
    scores = [s["score"] for s in scored]
    avg = sum(scores) / len(scores)
    # top format by average score
    by_fmt: dict[str, list[float]] = {}
    for s in scored:
        by_fmt.setdefault(str(s.get("format") or "unknown"), []).append(s["score"])
    top_fmt = max(by_fmt.items(), key=lambda kv: sum(kv[1]) / len(kv[1]))[0]
    verdict = "strong" if avg >= 10 else "healthy" if avg >= 5 else "weak" if avg >= 1 else "critical"
    return {"videos": len(videos), "avg_score": round(avg, 2),
            "top_format": top_fmt, "verdict": verdict,
            "ranked": [{"title": s.get("title"), "score": s["score"]} for s in scored[:5]]}
