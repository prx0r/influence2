"""Social onboarding kit — objective, brand-agnostic claim playbooks.

Source of truth: data/social_onboarding.v1.json.
Rendered per brand from handle/email/domain/phone/display_name.
Used by passport builders, dash guide cards, chat, and MCP.

Agents read this module; they do not invent signup steps.
Human still performs every signup (ToS/CAPTCHA). Drafts everywhere.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

_HERE = os.path.dirname(os.path.abspath(__file__))
_INFLUENCE = os.path.dirname(os.path.dirname(_HERE))
DEFAULT_PATH = os.path.join(_INFLUENCE, "data", "social_onboarding.v1.json")

_TOKEN_RE = re.compile(r"\{\{(\w+)\}\}")


def registry_path() -> str:
    return os.getenv("SOCIAL_ONBOARDING_PATH", DEFAULT_PATH)


def load_registry(path: str | None = None) -> dict[str, Any]:
    p = path or registry_path()
    with open(p, encoding="utf-8") as f:
        reg = json.load(f)
    if reg.get("schema") != "influence.social_onboarding.v1":
        raise ValueError(f"unexpected social onboarding schema: {reg.get('schema')}")
    return reg


def brand_context(
    handle: str,
    domain: str = "",
    display_name: str = "",
    email: str = "",
    phone: str = "",
    bio_primary: str = "",
    bio_short: str = "",
    bio_x: str = "",
    bio_youtube: str = "",
    website: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Canonical brand fields used to parameterize kits."""
    handle = (handle or "").lstrip("@").strip()
    domain = (domain or "").strip()
    website = website or (f"https://{domain}" if domain else "")
    email = email or (f"hello@{domain}" if domain else "")
    display_name = display_name or handle.title().replace("-", " ")
    ctx = {
        "handle": handle,
        "domain": domain,
        "display_name": display_name,
        "email": email,
        "phone": phone,
        "website": website,
        "otp_app": "https://phone.agentcom.org/app",
    }
    if extra:
        ctx.update({k: str(v) for k, v in extra.items() if v is not None})
    return ctx


def render_template(text: str, ctx: dict[str, str]) -> str:
    if not text:
        return ""
    def _sub(m: re.Match) -> str:
        key = m.group(1)
        return str(ctx.get(key, m.group(0)))
    return _TOKEN_RE.sub(_sub, text)


def _resolved_defaults(reg: dict[str, Any], ctx: dict[str, str]) -> dict[str, str]:
    defaults = dict(reg.get("defaults") or {})
    out = dict(ctx)
    # Resolve defaults in registration order so later tokens can use earlier ones.
    for key in list(defaults.keys()):
        val = render_template(str(defaults[key]), out)
        out[key] = val
    # Caller overrides win.
    for k, v in ctx.items():
        if v:
            out[k] = v
    # Ensure bio variants exist even if caller passed none.
    for key in ("bio_primary", "bio_short", "bio_x", "bio_youtube", "otp_app"):
        if not out.get(key):
            out[key] = render_template(str(defaults.get(key, "")), ctx)
    return out


def list_platforms(path: str | None = None) -> list[dict[str, Any]]:
    reg = load_registry(path)
    order = reg.get("claim_order") or list(reg.get("platforms", {}).keys())
    platforms = reg.get("platforms", {})
    out = []
    for pid in order:
        p = platforms.get(pid)
        if not p:
            continue
        out.append({
            "platform": pid,
            "label": p.get("label", pid),
            "resource_key": p.get("resource_key", f"claim-{pid}"),
            "optional": bool(p.get("optional")),
            "priority": int(p.get("priority", 50)),
            "signup_url": p.get("signup_url", ""),
            "handle_rule": p.get("handle_rule", ""),
            "account_type": p.get("account_type", ""),
        })
    # Any platforms not in claim_order still listed, after ordered ones.
    for pid, p in platforms.items():
        if pid in order:
            continue
        out.append({
            "platform": pid,
            "label": p.get("label", pid),
            "resource_key": p.get("resource_key", f"claim-{pid}"),
            "optional": bool(p.get("optional")),
            "priority": int(p.get("priority", 50)),
            "signup_url": p.get("signup_url", ""),
            "handle_rule": p.get("handle_rule", ""),
            "account_type": p.get("account_type", ""),
        })
    return out


def render_platform_kit(
    platform: str,
    handle: str,
    domain: str = "",
    brand: dict[str, Any] | None = None,
    path: str | None = None,
) -> dict[str, Any]:
    """Render one platform claim kit for a brand. Raises KeyError if unknown."""
    reg = load_registry(path)
    platforms = reg.get("platforms", {})
    if platform not in platforms:
        raise KeyError(f"unknown platform {platform}")
    p = platforms[platform]
    brand = brand or {}
    ctx = _resolved_defaults(reg, brand_context(
        handle=handle,
        domain=domain,
        display_name=brand.get("display_name", ""),
        email=brand.get("email", ""),
        phone=brand.get("phone", ""),
        bio_primary=brand.get("bio_primary", ""),
        bio_short=brand.get("bio_short", ""),
        bio_x=brand.get("bio_x", ""),
        bio_youtube=brand.get("bio_youtube", ""),
        website=brand.get("website", ""),
        extra={k: v for k, v in brand.items()
               if k not in {"display_name", "email", "phone", "bio_primary",
                            "bio_short", "bio_x", "bio_youtube", "website"}},
    ))
    steps = [render_template(s, ctx) for s in (p.get("steps") or [])]
    pin = render_template(p.get("pin_post") or "", ctx) or None
    first_idea = render_template(p.get("first_content_idea") or "", ctx) or None
    post_claim = [render_template(s, ctx) for s in (p.get("post_claim") or [])]
    bio_key = p.get("bio_variant") or "bio_short"
    bio = ctx.get(bio_key) or ctx.get("bio_short") or ""
    instructions_lines = [
        f"{i+1}. {s}" for i, s in enumerate(steps)
    ]
    instructions = "\n".join(instructions_lines)
    if pin:
        instructions += f"\n\nPin:\n{pin}"
    instructions += f"\n\nBio:\n{bio}"
    if p.get("website_required") and ctx.get("website"):
        instructions += f"\nWebsite: {ctx['website']}"
    if ctx.get("email"):
        instructions += f"\nEmail: {ctx['email']}"
    if ctx.get("phone") and "phone" in (p.get("auth") or ["phone", "email"]):
        instructions += f"\nPhone OTP: {ctx['phone']} (read at {ctx.get('otp_app', '')})"
    do_not = [render_template(s, ctx) for s in (reg.get("defaults") or {}).get("do_not", [])]
    if do_not:
        instructions += "\n\nDo not:\n" + "\n".join(f"· {d}" for d in do_not)
    resource_key = p.get("resource_key") or f"claim-{platform}"
    return {
        "platform": platform,
        "label": p.get("label", platform),
        "resource_key": resource_key,
        "handle": ctx.get("handle", handle),
        "display_name": ctx.get("display_name", ""),
        "account_type": p.get("account_type", ""),
        "signup_url": p.get("signup_url", ""),
        "handle_rule": p.get("handle_rule", ""),
        "auth": p.get("auth") or [],
        "bio": bio,
        "bio_variant": bio_key,
        "website": ctx.get("website", ""),
        "email": ctx.get("email", ""),
        "phone": ctx.get("phone", ""),
        "otp_app": ctx.get("otp_app", ""),
        "steps": steps,
        "pin_post": pin,
        "first_content_idea": first_idea,
        "post_claim": post_claim,
        "priority": int(p.get("priority", 50)),
        "estimate_seconds": int(p.get("estimate_seconds", 120)),
        "optional": bool(p.get("optional")),
        "claim_domain": bool(p.get("claim_domain")),
        "instructions": instructions,
        "do_not": do_not,
        "registry": "data/social_onboarding.v1.json",
        "registry_schema": reg.get("schema"),
        "registry_version": reg.get("version"),
    }


def render_brand_onboarding(
    handle: str,
    domain: str = "",
    platforms: list[str] | None = None,
    brand: dict[str, Any] | None = None,
    path: str | None = None,
) -> dict[str, Any]:
    """Full onboarding kit for one brand across platforms.

    If platforms is given, those ids are selected then sorted by registry
    priority (claim_order default) so dash urgency always matches kit order.
    """
    reg = load_registry(path)
    default_order = reg.get("claim_order") or list((reg.get("platforms") or {}).keys())
    if platforms is None:
        order = list(default_order)
    else:
        wanted = [p.lower() for p in platforms]
        order = [p for p in default_order if p in wanted]
        order += [p for p in wanted if p not in order]
    kits = []
    errors = []
    for pid in order:
        try:
            kits.append(render_platform_kit(pid, handle, domain, brand=brand, path=path))
        except KeyError as e:
            errors.append(str(e))
    kits.sort(key=lambda k: (-k["priority"], k["platform"]))
    defaults = _resolved_defaults(reg, brand_context(
        handle=handle, domain=domain,
        **{k: (brand or {}).get(k, "") for k in
           ("display_name", "email", "phone", "website",
            "bio_primary", "bio_short", "bio_x", "bio_youtube")},
    ))
    return {
        "schema": reg.get("schema"),
        "version": reg.get("version"),
        "handle": defaults.get("handle", handle),
        "domain": defaults.get("domain", domain),
        "display_name": defaults.get("display_name", ""),
        "email": defaults.get("email", ""),
        "phone": defaults.get("phone", ""),
        "website": defaults.get("website", ""),
        "otp_app": defaults.get("otp_app", ""),
        "claim_order": [k["platform"] for k in kits],
        "platforms": kits,
        "do_not": [render_template(s, defaults)
                   for s in (reg.get("defaults") or {}).get("do_not", [])],
        "after_claim": [render_template(s, defaults)
                        for s in (reg.get("defaults") or {}).get("after_claim", [])],
        "otp_dependency": render_template(
            str((reg.get("universal") or {}).get("otp_dependency", "")), defaults),
        "errors": errors,
    }


def passport_social_resources(
    handle: str,
    domain: str = "",
    platforms: list[str] | None = None,
    brand: dict[str, Any] | None = None,
    done: dict[str, bool] | None = None,
    path: str | None = None,
) -> list[dict[str, Any]]:
    """Passport resources for social claims — kind=static so dash ✓ closes them.

    done maps resource_key → True (e.g. claim-tt) or platform id → True.
    """
    done = done or {}
    onboard = render_brand_onboarding(handle, domain, platforms=platforms, brand=brand, path=path)
    resources: list[dict[str, Any]] = []
    for kit in onboard["platforms"]:
        key = kit["resource_key"]
        is_done = bool(done.get(key) or done.get(kit["platform"]))
        resources.append({
            "key": key,
            "kind": "static",
            "label": f"Claim {kit['label']}",
            "desired": {
                "label": f"Claim {kit['label']}",
                "done": is_done,
                "executor": "HUMAN",
                "human_title": f"Claim @{kit['handle']} on {kit['label']}",
                "instructions": kit["instructions"],
                "url": kit["signup_url"],
                "priority": kit["priority"],
                "estimate_seconds": kit["estimate_seconds"],
                "kit": {
                    "platform": kit["platform"],
                    "label": kit["label"],
                    "handle": kit["handle"],
                    "account_type": kit["account_type"],
                    "signup_url": kit["signup_url"],
                    "handle_rule": kit["handle_rule"],
                    "bio": kit["bio"],
                    "pin_post": kit["pin_post"],
                    "website": kit["website"],
                    "email": kit["email"],
                    "phone": kit["phone"],
                    "otp_app": kit["otp_app"],
                    "steps": kit["steps"],
                    "post_claim": kit["post_claim"],
                    "first_content_idea": kit["first_content_idea"],
                    "registry": kit["registry"],
                    "registry_version": kit["registry_version"],
                },
            },
        })
    # Universal verify-report task after claims
    verify_done = bool(done.get("verify-report") or done.get("verify_report"))
    resources.append({
        "key": "verify-report",
        "kind": "static",
        "label": "Verify + report socials",
        "desired": {
            "label": "Verify + report socials",
            "done": verify_done,
            "executor": "HUMAN",
            "human_title": "Report claimed social handles",
            "instructions": (
                "Reply with each platform + final handle/URL.\n"
                "Then: flip bgraph registry branches ready_to_claim → claimed, "
                "flip store.json *_status, tick runbook tracker.\n"
                "Later: one OAuth click per platform (Postiz). Publish stays human_confirm.\n\n"
                "Format: <PLATFORM> DONE @{{handle}} <url>"
            ).replace("{{handle}}", onboard.get("handle", handle)),
            "url": "",
            "priority": 15,
            "estimate_seconds": 180,
        },
    })
    return resources


def format_onboarding_reply(onboard: dict[str, Any]) -> str:
    """Human-readable onboarding brief for chat / dash guide."""
    lines = [
        f"Social onboarding — {onboard.get('display_name')} (@{onboard.get('handle')})",
        f"Domain: {onboard.get('domain')} · Email: {onboard.get('email')}",
        f"Website: {onboard.get('website')}",
        f"Phone OTP: {onboard.get('phone') or '—'} · app {onboard.get('otp_app', '')}",
        f"Claim order: {' → '.join(onboard.get('claim_order') or [])}",
        "",
    ]
    for kit in onboard.get("platforms") or []:
        lines.append(f"## {kit['label']} (@{kit['handle']}) — {kit['resource_key']}")
        lines.append(f"Type: {kit.get('account_type') or '—'} · rule: {kit.get('handle_rule') or '—'}")
        lines.append(f"Signup: {kit.get('signup_url', '')}")
        if kit.get("bio"):
            lines.append(f"Bio: {kit['bio']}")
        if kit.get("pin_post"):
            lines.append(f"Pin: {kit['pin_post']}")
        for i, s in enumerate(kit.get("steps") or [], 1):
            lines.append(f"  {i}. {s}")
        if kit.get("first_content_idea"):
            lines.append(f"First content: {kit['first_content_idea']}")
        lines.append("")
    if onboard.get("otp_dependency"):
        lines.append(f"OTP note: {onboard['otp_dependency']}")
    if onboard.get("do_not"):
        lines.append("Do not:")
        lines.extend(f"· {d}" for d in onboard["do_not"])
    if onboard.get("after_claim"):
        lines.append("After claim:")
        lines.extend(f"· {d}" for d in onboard["after_claim"])
    if onboard.get("errors"):
        lines.append("Errors: " + "; ".join(onboard["errors"]))
    return "\n".join(lines)
