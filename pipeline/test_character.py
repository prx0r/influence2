"""Tests for the character hub (marketing/socials adapter). SDK logic is tested
in characters/sdk/test_character_sdk.py — here we test hub wiring only."""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)

from pipeline import character as _ch
import pytest


@pytest.fixture()
def _tmp_graph(tmp_path, monkeypatch):
    import character_sdk
    d = tmp_path / "graphs"
    d.mkdir()
    g = {"character_id": "t", "version": "v1",
         "seed": {"philosophy": {"orientation": ["O"], "problem_space": ["P"]},
                  "modulator_range": ["angry"]},
         "profile": {"branches": [{"platform": "youtube",
                                    "account": {"status": "claimed",
                                                "handle": "@t"}}]},
         "instances": [], "edges": [], "updated_at": None}
    (d / "t.json").write_text(json.dumps(g))
    monkeypatch.setattr(character_sdk, "GRAPH_DIR", d)
    return d


def test_profile_loads():
    p = _ch.load_profile("nolan")
    assert p["character_id"] == "no_nose_nolan"
    assert p["slots"]["youtube"]["status"] == "pending"
    with pytest.raises(FileNotFoundError):
        _ch.load_profile("dobby-xyz")


def test_sdk_reexport_seed_state(_tmp_graph):
    s = _ch.seed_state("t", {"id": "sc1", "brief": "b"})
    assert s["character_id"] == "t" and s["scenario"]["id"] == "sc1"


def test_branch_handle(_tmp_graph):
    assert _ch.branch_handle("t", "youtube") == "@t"
    assert _ch.branch_handle("t", "x") is None


def test_analytics_wiring(_tmp_graph, monkeypatch):
    assert _ch.ingest_channel_analytics("t", "myspace")["ok"] is False
    r = _ch.ingest_channel_analytics("t", "instagram")
    assert r["ok"] is False and "not wired" in r["error"]
    import pipeline.yt_analytics as _yt
    monkeypatch.setattr(_yt, "load_analysis", lambda slug: None)
    r2 = _ch.ingest_channel_analytics("t", "youtube")
    assert r2["ok"] is False and "yt.analyze first" in r2["error"]
    monkeypatch.setattr(_yt, "load_analysis",
                        lambda slug: {"aggregate": {"avg_wpm": 165.0, "analyzed_count": 3}})
    r3 = _ch.ingest_channel_analytics("t", "youtube")
    assert r3["ok"] is True and r3["avg_wpm"] == 165.0


def test_propose_post_still_draft_only(_tmp_graph):
    _ch.record_instance("t", {"instance_id": "i1", "seed_id": "t", "scenario_id": "sc1"})
    r = _ch.propose_post("t", "i1", "youtube", "hi")
    assert r["ok"] is False  # claimed, not connected
    assert r.get("posted") is not True
