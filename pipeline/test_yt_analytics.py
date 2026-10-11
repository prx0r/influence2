"""Tests for vendored yt-analytics (KewkLW/yt-analytics-mcp, MIT). All pure — no network."""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)

from yt_analytics import (analyze_text, analyze_title, aggregate, slug_of,
                          save_analysis, load_analysis, list_analyses,
                          compare_channels, CACHE_DIR)
import yt_analytics as _mod


def test_wpm_math():
    text = " ".join(["word"] * 120)
    a = analyze_text(text, 60.0)
    assert a["word_count"] == 120
    assert a["wpm"] == 120.0
    assert a["duration_min"] == 1.0


def test_humor_and_profanity():
    text = "I am stupid and you are wrong stop doing that oh shit this blows my mind"
    a = analyze_text(text, 60.0)
    assert a["humor_counts"]["self_deprecating"] >= 1
    assert a["humor_counts"]["confrontational"] >= 1
    assert a["humor_counts"]["hyperbolic"] >= 1
    assert a["profanity_count"] >= 1
    assert a["profanity_per_min"] == a["profanity_count"]


def test_title_formula():
    t = analyze_title("I Did THIS on STAGE! (Gone Wrong) | Tour?")
    assert t["caps_words"] >= 2
    assert t["has_exclamation"] is True
    assert t["has_parenthetical"] is True
    assert t["has_pipe"] is True
    assert t["has_question"] is True


def _vid(wpm_words, dur, title="T"):
    return {"id": "x", "title": title, "url": "u", "upload_date": None,
            "analysis": analyze_text(" ".join(["w"] * wpm_words), dur),
            "title_analysis": analyze_title(title)}


def test_aggregate():
    agg = aggregate([_vid(200, 60.0), _vid(100, 60.0)])
    assert agg["analyzed_count"] == 2
    assert agg["avg_wpm"] == 150.0
    assert agg["median_wpm"] == 200.0
    assert agg["total_words"] == 300


def test_aggregate_empty():
    assert aggregate([]) == {}
    assert aggregate([{"analysis": {"wpm": None}}]) == {}


def test_slug():
    assert slug_of("https://www.youtube.com/@SomeComic") == "somecomic"
    assert slug_of("@SomeComic") == "somecomic"
    assert slug_of("  ") == "unknown"


def test_cache_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(_mod, "CACHE_DIR", tmp_path)
    out = {"channel": "C", "aggregate": {"avg_wpm": 170.0}, "videos": [], "failed": []}
    save_analysis("c", out)
    assert load_analysis("c")["channel"] == "C"
    assert load_analysis("nope") is None
    lst = list_analyses()
    assert any(r["slug"] == "c" for r in lst)


def test_compare_missing_only(tmp_path, monkeypatch):
    monkeypatch.setattr(_mod, "CACHE_DIR", tmp_path)
    r = compare_channels(["@ghost"])
    assert r["compared"] == [] and r["missing"] == ["@ghost"]


def test_no_sysexit_in_library():
    import inspect
    src = inspect.getsource(_mod.get_channel_videos)
    assert "sys.exit(" not in src  # server-safe vendored change (mentions in comments ok)
