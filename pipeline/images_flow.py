"""Image flow — plan (pure) + generate/upload (grant-gated live).

- plan(): pack → 5+1 plan. Pure. No network, no spend, ever.
- generate(): dry_run (default) → prompts + provider request preview + payload
  hashes (hashes are what a human approves to mint a grant). live → each slot
  through runtime.execute (consequence generate_paid) with ctx grant. FAIL CLOSED.
- upload_batch(): dry_run (default) → rank/file/sha plan + verify steps.
  live → each image through runtime.execute (consequence listing_mutate).

Rule 1: no external consequence outside runtime.execute. All live paths
require ctx={"grant": {...}} whose payload_hash matches the exact payload.
Without it: FAIL CLOSED with a message telling the human what to approve.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)

RUNS_DIR = os.path.join(_HERE, "runs")


def _pack(store_id: str, sku: str) -> dict:
    try:
        from compilers.pack_loader import load
    except ImportError:
        from pipeline.compilers.pack_loader import load
    return load(store_id, sku)


def _scale_for(sku: str) -> str:
    try:
        try:
            from compilers.specs import compile_specs
        except ImportError:
            from pipeline.compilers.specs import compile_specs
        return compile_specs(sku).get("scale_prompt", "")
    except Exception:
        return ""


def plan(store_id: str, sku: str, provider: str = "cloudflare") -> dict:
    """Pure 5+1 plan for one SKU. No network, no spend."""
    try:
        from compilers.images import plan_sku, etsy_checklist
    except ImportError:
        from pipeline.compilers.images import plan_sku, etsy_checklist
    pack = _pack(store_id, sku)
    scale = _scale_for(pack.get("sku", sku))
    p = plan_sku(pack, scale, provider)
    p["checklist"] = etsy_checklist(pack)
    p["listing_id"] = pack.get("etsy_listing_id")
    p["store"] = store_id
    return p


def _spec_payload(slot: int, sku: str, prompt: str, provider: str, model: str) -> dict:
    return {"slot": slot, "sku": sku, "provider": provider,
            "model": model, "prompt": prompt}


def generate(store_id: str, sku: str, slots: list[int] | None = None,
             provider: str = "cloudflare", dry_run: bool = True,
             ctx: dict | None = None, out_dir: str | None = None) -> dict:
    """Dry-run (default): prompts + request preview + payload hashes. Pure.

    live=True: requires ctx grant per slot payload. Each slot executes via
    runtime.execute; bytes saved to out_dir. Any failure fails that slot
    closed; other slots still attempted (results list carries per-slot ok).
    """
    try:
        from compilers.images import build_prompt, FORMULAS
    except ImportError:
        from pipeline.compilers.images import build_prompt, FORMULAS
    pack = _pack(store_id, sku)
    scale = _scale_for(pack.get("sku", sku))
    want = slots or [1, 2, 3, 4, 5, 6]
    for s in want:
        if s not in FORMULAS:
            return {"ok": False, "reason": f"unknown slot {s}"}

    if provider != "cloudflare":
        return {"ok": False,
                "reason": f"provider={provider} not configured (use cloudflare)"}

    try:
        from providers.cloudflare import build_request, CAPABILITY_MODEL
    except ImportError:
        from pipeline.providers.cloudflare import build_request, CAPABILITY_MODEL
    try:
        from providers import SLOT_CAPABILITY
    except ImportError:
        from pipeline.providers import SLOT_CAPABILITY

    items = []
    for s in want:
        b = build_prompt(s, pack, scale)
        model = CAPABILITY_MODEL.get(SLOT_CAPABILITY.get(s, "product_packshot"), "flux")
        payload = _spec_payload(s, pack.get("sku", sku), b["prompt"], provider, model)
        sha = "sha256:" + hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
        items.append({"slot": s, "role": FORMULAS[s]["role"],
                      "prompt": b["prompt"], "gaps": b["gaps"],
                      "request": build_request(b["prompt"], model),
                      "payload": payload, "payload_hash": sha})

    if dry_run:
        return {"ok": True, "dry_run": True, "sku": sku, "store": store_id,
                "provider": provider, "items": items,
                "next": "human reviews prompts → approves exact payload hashes → "
                        "live call with grant"}

    if not ctx or not ctx.get("grant"):
        return {"ok": False,
                "reason": "no execution context with verified grant: FAIL CLOSED. "
                          "Run dry-run first, approve payload hashes, then call "
                          "with ctx.grant."}
    try:
        from runtime import make_spec, execute
    except ImportError:
        from pipeline.runtime import make_spec, execute
    try:
        from providers.cloudflare import run as _cf_run
    except ImportError:
        from pipeline.providers.cloudflare import run as _cf_run

    out_dir = out_dir or os.path.join(RUNS_DIR, sku)
    os.makedirs(out_dir, exist_ok=True)
    results = []
    for it in items:
        spec = make_spec(store_id, f"images.slot{it['slot']}", "generate_paid",
                         "pipeline.providers.cloudflare:run",
                         f"image:{sku}:{it['slot']}", it["payload"],
                         expected_cost_usd=0.0)
        req = it["request"]

        def _exec(req=req, it=it):
            r = _cf_run(it["prompt"], req.get("model_key", "flux"), ctx)
            if not r.get("ok"):
                return {"ok": False, "response": {"reason": r.get("reason")}}
            return {"ok": True, "external_id": f"cf-img:{sku}:{it['slot']}",
                    "response": {"model": r.get("model"), "bytes": len(r.get("image_bytes") or b"")},
                    "image_bytes": r.get("image_bytes", b"")}

        res = execute(spec, ctx["grant"], _exec)
        if res.get("ok") and res.get("image_bytes"):
            path = os.path.join(out_dir, f"{sku}-{it['slot']}-{it['role']}.png")
            with open(path, "wb") as fh:
                fh.write(res["image_bytes"])
            res = {k: v for k, v in res.items() if k != "image_bytes"}
            res["path"] = path
        results.append({"slot": it["slot"], **res})
    ok = all(r.get("ok") for r in results)
    return {"ok": ok, "dry_run": False, "sku": sku, "out_dir": out_dir,
            "results": results}


def upload_batch(store_id: str, sku: str, items: list[dict] | None = None,
                 dry_run: bool = True, ctx: dict | None = None,
                 campaign: str | None = None) -> dict:
    """Batch image → listing ranks. dry_run (default): plan only.

    items: [{path, rank}]. live=True: requires ctx grant; each upload via
    runtime.execute (listing_mutate) → adapter refetch-verifies rank.
    """
    pack = _pack(store_id, sku)
    listing_id = str(pack.get("etsy_listing_id") or "")
    if not listing_id:
        return {"ok": False, "reason": f"{sku}: no etsy_listing_id in pack (draft listing first)"}
    if not items:
        return {"ok": False, "reason": "items required: [{path, rank}] (ranks 1-5 Etsy, never 6)"}
    for it in items:
        if it.get("rank") not in (1, 2, 3, 4, 5):
            return {"ok": False,
                    "reason": f"rank {it.get('rank')} rejected: only 1-5 go to Etsy (6 is off-Etsy only)"}
        if not os.path.isfile(it.get("path", "")):
            return {"ok": False, "reason": f"file not found: {it.get('path')}"}

    planned = []
    for it in items:
        with open(it["path"], "rb") as fh:
            digest = hashlib.sha256(fh.read()).hexdigest()
        planned.append({"rank": it["rank"], "path": it["path"],
                        "sha256": digest,
                        "payload": {"listing_id": listing_id, "rank": it["rank"],
                                    "sha256": digest}})
    if dry_run:
        return {"ok": True, "dry_run": True, "sku": sku, "listing_id": listing_id,
                "items": planned,
                "verify": "per image: POST → GET listing images → rank+count match → receipt",
                "next": "human approves payload hashes → live call with grant"}

    if not ctx or not ctx.get("grant"):
        return {"ok": False,
                "reason": "no execution context with verified grant: FAIL CLOSED. "
                          "Run dry-run first, approve payload hashes, then call "
                          "with ctx.grant."}
    try:
        from runtime import make_spec, execute
    except ImportError:
        from pipeline.runtime import make_spec, execute
    try:
        from adapters.etsy import upload_image
    except ImportError:
        from pipeline.adapters.etsy import upload_image

    results = []
    for it, pl in zip(items, planned):
        spec = make_spec(store_id, "etsy.image.upload", "listing_mutate",
                         "pipeline.adapters.etsy:upload_image",
                         f"listing:{listing_id}:rank{pl['rank']}", pl["payload"],
                         campaign=campaign, expected_cost_usd=0.0)

        def _exec(pl=pl, it=it):
            r = upload_image(listing_id, it["path"], pl["rank"], sku,
                             campaign, dry_run=False, ctx=ctx)
            if not r.get("ok"):
                return {"ok": False, "response": {"reason": r.get("reason")}}
            return {"ok": True, "external_id": str(r.get("listing_image_id", "")),
                    "response": {"rank": r.get("rank"),
                                 "verified_rank": r.get("verified_rank"),
                                 "proof": r.get("proof"),
                                 "receipt_id": r.get("receipt_id")}}

        results.append({"rank": pl["rank"], **execute(spec, ctx["grant"], _exec)})
    ok = all(r.get("ok") for r in results)
    return {"ok": ok, "dry_run": False, "sku": sku, "listing_id": listing_id,
            "results": results}
