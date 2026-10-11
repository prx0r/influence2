"""Tests for images_flow + new MCP tools + pi allowlist. No network, no spend.

Live paths are tested fail-closed only (no grant → refusal). Real Cloudflare
calls are infra-verified manually, never in the suite.
"""
import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)

from images_flow import plan, generate, upload_batch

SKU = "CHARM-CROC-JIBBIT"
STORE = "oddhobb"


def test_plan_pure():
    p = plan(STORE, SKU)
    assert p["sku"] == SKU and len(p["slots"]) == 6
    assert p["listing_id"] == "4587938701"
    assert p["checklist"]["score"].endswith("/5")
    assert all(s["cost_usd"] == 0.0 for s in p["slots"])


def test_generate_dryrun_pure():
    g = generate(STORE, SKU, slots=[1, 3])
    assert g["ok"] is True and g["dry_run"] is True
    assert len(g["items"]) == 2
    for it in g["items"]:
        assert it["prompt"] and it["payload_hash"].startswith("sha256:")
        assert it["request"]["cost_usd"] == 0.0
    bad = generate(STORE, SKU, slots=[9])
    assert bad["ok"] is False


def test_generate_live_fails_closed_without_grant():
    r = generate(STORE, SKU, slots=[1], dry_run=False)
    assert r["ok"] is False and "FAIL CLOSED" in r["reason"]
    r2 = generate(STORE, SKU, slots=[1], dry_run=False, ctx={})
    assert r2["ok"] is False


def test_generate_rejects_unconfigured_provider():
    r = generate(STORE, SKU, provider="fal")
    assert r["ok"] is False and "cloudflare" in r["reason"]


def test_upload_dryrun_plans_ranks():
    d = tempfile.mkdtemp()
    f1 = os.path.join(d, "1-hero.jpg")
    open(f1, "wb").write(b"fake-jpeg-bytes-1")
    u = upload_batch(STORE, SKU, [{"path": f1, "rank": 1}])
    assert u["ok"] is True and u["dry_run"] is True
    assert u["listing_id"] == "4587938701"
    assert len(u["items"]) == 1 and len(u["items"][0]["sha256"]) == 64


def test_upload_rejects_rank_6_and_missing():
    d = tempfile.mkdtemp()
    f1 = os.path.join(d, "6-cta.jpg")
    open(f1, "wb").write(b"x")
    r = upload_batch(STORE, SKU, [{"path": f1, "rank": 6}])
    assert r["ok"] is False and "1-5" in r["reason"]
    r2 = upload_batch(STORE, SKU, [{"path": "/nope.jpg", "rank": 1}])
    assert r2["ok"] is False and "not found" in r2["reason"]
    r3 = upload_batch(STORE, SKU, None)
    assert r3["ok"] is False


def test_upload_live_fails_closed_without_grant():
    d = tempfile.mkdtemp()
    f1 = os.path.join(d, "1-hero.jpg")
    open(f1, "wb").write(b"fake-jpeg-bytes-1")
    r = upload_batch(STORE, SKU, [{"path": f1, "rank": 1}], dry_run=False)
    assert r["ok"] is False and "FAIL CLOSED" in r["reason"]


def test_mcp_dispatch_images_plan():
    sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "dash"))
    from mcp import handle
    out = handle({}, "tools/call", {"name": "images.plan",
                                    "arguments": {"store": STORE, "sku": SKU}})
    assert "result" in out and out["result"]["sku"] == SKU
    names = [t["name"] for t in handle({}, "tools/list", {})["tools"]]
    assert {"images.plan", "images.generate", "images.upload"} <= set(names)


def test_mcp_generate_dryrun_and_fail_closed():
    from mcp import handle
    out = handle({}, "tools/call", {"name": "images.generate",
                                    "arguments": {"sku": SKU, "slots": [1]}})
    assert out["result"]["ok"] is True and out["result"]["dry_run"] is True
    live = handle({}, "tools/call", {"name": "images.generate",
                                     "arguments": {"sku": SKU, "slots": [1], "live": True}})
    assert live["result"]["ok"] is False and "FAIL CLOSED" in live["result"]["reason"]


def test_pi_allowlist_has_etsy_read_tools():
    sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "dash"))
    import agent_chat
    for t in ("pack.compile", "etsy.listing", "task.status"):
        assert t in agent_chat.READONLY_TOOLS, t
        assert any(s["function"]["name"] == t for s in agent_chat.TOOL_SCHEMAS), t
    assert "release.create" not in agent_chat.READONLY_TOOLS  # drafts stay human-gated
