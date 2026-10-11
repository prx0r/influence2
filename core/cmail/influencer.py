"""Influencer passport shape. New code: ordered resources + stage derivation. Statuses still come from reconcile."""
from __future__ import annotations

from typing import Any

from .social_onboarding import passport_social_resources


def _checklist(label: str, title: str, instructions: str, done: bool = False,
               priority: int = 60) -> dict[str, Any]:
    return {"kind": "static", "label": label,
            "desired": {"label": label, "done": done, "executor": "HUMAN",
                        "human_title": title, "instructions": instructions, "priority": priority}}


DEFAULT_SOCIAL_PLATFORMS = ["tiktok", "youtube", "x", "instagram", "pinterest"]


def influencer_passport(
    handle: str,
    domain: str,
    done: dict[str, bool] | None = None,
    *,
    display_name: str = "",
    email: str = "",
    phone: str = "",
    website: str = "",
    social_platforms: list[str] | None = None,
    brand: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ordered onboarding chain. done maps resource key -> checklist complete (human-marked).

    Social claims come from data/social_onboarding.v1.json via
    core.cmail.social_onboarding — one registry, every brand.
    """
    done = done or {}
    brand = dict(brand or {})
    if display_name:
        brand["display_name"] = display_name
    if email:
        brand["email"] = email
    if phone:
        brand["phone"] = phone
    if website:
        brand["website"] = website

    resources = [
        {"key": "name", **_checklist("Handle + domain picked", f"Pick handle + domain ({handle} / {domain})",
            "Choose the canonical handle and domain, then record them here.", done.get("name", True))},
        {"key": "handles", **_checklist("Handles mapped", f"Map handles for {handle}",
            "Map the handle across social platforms. Record availability proof.", priority=55)},
        {"key": "domain", "kind": "domain", "label": "Domain owned",
         "desired": {"domain": domain}},
        {"key": "registrar", "kind": "registrar", "label": "Registration verified",
         "desired": {"domain": domain}},
        {"key": "zone", "kind": "website", "label": "Zone + site live",
         "desired": {"url": f"https://{domain}"}},
        {"key": "mailbox", "kind": "mail", "label": "Mailbox live",
         "desired": {"domain": domain}},
        {"key": "number", "kind": "number", "label": "Number provisioned",
         "desired": {"capabilities": ["sms_in"], "max_class": "PSEUDONYMOUS_BRIDGE"}},
    ]
    # Social claim kits (objective registry) replace the old single social:x stub.
    platforms = social_platforms if social_platforms is not None else list(DEFAULT_SOCIAL_PLATFORMS)
    resources.extend(passport_social_resources(
        handle, domain, platforms=platforms, brand=brand, done=done,
    ))
    resources.append(
        {"key": "content", **_checklist("First week queued", f"Queue first week for {handle}",
            "Draft 7 posts. Drafts only, publishing stays gated.", priority=40)}
    )
    for r in resources:
        if r["key"] in done:
            r["desired"]["done"] = done[r["key"]]
    return {
        "version": 2,
        "influencer": {"handle": handle, "domain": domain},
        "social_registry": "data/social_onboarding.v1.json",
        "resources": resources,
    }


def derive_stage(states: dict[str, str]) -> str:
    """Stage from resource statuses. Mirrors seed stages so dash stays stable across the port."""
    if states.get("content") == "READY":
        return "live"
    # Any claimed social + mailbox counts as wired; prefer explicit READY socials.
    social_ready = any(k.startswith("claim-") and v == "READY" for k, v in states.items())
    if states.get("mailbox") == "READY" or states.get("social:x") == "READY" or social_ready:
        return "wired-needs-content"
    if states.get("domain") == "READY":
        return "domain-owned"
    if states.get("name") == "READY":
        return "name-only"
    return "untouched"
