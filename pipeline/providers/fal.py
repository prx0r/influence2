"""fal.ai — paid upgrade path. STUB (not configured).

Same interface as cloudflare.py. Every call fails closed until fal keys
land in vault + human approves spend. Router default stays cloudflare.
"""
from __future__ import annotations

COST_HINT = "see pipeline/costs.py fal.* (0.01-0.05/image)"


def build_request(prompt: str, model: str = "flux_schnell") -> dict:
    """Pure: describe what WOULD be called. No network, no spend."""
    return {"provider": "fal", "model": model, "prompt_chars": len(prompt),
            "status": "stub — fal not configured, use cloudflare",
            "cost_hint": COST_HINT}


def run(prompt: str, model: str = "flux_schnell", ctx: dict | None = None) -> dict:
    """Always fails closed until fal is wired + granted."""
    return {"ok": False, "reason": "fal stub: not configured (use provider=cloudflare)"}
