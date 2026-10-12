# Marble Prompting — How to Prompt Properly

*Sources: World Labs official docs + sandraschi/worldlabs-mcp PROMPT_GUIDE.md (in docs/atlas/).*
*Core principle: **if you can model it in Blender, Marble can render it.***
*Emotions, narrative, painting techniques don't translate. Concrete 3D elements do.*

---

## The formula

```
[ARCHITECTURE/SPACE] + [MATERIALS] + [LIGHTING/TIME] + [WEATHER] + [SCALE] + [COLOUR PALETTE]
```

Every prompt needs all six. Missing any = model guesses (badly).

## Rules that matter

1. **Materials by name** — "aged oak", "moss-covered brick", "cracked marble",
   "polished brass", "rough-hewn stone" render differently. Generic "wood" or
   "stone" gives generic mush. Name every surface.
2. **No people, ever** — Marble makes indistinct silhouettes at best. No faces,
   no figures, no "pianist sitting at". Empty rooms only. We composite performers.
3. **Ground plane first** — most visible surface in any walkthrough. Always specify:
   flagstone, polished wood, sticky boards with sawdust, Persian rug on oak.
4. **Sightlines explicit** — "narrow corridor", "receding into darkness",
   "wide-open", "obstructed view". Controls what the viewer sees vs imagines.
5. **Lighting as geometry** — not "moody" (abstract) but "single Edison bulb
   hanging 2m above stage-left, warm pool 3m diameter, corners fall to black"
   (concrete). Light sources are objects with positions.
6. **Scale numbers** — "3-metre ceiling", "8 round tables", "intimate 10×8m room".
   Without scale, Marble guesses palatial (bad for cellar, good for cathedral).
7. **Draft first** (150cr, $0.12) → HQ the winner (1500cr, $1.20). Never HQ blind.
8. **Create & edit flow** — pano → edit problem areas → draft → world. Fix at
   pano stage (20s per edit), not after full generation (5 min wasted).

## What fails (don't prompt these)

- Abstract: justice, chaos, love, freedom, "cozy feeling", "jazz atmosphere"
- People: any specific person, faces, crowds, audiences (empty rooms only)
- Text: signs with readable words, posters with text (garbled — add text in post)
- Mirrors, motion blur, moving people (confuses reconstruction)

---

## Our venue prompts (rewritten to spec)

### Cellar (Pogtown comedy + jazz + stories)

> Small underground comedy cellar, 10 metres by 8 metres, 2.5-metre black
> ceiling with exposed iron pipes. Exposed red brick walls with layered
> paper flyers and white paint tags. Sticky dark oak plank floor with
> sawdust patches near a small raised wooden stage, 3 metres by 2 metres,
> 40 centimetres high. Single microphone stand centre stage. Worn red
> brick stage backdrop wall. Unlit rectangular neon tube frame mounted
> above stage. Eight small round pine tables with white candle stubs in
> glass jars, bentwood chairs tucked in, arranged facing the stage.
> Narrow oak bar along the right wall with mismatched amber glass bottles
> on back shelf. Single hanging Edison bulb with visible filament above
> each table, warm 2700K pools 2 metres diameter. Far corners receding
> into complete darkness. Thin haze catching one cool-white spotlight beam
> aimed at the empty microphone from above front. Colour palette: amber
> candle glow against deep umber shadow, dull red brick, black ceiling.

**Why this works per the rules:** every surface named (red brick, dark oak,
pine, bentwood, amber glass). Scale explicit (10×8m, 2.5m ceiling, 8 tables).
Lighting geometric (Edison positions, spot direction, pools measured). No
people. No text (neon unlit — add POGTOWN in post). Sightlines (corners to
darkness = intimate, not cavernous).

### Concert room (Classical Nights piano)

> Intimate wood-panelled recital room at night, 8 metres by 6 metres,
> 3-metre ceiling with dark mahogany beams. Walls of aged walnut panels
> with brass picture lights (unlit). Polished dark oak floor with a large
> faded Persian rug, deep reds and navy, centred in the room. Tall
> multi-paned window on the left wall showing night rain streaks on glass,
> faint blue moonlight bleeding through. Heavy forest-green velvet curtains
> drawn to one side of the window, brass tiebacks. Empty floor space where
> a grand piano will stand (no piano in scene). Single brass floor lamp
> with cream silk shade in the far right corner, unlit, warm bulb visible.
> Rows of empty bentwood chairs with dark leather seats arranged in a
> shallow arc facing the empty piano position, fading into shadow at the
> back. Colour palette: deep walnut brown, forest green velvet, navy rug,
> warm amber lamp glow against blue-black window light.

**Why:** piano deliberately absent (separate splat/mesh for toggling).
Chairs face empty position (audience sightline established without performer).
Two-tone lighting (amber lamp vs blue window) gives cameras contrast to work
with. Rain on glass = free atmosphere (Marble renders glass + streaks well).

### Library corner (Folk & Fable stories + Grimoire rituals)

> Dark library corner at night, floor-to-ceiling mahogany bookshelves on
> two walls filled with leather-bound volumes in oxblood, forest, and
> umber. Worn Turkish rug in deep reds over dark oak floorboards. Leather
> wingback armchair angled toward a stone fireplace with unlit logs and
> blackened firebox, brass fender. Small round mahogany side table beside
> the chair with an unlit pillar candle in brass holder and a closed
> leather-bound book. Tall narrow window with heavy damask curtains,
> night black beyond glass. Single green-shaded banker's lamp on a low
> bookshelf, warm pool on spines. Far shelves receding into complete
> darkness. Colour palette: oxblood leather, brass glints, deep wood brown,
> single warm lamp against enveloping black.

**Why:** fireplace unlit (fire is composited loop, not baked — allows
on/off per video + flicker control). Book closed (opens in animation —
transformation reads as event). Banker's lamp = iconic library signal
(single green shade = instantly legible "reading room" at thumbnail size).
Grimoire variant: swap candle colour to violet + book to black leather
(same room, palette shift in post or second generation).

---

## Generation workflow (per venue)

1. **Draft** ($0.12): prompt above, check layout (stage position? table density?
   bar side? ceiling feel?). Screenshot for reference.
2. **Iterate drafts** ($0.12 each): adjust what failed. Max 3 drafts ($0.36).
3. **HQ winner** ($1.20): full quality on best layout.
4. **Verify in viewer**: orbit 360°, check far-wall quality, sightlines from
   audience POV, table readability. Cameras stay within 5m — mush beyond is OK.
5. **Export .spz** (free): ~30MB → R2 → Spark viewer embeds.

**Total per venue: ~$1.50.** Three venues (cellar + concert + library) = ~$4.50.
The permanent set for everything.
