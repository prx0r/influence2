# Reference Images Beat Text Prompting (Marble/Atlas)

*Sources: World Labs official docs, sandraschi/worldlabs-mcp PROMPT_GUIDE, atlasworldmodel guides.*

## The hierarchy (best → worst input)

1. **Multi-image directional** (up to 4: Front/Back/Left/Right) — art-direct each wall. Best control, recommended for venues.
2. **Multi-image auto-layout** (up to 8, same aspect ratio) — reconstruct real spaces from overlapping photos.
3. **Single image** (1024px+, 16:9/9:16) — extend a Flux render or photo into a world. Good balance.
4. **360° panorama** (2:1 equirectangular, 2560px wide) — fastest full-surround, but can't combine with other inputs.
5. **Video** (<100MB, <30s, slow steady motion) — walk-through capture.
6. **Text prompt** (2000 char max) — imagined spaces, least control. Use when nothing exists to photograph.

## Why images win for venues

- See before spending ($1.20 blind vs $0 Flux preview + $1.20 informed lift)
- Style lock across walls (same Flux palette → coherent venue, no drift)
- Per-wall control (jazz posters north, brick south — impossible in one prompt)
- Iterate free on 2D, lift once to 3D

## Our workflow: Flux → Marble

```
1. Flux (Workers AI, $0): generate 4 walls (N/E/S/W as separate images)
2. Pick winners, style-lock (same palette, same detail density)
3. Marble multi-image lift ($1.20): 4 walls → coherent 3D room
4. Export .spz → R2 → Spark viewer embeds
```

## image-blaster pattern (neilsonnn/image-blaster, MIT, 4,860 stars)

Claude skills orchestrating full venue build from one image:
- Input image → **Marble splat** (static env, `.spz`)
- Same image → **Hunyuan 3D meshes** (dynamic objects, `.glb` 50k faces)
- Same image → **ElevenLabs SFX** (ambient loop + object sounds)
- Under 5 minutes, file outputs, embeddable in Unity/Unreal/Blender/three.js

Key trick: **clean-plate** — remove dynamic objects from source before lifting (avoids ghost artifacts in splat). Nano-banana for cleanup, GPT-image-2 alternative.

Our equivalent: room splat (Marble) + piano mesh (procedural 88-key, not Hunyuan) + hands (MIDI IK, not mocap) + fire loop (stock/CC0, not ElevenLabs SFX). Same split, domain-specific tools.

## Image requirements (official spec)

- Resolution: 1024px+ long side (2560px for panoramas)
- Format: PNG (recommended), JPG, WebP. Max 20MB.
- Composition: clear depth (foreground/mid/background), floors+walls+ceilings visible, multiple elements, good lighting.
- Avoid: close-ups (no spatial context), people/animals (unsupported), blur, abstract/flat graphics, dark/overexposed, borders (crop — flat patches leak into 3D).
- Multi-image: same aspect ratio + resolution, overlapping views, consistent lighting/color temp, same space.

## Create & edit flow (refine before committing)

1. Pano (~30s) → check layout
2. Pano edit (~20s each) → fix problem areas with natural language + optional reference images
3. Draft world (~20s) → check 3D structure cheap
4. Full world (~5 min) → commit to HQ
5. Expand/click-to-grow (~5 min) → extend beyond boundaries if needed

Fix at pano stage (20s), not after full generation (5 min wasted).
