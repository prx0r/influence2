"""Image providers — Cloudflare free by default, fal later.

Same interface, swappable backend. Preview is pure (no network).
Live generation goes through pipeline.runtime.execute with a grant
(consequence generate_paid). Direct live calls fail closed.
"""
from __future__ import annotations

DEFAULT_PROVIDER = "cloudflare"

# Slot capability → provider default. Slots 1-3 photo, 4-5 art-half.
SLOT_CAPABILITY = {
    1: "identity_transform",
    2: "identity_transform",
    3: "product_packshot",
    4: "product_packshot",   # art half only; text composed locally
    5: "product_packshot",   # art panels only; text composed locally
    6: "product_packshot",   # CTA card, off-Etsy only
}


def preview(slot: int, prompt: str, provider: str = DEFAULT_PROVIDER) -> dict:
    """Pure preview of what generation WOULD do. Zero network, zero spend."""
    import sys as _sys
    import os as _os
    _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    capability = SLOT_CAPABILITY.get(slot, "product_packshot")
    if provider == "fal":
        try:
            from providers.fal import build_request
        except ImportError:
            from pipeline.providers.fal import build_request
        return {"slot": slot, "capability": capability, "provider": "fal",
                "request": build_request(prompt)}
    try:
        from providers.cloudflare import build_request, CAPABILITY_MODEL, COST_USD
    except ImportError:
        from pipeline.providers.cloudflare import build_request, CAPABILITY_MODEL, COST_USD
    model = CAPABILITY_MODEL.get(capability, "flux")
    return {"slot": slot, "capability": capability, "provider": "cloudflare",
            "request": build_request(prompt, model), "cost_usd": COST_USD}
