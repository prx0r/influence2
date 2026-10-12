# The Cellar — Multipurpose Underground Venue (Marble Splat Spec)

*Kill Tony intimacy + jazz club warmth + Mos Eisley cantina otherness.
One room, many nights, different species operate it.*

---

## Master prompt (room shell, no people, no instruments)

> Tiny underground comedy cellar fused with a late-night jazz joint and a
> far-out cantina. Exposed brick walls layered with stickers, gig flyers,
> and strange alien graffiti. Low black ceiling with visible pipes and
> hanging Edison bulbs. Small raised wooden stage with a single mic stand
> and worn brick backdrop. Neon sign mount above stage (unlit frame, sign
> added separately). Eight small round tables with flickering candles
> crammed close to the stage. Bentwood chairs, some stacked in the corner.
> Sticky wooden floor with sawdust patches. A small bar along the right
> wall with mismatched bottles glowing amber. Haze drifting through a
> single warm spotlight beam aimed at the empty mic. Deep shadows swallowing
> the corners. Intimate, grungy, otherworldly, lived-in. Photorealistic.
> No people, no instruments, no text, no readable signs.

**Why each element:**
- Brick + stickers/flyers → Kill Tony cellar texture (forgiving, hides artifacts)
- Edison bulbs + candles → jazz warmth (amber pools, not overhead fluorescents)
- Alien graffiti + otherness → Mos Eisley signal (this room hosts *species*, not just humans)
- Unlit neon mount → swappable sign per night (POGTOWN pink / BLUE CELLAR blue / TALES amber)
- Bar with amber bottles → revenue signal (drinks = real venue, not set)
- Haze in spotlight → depth cue (splat renders haze beautifully, hides far-wall mush)
- No people/instruments/text → clean stage for compositing (performers + props + signs separately)

## Night variants (same room, furniture + light shifts)

| Night | Sign | Furniture | Light | Audio bed |
|---|---|---|---|---|
| Tue open mic | POGTOWN pink | Mic + stool, 8 tables full | Harsh spot, house half | Crowd murmur, glass |
| Wed jazz trio | BLUE CELLAR blue | Piano L, drums C, bass R, 4 tables | Warm wash, all lit | Brush swish, bass hum |
| Thu stories | TALES amber | Armchair + side table + candle, 2 tables | Tight spot, rest black | Fire crackle |
| Fri headliner | POGTOWN pink full | Mic + stool, 8 tables, standing room | Full lights, neon max | Packed crowd bed |
| Sat late jazz | BLUE CELLAR dim blue | Trio tight, candles only on tables | Blue wash, near-dark | Brushes, ice, low talk |
| Sun dark | Off | One candle cluster center | Moon/window only (if any) | Rain loop (sleep stream?) |

## Species operators (rotating staff, same room)

| Night | Operator species | Role | Visual cue |
|---|---|---|---|
| Tue | Human (bartender) | Takes orders, heckles lightly | Apron, towel over shoulder |
| Wed | Reptilian (from Galactic world) | Sound engineer, too precise | Headphones over scales, level-obsessed |
| Thu | Brownie (Folk world) | Candle lighter, seat usher | Small, fast, appears in corners |
| Fri | Kappa (Kyle?) | Bouncer, cucumber-based diplomacy | Poolside towel, water dish |
| Sat | Gray (tall, quiet) | Late-night bartender, says nothing | Polishes same glass all night |

Staff are background regulars, not headliners. Audience learns them across nights. Merch potential (Kyle's towel, Brownie candle set).

## Camera ring (5 locked, dissolve only)

| Camera | Frames | Best nights |
|---|---|---|
| Stage close | Performer waist-up, mic, brick | Comedy (punchline holds) |
| Stage wide | Full stage + neon + first tables | Openings, closings |
| Audience POV | Over crowd heads toward stage | Immersion (viewer sits at table) |
| Bar side | Bartender + bottles + stage bg | Between-act texture, jazz |
| Corner wide | Whole room, haze, all tables | Establishing, sleep-stream static |

Rules: ≤0.5°/s drift, 2s dissolve on phrase/section boundaries, hold 2-4 min. Corner wide dominates sleep content (lowest energy).

## Generation plan

1. **Draft tier** ($0.12): room shell prompt above. Check layout (stage position, table density, bar placement, ceiling height feel).
2. **Iterate prompt** if wrong (more/less tables, bar left vs right, ceiling higher/lower). Drafts are cheap — try 3 variants ($0.36 total).
3. **HQ winner** ($1.20): full quality on best layout.
4. **Sign variants**: generate 3 neon sign close-ups separately (POGTOWN pink / BLUE CELLAR blue / TALES amber) as composable overlays — OR single unlit mount + add text in post (cheaper, crisper type).
5. **Verify in viewer**: orbit full 360°, check far-wall quality, table readability, stage sightlines from audience POV. If mushy beyond 5m, accept (cameras stay within 5m) or Plus-cube expand.

Total venue cost: ~$1.50. Hosts everything forever.

---

## Reference precedents (real buildings/spaces)

### Blaibach Concert Hall (Peter Haimerl, Bavaria, 2014)
- **Descend to enter:** concrete stairs through slit in ground → subterranean lobby with bar wrapping auditorium → hall. The descent IS the opening shot (leave world behind, enter music below).
- **Pleated concrete walls:** folded layers per acoustic spec, light slits leaking between. Sound looks like folded stone. Specify "pleated concrete + light slits" for concert variant prompt.
- **200 seats, sold out, village of 2,000.** Intimate scale proven commercially.
- **Floating seats** on iron swords above light slits (weightless audience feel).
- Links: archdaily.com/567635 (60 photos), dezeen (ровно concrete interior), Yatzer (best interior shots). Search "Blaibach interior" for money shots.
- **Apply:** descent sequence for all venues (stairs down = sleep cue), pleated walls for concert room prompt, bar-wrapping-auditorium layout for cellar (bar along wall serving seated audience).

### Mos Eisley Cantina (Star Wars, 1977 — design bible)
- **Circular bar:** everyone faces inward, audience sees each other. Comedy needs witnesses. Consider round bar variant (vs straight) for Pogtown nights.
- **Shady alcoves:** perimeter booths for private deals, eavesdropped jokes, species huddling. Side-action cameras. Whispered bits land harder in alcoves than on stage.
- **Modal Nodes corner:** live band position mapped 1:1 to our jazz trio layout. Bith musicians = reptilian house band precedent.
- **Droid detector at door** ("we don't serve their kind"): Jev pre-filter made diegetic. Room has standards in-fiction, not just code. Bouncer character enforces.
- **Trophy walls** (crocodile head, skulls, space-fish): remnant walls proven at galactic scale. Lucas hung trophies; we hang etchings/posters/seals. Same instinct, same payoff.
- **Brief screen → expanded universe:** 7-min cantina scene spawned Tales anthology (every background alien got backstory). Our model: brief stage appearances → audience demands lore → backstories become content. Every extra is a future headliner.
- **Implication over exposition:** hooded figure, arguing Rodians, band that never stops. Background species with implied lives. Audience invents stories, then demands them. Discovery engine runs on implication.

---

## Laptop-safe splat viewing (render crashed? read this)

Gaussian splats sort millions of ellipsoids per frame on GPU. Integrated graphics / older laptops choke. Options in order:

1. **100k preview** (free, instant): every Marble export includes 100k-splat preview alongside full-res. Load the small one first — 10× fewer splats, runs anywhere, layout readable.
2. **Browser viewer, low pixel ratio**: atlasworldmodel.com/tools/splat-viewer renders locally. Shrink browser window to 50% → quarter pixels → quarter GPU load. Still representative for layout checks.
3. **Server-side screenshots**: ask here — I can render viewpoints headless on this VPS (has GPU? check `nvidia-smi`) and return PNGs. No local GPU needed.
4. **Thumbnail proxy**: Marble web app shows rendered thumbnails without loading splats. Judge layout from pano/thumbnail before downloading .spz at all.
5. **Cloud workstation** (nuclear): vast.ai RTX 3090 at ~$0.20/hr for heavy orbit sessions. Only needed for final quality review, never for drafts.
6. **Skip viewing entirely**: trust the pano (2D preview in Marble dashboard pre-export). If pano looks right, splat is almost certainly fine. Download .spz straight to R2 without local inspection.

**Rule:** never download full-res .spz to laptop. Preview 100k locally, HQ lives on R2 + renders server-side.
