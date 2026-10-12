# Marble/Atlas API — Key Facts (from atlasworldmodel.com guides, Sep 2026)

## Endpoints (api.worldlabs.ai)
- POST /marble/v1/worlds:generate — header `WLT-Api-Key` (NOT Bearer)
- GET /marble/v1/operations/{id} — poll with backoff 3s→15s
- GET /marble/v1/credits — check balance
- Body: {model: "marble-1.0-draft" | "marble-1.1", world_prompt: {type: "text", text_prompt: "..."}}
- Inputs: text, single image, multi-image, 360° panorama, video

## Costs ($1 = 1,250 credits, min $5 top-up, credits never expire)
- Draft world: 150 credits (~$0.12)
- Standard marble-1.1: 1,500 credits (~$1.20)
- Plus dynamic cube: +300 each (max 5)
- HQ mesh (GLB): 3,500 credits (~$2.80)
- PLY export: FREE. SPZ export: FREE.
- Failed generations: auto-refunded.

## Exports
- .spz (~30MB, 10× smaller, for browsers/CDN)
- .ply (~300MB, lossless archive, keep cold)
- .glb mesh (for Unity/Unreal/Blender, loses view-dependent look)
- Video fly-through: web app only, NOT via API

## Viewing
- Spark renderer (MIT, three.js): github.com/sparkjsdev/spark
- Free browser viewer (no upload, local GPU render)
- Unity/Unreal via splat plugins

## Atlas status (Sep 2026)
- Early access only, no public API. Same platform expected when opens.
- Atlas adds: 1440p camera-controlled video (1 min), point clouds, 2-3 photo reconstruction.
- Everything built for Marble ports forward (same .spz family).

## Production pattern
1. Enqueue (validate → reserve credits → POST generate → store operation_id)
2. Poll worker (backoff, download .spz straight to R2/CDN)
3. Notify (mark done, settle credits, link viewer)
- Never block web requests on generation (minutes). Never embed key in client.
