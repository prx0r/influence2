"""Cloudflare Workers AI — free-tier image generation.

Proven pattern: /root/sleepdraw/sleepdraw/art.py (flux-1-schnell).
Creds: vault oracle CLOUDFLARE_ACCOUNT_ID + CLOUDFLARE_WORKERS_TOKEN
(fallback CLOUDFLARE_API_TOKEN). Never in tree — read at call time.

Cost: $0.00 (free allocation). Still logged + receipted.
Live calls REQUIRE runtime.execute grant (generate_paid). This module
exposes build_request() (pure) + run() (live, grant-gated by caller).
"""
from __future__ import annotations

import base64
import json
import subprocess
import urllib.request

MODEL_IDS = {
    # text-to-image, free allocation
    "flux": "@cf/black-forest-labs/flux-1-schnell",
    "sdxl": "@cf/stabilityai/stable-diffusion-xl-base-1.0",
    "lightning": "@cf/bytedance/stable-diffusion-xl-lightning",
    "dreamshaper": "@cf/lykon/dreamshaper-8-lcm",
}

# Capability → model. Slots 1-3 photo-real: flux default.
# Slots 4-5 art-half only (text composed locally via PIL, never AI text).
CAPABILITY_MODEL = {
    "identity_transform": "flux",
    "product_packshot": "flux",
    "text_heavy_art": "sdxl",
}

COST_USD = 0.0


def _vault(key: str) -> str:
    try:
        return subprocess.run(
            ["agent-vault", "vault", "credential", "get", key, "--vault", "oracle"],
            capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return ""


def creds() -> tuple[str, str]:
    """(account_id, token). Empty strings when unconfigured — caller fails closed."""
    account = _vault("CLOUDFLARE_ACCOUNT_ID")
    token = _vault("CLOUDFLARE_WORKERS_TOKEN") or _vault("CLOUDFLARE_API_TOKEN")
    return account, token


def build_request(prompt: str, model: str = "flux", steps: int | None = None) -> dict:
    """Pure: prompt → Workers AI request body + URL template. No network."""
    if model not in MODEL_IDS:
        raise ValueError(f"unknown cf model {model!r}; pick {sorted(MODEL_IDS)}")
    body: dict = {"prompt": prompt}
    if steps is not None:
        body["num_steps"] = steps
    return {"model": MODEL_IDS[model], "model_key": model, "body": body,
            "cost_usd": COST_USD}


def run(prompt: str, model: str = "flux", ctx: dict | None = None) -> dict:
    """Live text-to-image. Requires ctx grant (checked by runtime, not here).

    Returns {"ok", "image_bytes", "model", "cost_usd"}. No dry-run path here —
    callers preview via build_request() and execute via runtime.execute().
    """
    import time
    import urllib.error
    if not ctx or not ctx.get("grant"):
        return {"ok": False, "reason": "no execution context with verified grant: FAIL CLOSED"}
    account, token = creds()
    if not account or not token:
        return {"ok": False, "reason": "cloudflare creds not in vault"}
    req = build_request(prompt, model)
    url = (f"https://api.cloudflare.com/client/v4/accounts/{account}"
           f"/ai/run/{req['model']}")
    data = json.dumps(req["body"]).encode()
    last = ""
    for _ in range(4):
        try:
            r = urllib.request.Request(
                url, data=data,
                headers={"Authorization": f"Bearer {token}",
                         "Content-Type": "application/json"})
            with urllib.request.urlopen(r, timeout=180) as resp:
                raw = resp.read()
                if resp.headers.get("Content-Type", "").startswith("image/"):
                    return {"ok": True, "image_bytes": raw, "model": req["model"],
                            "cost_usd": COST_USD}
                img = base64.b64decode(json.loads(raw.decode())["result"]["image"])
                return {"ok": True, "image_bytes": img, "model": req["model"],
                        "cost_usd": COST_USD}
        except urllib.error.HTTPError as e:
            try:
                last = e.read().decode()[:200]
            except Exception:
                last = str(e)[:200]
            time.sleep(15)
        except Exception as e:  # noqa: BLE001
            last = str(e)[:200]
            time.sleep(15)
    return {"ok": False, "reason": f"workers ai failed: {last}"[:250]}


def r2_path(store_id: str, sku: str, rank: int, role: str) -> str:
    """Deterministic R2 key for a slot render. Upload itself is a separate
    effect (r2 ship) — this is just the naming contract."""
    return f"commerce/stores/{store_id}/assets/etsy/{sku}/{rank}-{role}.jpg"
