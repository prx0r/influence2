"""Tests for influencer passport shape + stage derivation."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.cmail.influencer import derive_stage, influencer_passport


def test_passport_chain_order_and_shape():
    p = influencer_passport("novaink", "novaink.dev")
    keys = [r["key"] for r in p["resources"]]
    assert keys[:7] == ["name", "handles", "domain", "registrar", "zone", "mailbox", "number"]
    assert keys[-1] == "content"
    # Social claims come from the objective registry (claim_order).
    assert "claim-tt" in keys and "claim-yt" in keys and "claim-x" in keys
    assert keys.index("claim-tt") < keys.index("claim-yt") < keys.index("claim-x")
    assert "verify-report" in keys
    assert p["social_registry"] == "data/social_onboarding.v1.json"
    assert all(r["kind"] and r["label"] and r["desired"] for r in p["resources"])
    kinds = {r["key"]: r["kind"] for r in p["resources"]}
    assert kinds["domain"] == "domain" and kinds["zone"] == "website"
    assert kinds["registrar"] == "registrar" and kinds["mailbox"] == "mail" and kinds["number"] == "number"
    assert kinds["claim-tt"] == "static" and kinds["claim-x"] == "static"


def test_passport_social_kit_carried():
    p = influencer_passport(
        "oddhobbstudio", "oddhobb.com",
        display_name="OddHobb",
        done={"claim-tt": True},
    )
    by = {r["key"]: r for r in p["resources"]}
    assert by["claim-tt"]["desired"]["done"] is True
    kit = by["claim-x"]["desired"]["kit"]
    assert kit["platform"] == "x"
    assert kit["signup_url"].startswith("https://x.com")
    assert "oddhobb.com" in by["claim-x"]["desired"]["instructions"]


def test_stage_derivation():
    assert derive_stage({}) == "untouched"
    assert derive_stage({"name": "READY"}) == "name-only"
    assert derive_stage({"name": "READY", "domain": "READY"}) == "domain-owned"
    assert derive_stage({"domain": "READY", "mailbox": "READY"}) == "wired-needs-content"
    assert derive_stage({"claim-tt": "READY"}) == "wired-needs-content"
    assert derive_stage({"content": "READY"}) == "live"
