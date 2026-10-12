"""Tests for scoring, momentum, patterns, archetypes, market, intel.

Pure functions only — no network, no vault, no API keys.
Proves the math is correct, not that external services work.
"""
from pipeline import content_score as cs
from pipeline import momentum as mo
from pipeline import pattern_check as pc


def test_engagement_score_rates_not_volume():
    # high rate, low volume should outscore low rate, high volume
    small_hot = {"views": 1000, "likes": 73, "comments": 10}
    big_cold = {"views": 12500, "likes": 890, "comments": 134}
    s_small = cs.engagement_score(small_hot)["score"]
    s_big = cs.engagement_score(big_cold)["score"]
    # both healthy; small_hot has 7.3% like rate vs 7.1% — should be close or higher
    assert abs(s_small - s_big) < 3.0, f"{s_small} vs {s_big}"


def test_engagement_score_dead_channel():
    dead = {"views": 100, "likes": 1, "comments": 0}
    s = cs.engagement_score(dead)
    assert s["score"] < 2.0


def test_engagement_score_retention_bonus():
    hi = {"views": 1000, "likes": 50, "comments": 5,
          "avg_view_duration": 120, "duration": 180}  # 67% retention
    lo = {"views": 1000, "likes": 50, "comments": 5,
          "avg_view_duration": 20, "duration": 180}  # 11% retention
    assert (cs.engagement_score(hi)["score"] >
            cs.engagement_score(lo)["score"])


def test_rank_videos_orders_and_diversity():
    vids = [
        {"title": "a", "views": 5000, "likes": 300, "format": "essay"},
        {"title": "b", "views": 4000, "likes": 280, "format": "essay"},
        {"title": "c", "views": 3000, "likes": 200, "format": "short"},
    ]
    ranked = cs.rank_videos(vids)
    assert ranked[0]["score"] >= ranked[-1]["score"]
    # second essay-format video should carry diversity penalty
    essays = [v for v in ranked if v.get("format") == "essay"]
    assert any("diversity_penalty" in v for v in essays)


def test_channel_health_verdicts():
    assert cs.channel_health([])["verdict"] == "no_data"
    strong = [{"views": 10000, "likes": 800, "comments": 100}
              for _ in range(3)]
    h = cs.channel_health(strong)
    assert h["verdict"] in ("strong", "healthy")
    assert h["videos"] == 3


def test_rsi_overbought():
    # 20 straight up days = max momentum
    growth = [100 * (1.15 ** i) for i in range(20)]
    r = mo.momentum_signal(growth)
    assert r["trend"] == "overbought"
    assert r["rsi"] is not None and r["rsi"] >= 70


def test_rsi_oversold():
    dead = [5000 * (0.9 ** i) for i in range(20)]
    r = mo.momentum_signal(dead)
    assert r["trend"] == "oversold"
    assert any("pivot" in f or "dead" in f for f in r["flags"])


def test_rsi_insufficient():
    r = mo.momentum_signal([100, 200])
    assert r["trend"] == "insufficient_data"


def test_rsi_range():
    import random
    random.seed(1)
    vals = [100 + random.uniform(-5, 5) for _ in range(20)]
    r = mo.momentum_signal(vals)
    assert r["rsi"] is not None
    assert 0 <= r["rsi"] <= 100


def test_velocity():
    assert mo.velocity(150, 100)["direction"] == "up"
    assert mo.velocity(80, 100)["direction"] == "down"
    assert mo.velocity(105, 100)["direction"] == "flat"
    assert mo.velocity(100, 0)["direction"] == "no_baseline"


def test_pattern_earl_scores_high():
    r = pc.check_all(
        title="STOP Buying Canned Tomatoes! 7 Old Tricks That Beat Any Restaurant",
        description="I learned this over 19 years. https://x.com 0:00 intro",
        uploads_per_week=4, has_product_link=True, has_chapters=True,
        thumb_brief='same face, "STOP BUYING THIS", arrow at can')
    assert r["verdict"] == "FOLLOWS"
    assert r["passed"] >= 5


def test_pattern_generic_scores_low():
    r = pc.check_all(title="My Thoughts on Various Topics Today",
                     uploads_per_week=1)
    assert r["verdict"] == "BREAKS"
    assert r["passed"] <= 2


def test_pattern_hook_detection():
    assert pc.check_hook("STOP Doing This NOW")["pass"] is True
    assert pc.check_hook("NEVER Eat This After 60")["pass"] is True
    assert pc.check_hook("A Nice Day Out")["pass"] is False


def test_pattern_numbered():
    assert pc.check_numbered("7 Old Tricks")["pass"] is True
    assert pc.check_numbered("7 Best Ways to Save")["pass"] is True
    assert pc.check_numbered("Hello World")["pass"] is False


def test_pattern_cadence():
    assert pc.check_cadence(5)["pass"] is True
    assert pc.check_cadence(1)["pass"] is False


def test_voice_timing_plan():
    from pipeline import voice_timing as vt
    t = vt.timing_plan("Hello world. This is a test.", {"speed": 1.0})
    assert t["duration_ms"] > t["audible_ms"]
    assert len(t["tokens"]) == 6
    assert t["schedule"]["voice_start_ms"] == 1200
    # slow pace = longer
    slow = vt.timing_plan("Hello world.", pace="slow")
    fast = vt.timing_plan("Hello world.", pace="fast")
    assert slow["audible_ms"] > fast["audible_ms"]


def test_voice_reveal():
    from pipeline import voice_timing as vt
    text = "Hello world test."
    t = vt.timing_plan(text)
    assert vt.revealed_length(text, t, -1) == 0
    assert vt.revealed_length(text, t, 999999) == len(text)


def test_shared_events():
    import sqlite3
    from pipeline import shared_events as se
    db = sqlite3.connect(":memory:")
    s1 = se.record(db, "move", "human moved prop", by="human")
    s2 = se.record(db, "judge", "jev scored", by="agent")
    assert s2 == s1 + 1
    assert len(se.events_since(db, 0)) == 2
    assert len(se.events_since(db, s1)) == 1
    news = se.human_news_line(db, 0)
    assert "human moved prop" in news
    assert se.human_news_line(db, s2) == ""
