"""Social connector tests — kit-driven instructions, no network."""
from __future__ import annotations

from .social import SocialConnector
from core.cmail.social_onboarding import render_platform_kit


def test_missing_without_handle():
    obs = SocialConnector().observe({"platform": "tiktok"})
    assert obs.status == "MISSING"
    assert obs.executor == "HUMAN"
    assert "tiktok" in obs.human_title.lower() or "TikTok" in obs.human_title


def test_unknown_with_handle_uses_kit_instructions():
    kit = render_platform_kit("x", "oddhobbstudio", "oddhobb.com",
                              brand={"display_name": "OddHobb"})
    obs = SocialConnector().observe({
        "platform": "x",
        "handle": "oddhobbstudio",
        "kit": kit,
    })
    assert obs.status == "UNKNOWN"
    assert obs.executor == "HUMAN"
    assert "oddhobb.com" in obs.human_instructions
    assert obs.human_url == "https://x.com/i/flow/signup"
    assert "Pin:" in obs.human_instructions


def test_connected_is_ready():
    obs = SocialConnector().observe({"platform": "x", "handle": "oddhobbstudio", "state": "connected"})
    assert obs.status == "READY"


def test_optional_not_required():
    obs = SocialConnector().observe({"platform": "github", "handle": "oddhobbstudio", "required": False})
    assert obs.status == "READY"
