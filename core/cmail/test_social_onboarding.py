"""Tests for social onboarding kit + passport resources. Offline only."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.cmail.social_onboarding import (
    brand_context,
    format_onboarding_reply,
    list_platforms,
    load_registry,
    passport_social_resources,
    render_brand_onboarding,
    render_platform_kit,
    render_template,
)


def test_registry_loads():
    reg = load_registry()
    assert reg["schema"] == "influence.social_onboarding.v1"
    assert "tiktok" in reg["platforms"]
    assert reg["claim_order"][0] == "tiktok"


def test_render_template_tokens():
    assert render_template("hi {{handle}} on {{domain}}",
                           {"handle": "odd", "domain": "odd.com"}) == "hi odd on odd.com"


def test_brand_context_defaults():
    ctx = brand_context("oddhobbstudio", "oddhobb.com")
    assert ctx["handle"] == "oddhobbstudio"
    assert ctx["email"] == "hello@oddhobb.com"
    assert ctx["website"] == "https://oddhobb.com"


def test_render_platform_kit_oddhobb():
    kit = render_platform_kit("tiktok", "oddhobbstudio", "oddhobb.com",
                              brand={"display_name": "OddHobb"})
    assert kit["resource_key"] == "claim-tt"
    assert "@oddhobbstudio" in kit["instructions"] or "oddhobbstudio" in kit["instructions"]
    assert "https://oddhobb.com" in kit["instructions"]
    assert kit["signup_url"] == "https://www.tiktok.com/signup"
    assert kit["pin_post"] is None  # tiktok has no pin
    assert kit["registry_schema"] == "influence.social_onboarding.v1"


def test_render_x_kit_has_pin():
    kit = render_platform_kit("x", "oddhobbstudio", "oddhobb.com",
                              brand={"display_name": "OddHobb"})
    assert kit["pin_post"] and "oddhobb.com" in kit["pin_post"]
    assert kit["resource_key"] == "claim-x"


def test_render_brand_onboarding_order():
    on = render_brand_onboarding("oddhobbstudio", "oddhobb.com",
                                 brand={"display_name": "OddHobb"})
    assert on["claim_order"] == ["tiktok", "youtube", "x", "instagram", "pinterest"]
    assert len(on["platforms"]) == 5
    assert on["errors"] == []
    text = format_onboarding_reply(on)
    assert "TikTok" in text and "YouTube" in text and "X" in text


def test_passport_social_resources_done_map():
    res = passport_social_resources(
        "oddhobbstudio", "oddhobb.com",
        platforms=["tiktok", "x", "youtube"],
        brand={"display_name": "OddHobb"},
        done={"claim-tt": True},
    )
    keys = [r["key"] for r in res]
    assert keys == ["claim-tt", "claim-yt", "claim-x", "verify-report"]
    by = {r["key"]: r for r in res}
    assert by["claim-tt"]["desired"]["done"] is True
    assert by["claim-x"]["desired"]["done"] is False
    assert by["claim-x"]["kind"] == "static"
    assert by["claim-x"]["desired"]["executor"] == "HUMAN"
    kit = by["claim-x"]["desired"]["kit"]
    assert kit["platform"] == "x"
    assert kit["registry"].endswith("social_onboarding.v1.json")


def test_unknown_platform_raises():
    try:
        render_platform_kit("myspace", "oddhobbstudio", "oddhobb.com")
    except KeyError:
        pass
    else:
        raise AssertionError("expected KeyError")


def test_list_platforms_optional_github():
    plats = {p["platform"]: p for p in list_platforms()}
    assert plats["github"]["optional"] is True
    assert plats["x"]["optional"] is False
