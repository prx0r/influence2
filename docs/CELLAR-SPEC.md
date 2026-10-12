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
