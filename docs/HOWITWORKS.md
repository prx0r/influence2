# How It Works — AgentRun Brand Manager Stack

*Last verified: 2026-10-12. All workflows live-tested. 35 tests green.*

---

## The idea in one paragraph

**influence2 is the manager. Characters are the performers. The audience votes with views.**
The manager pulls analytics, scores content with open-source algorithms, asks Jev what's
working, tells the performer "make more X because Y", and gates everything behind human
approval. The performer generates comedy. The loop repeats. Nobody auto-publishes.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CHARACTERS (brain)                        │
│  /root/characters — audition → battle → winner → TTS → MP4       │
│  /root/bgraph2 — character graph (seed, instances, edges)        │
│  Never publishes. Never fetches analytics. Propose drafts only. │
└────────────────────────────┬────────────────────────────────────┘
                             │ propose_post → {posted: False, draft}
                             │ seed_state ← recent instances + ratings
┌────────────────────────────▼────────────────────────────────────┐
│                     INFLUENCE2 (manager)                         │
│                                                                  │
│  AgentRun workflows (workflows/*.json, run via workflows/run.mjs)│
│    analytics_review → digest (auto, read-only)                   │
│    content_decide   → brief in-character voice (human approves)  │
│    release_gate     → PASS/FAIL (human approves)                 │
│    character_direct → "make more X because Y" (human approves)   │
│                                                                  │
│  Host (dash/agentrun_host.mjs)                                   │
│    runEffect → MCP tools + local ops (YT API, graph, scoring)    │
│    runJudge → Jev via OpenRouter typesafe/jev-router             │
│    runNode  → OpenRouter chat for agent steps                    │
│                                                                  │
│  Scoring (pipeline/)                                             │
│    content_score.py → Phoenix-style weighted scorer (X algo)     │
│    momentum.py      → RSI + EMA + divergence (Wilder, 1978)      │
│    jev_openrouter.py → Python Jev client                         │
│    learn.py         → content_items + snapshots + weights         │
│                                                                  │
│  Gates (never bypassed)                                          │
│    escalate nodes → human review queue                           │
│    runtime.execute → grant-gated consequences                    │
│    channel_state.can_publish → budget/cooldown/quality           │
└────────────────────────────┬────────────────────────────────────┘
                             │ receipts → dash/receipts.jsonl
                             │ snapshots → learn tables
                             │ directed edges → character graph
┌────────────────────────────▼────────────────────────────────────┐
│                         YOUTUBE (audience)                       │
│  Data API v3: channel stats, video metrics                       │
│  LongHauls: @longhauls / UCrntJs4IgQNEPUszDgDoXBg               │
└──────────────────────────────────────────────────────────────────┘
```

---

## The four workflows

### 1. analytics_review — "what happened?"

```
input: {brand, handle, channel_id}
  │
  ├─→ call local.youtube_channel_stats → {subs, views, videos}
  ├─→ call local.youtube_recent_videos → [{id, title, views, likes, comments}]
  ├─→ code compute-deltas → {avg_recent_views, top_video}
  ├─→ call local.score_videos (Phoenix) → {ranked, health}
  ├─→ judge detect-anomaly (Jev) → {is_anomaly, severity}
  ├─→ code build-digest → {digest}
  └─→ call local.log_receipt → receipts.jsonl
output: digest (status: complete, no human needed — read-only)
```

**Test mode:** `handle: "test-<brand>"` and `channel_id: "test-<brand>"` read from
seeded learn tables instead of YouTube API. Used by `scripts/seed_test_data.py`.

### 2. content_decide — "what should we make?"

```
input: {brand, character_id ("" for non-character), handle, digest, existing_titles}
  │
  ├─→ judge assess-strategy (Jev) → {winning_theme, has_enough_data}
  ├─→ call local.character_graph → {seed, voice, recent_instances}
  │     (returns {empty: true} if character_id is "" — graceful)
  ├─→ agent draft-briefs → {briefs: [{title, angle, format, why}]} (3x)
  │     (instructions inject character voice when present)
  ├─→ sift filter-brand-fit (Jev, keep on_brand=yes) → {items}
  ├─→ pick pick-winner (allowNone) → {item, index}
  ├─→ code build-decision → {decision}
  │     (falls back to candidates[0] if sift emptied everything)
  ├─→ call local.log_receipt
  └─→ escalate human-approves-brief (ALWAYS — needs_review: true)
output: decision (status: escalated — human picks the brief)
```

### 3. release_gate — "is this good enough to ship?"

```
input: {brand, channel, title, description, platform, handle}
  │
  ├─→ parallel:
  │     ├─→ judge check-brand-safety (Jev) → {is_safe}
  │     └─→ judge check-title-quality (Jev) → {quality: strong|adequate|weak}
  ├─→ code aggregate-verdict → {verdict: PASS|FAIL, checks, reasons}
  ├─→ call local.log_receipt
  └─→ escalate human-approves-release (ALWAYS)
output: gate (status: escalated — human approves the release)
```

PASS requires: brand_safe AND title_quality ≠ weak. Upload is always unlisted.
Human flips public separately.

### 4. character_direct — "make more X because Y"

```
input: {character_id, brand, handle, channel_id}
  │
  ├─→ call local.character_graph → {seed, instances, branches}
  ├─→ call local.youtube_recent_videos → performance data
  ├─→ judge assess-what-works (Jev) → {has_winners, direction_type}
  │     (thresholds: <500 views everywhere → pivot, not hold;
  │      <3 videos → hold; strong absolute numbers → double_down)
  ├─→ agent write-direction → {make_more, because, make_less, try_next, modulators}
  ├─→ code build-direction → {direction}
  ├─→ call local.character_snapshot_write:
  │     ├─→ directed edge in character graph (strategy + evidence)
  │     └─→ per-video snapshots in learn tables (unblocks learn.analyze)
  ├─→ call local.log_receipt
  └─→ escalate human-approves-direction (ALWAYS)
output: direction (status: escalated — human approves before performer sees it)
```

---

## The scoring algorithms

### Phoenix-style content scorer (`pipeline/content_score.py`)

Adapted from `xai-org/x-algorithm` (Apache 2.0). X predicts 19 engagement
probabilities; we score YouTube metrics with the observed 2026 weight hierarchy:

| Signal | Weight | Rationale |
|---|---|---|
| Comment + creator reply | +75 | X's highest observed signal (conversation) |
| Subscribe | +50 | X follow_author (strongest authority) |
| Like | +30 | X primary distribution signal |
| Share | +20 | X high-intent distribution |
| Retention >50% | +15 | X video_quality_view |
| Dwell (avg view duration) | +0.5/sec | X depth signal |
| Dislike | −15 | X negative signals |
| Retention <20% | −25 | Passive rejection penalty |

Plus: **recency decay** (7-day half-life, not X's 48h hard drop) and **format
diversity** (×0.85 per repeat format, from X's author_diversity_scorer).

Scores are **rate-based, not volume-based**. A video with 7.3% like rate
outranks one with 7.1% even with fewer views. Quality over volume.

### RSI momentum (`pipeline/momentum.py`)

Wilder's RSI (1978) on view time series:

| RSI | Meaning | Manager action |
|---|---|---|
| >70 | Overbought (viral peak) | Bank the win, prep follow-up within 48h |
| 55–70 | Bullish | Keep cadence, test adjacent formats |
| 45–55 | Neutral | Hold cadence |
| 30–45 | Bearish | Experiment, one pivot test |
| <30 | Oversold (dead) | Pivot or kill, do not feed a dead channel |

Also: bullish/bearish crosses (momentum regime change), divergence detection
(views peaking but RSI fading = weakening trend).

---

## The feedback loop (manager → performer)

```
1. Performer generates → battle winner → MP4 → published (human-gated)
2. Audience watches → views/retention/comments accumulate
3. Manager pulls → analytics_review digest (Phoenix scores + RSI)
4. Manager judges → character_direct (Jev: what's working?)
5. Manager directs → "make more X because Y" (agent writes brief)
6. Direction lands → directed edge in character graph + learn snapshots
7. Next audition → seed_state includes recent ratings + direction
8. Jev decide_instance → picks modulators informed by what performed
9. → back to 1.
```

**What the performer reads:** `seed_state()` returns philosophy + modulator_range +
recent instances (with battle_score/judge_rating). The directed edge is queryable
for Jev training. Raw analytics never enter the prompt — future agents get
`get_performance_brief`, not raw stats (per SPEC v1.4).

---

## Running it

### Prerequisites

```bash
# env (in .env, gitignored — or vault oracle)
OPENROUTER_API_KEY=...          # Jev + agent model calls
YOUTUBE_API_KEY_LONGHAULS=...   # YouTube Data API v3

# Pi extension (for /agentrun inside Pi)
pi install npm:@parcha/agentrun-pi@0.1.0-beta.2 -l
```

### Validate (no API calls)

```bash
node workflows/run.mjs --validate analytics_review
node workflows/run.mjs --validate content_decide
node workflows/run.mjs --validate release_gate
node workflows/run.mjs --validate character_direct
```

### Inspect (print graph)

```bash
node workflows/run.mjs --inspect character_direct
```

### Run live (LongHauls channel)

```bash
node --env-file=.env workflows/run.mjs analytics_review \
  '{"brand":"long-hauls","handle":"@longhauls","channel_id":"UCrntJs4IgQNEPUszDgDoXBg"}'

node --env-file=.env workflows/run.mjs release_gate \
  '{"brand":"long-hauls","channel":"youtube","title":"...","description":"...","platform":"youtube","handle":"@longhauls"}'
```

### Run with character direction (Nolan)

```bash
node --env-file=.env workflows/run.mjs character_direct \
  '{"character_id":"no_nose_nolan","brand":"long-hauls","handle":"@longhauls","channel_id":"UCrntJs4IgQNEPUszDgDoXBg"}'

node --env-file=.env workflows/run.mjs content_decide \
  '{"brand":"nolan","character_id":"no_nose_nolan","handle":"@longhauls","digest":{...},"existing_titles":[]}'
```

### Via MCP (dash)

```
agentrun.list                    → list workflows
agentrun.runs                    → recent runs from receipts
agentrun.validate                → validate without running
  args: {workflow: "analytics_review" | "content_decide" | "release_gate" | "character_direct"}
```

---

## Testing with sample data

The live LongHauls channel is empty (0 videos). Use seeded scenarios:

```bash
# seed: 5 character instances + 5 videos + learn snapshots
python3 scripts/seed_test_data.py --scenario winners  # 12.5k views, 0.82 scores → double_down
python3 scripts/seed_test_data.py --scenario mixed    # ~3k views, 0.55 scores → experiment
python3 scripts/seed_test_data.py --scenario losers   # <200 views, 0.30 scores → pivot

# run against seeded data (test- prefix reads learn tables, not YouTube API)
node --env-file=.env workflows/run.mjs character_direct \
  '{"character_id":"no_nose_nolan","brand":"long-hauls","handle":"test-long-hauls","channel_id":"test-long-hauls"}'

node --env-file=.env workflows/run.mjs analytics_review \
  '{"brand":"long-hauls","handle":"test-long-hauls","channel_id":"test-long-hauls"}'

# clean up
python3 scripts/seed_test_data.py --clear
```

**Expected results:**

| Scenario | character_direct strategy | analytics_review health |
|---|---|---|
| winners | `double_down` (cites 12.5k views, 0.85 scores) | varies (2 strong + 3 weak) |
| mixed | `experiment` | weak |
| losers | `pivot` | weak |

---

## Costs

| Operation | Cost |
|---|---|
| Jev judgment (via OpenRouter) | ~$0.0001 |
| Agent draft (1 step) | ~$0.01–0.02 |
| YouTube Data API | free (quota) |
| Phoenix scoring / RSI | $0.00 (pure Python) |
| **Full analytics_review run** | **~$0.0002** (1 Jev call) |
| **Full character_direct run** | **~$0.02** (2 Jev + 1 agent) |
| **Full day (all monitors)** | **~$0.05** |

---

## Safety rules (never violated)

1. **No auto-publish.** Every workflow that leads to consequences ends in `escalate`.
   Workflows literally cannot complete past a gate without human state.
2. **No grant minting.** The host never creates grants. `runtime.execute` fails
   closed without human-approved grants.
3. **No secret leaks.** Keys load from env/vault at call time, never logged,
   never in workflow JSON, never in receipts.
4. **Jev is advisory.** Typed judgments inform decisions; they don't execute them.
   Confidence ≠ accuracy. Thresholds are tuned on real data, not assumed.
5. **Honest degradation.** No data → strategy is `hold`, not hallucinated winners.
   IP-blocked captions → `failed: [no transcript]`, not fake transcripts.
   Empty sift → fallback to unfiltered, not crash.

---

## The feedback harness (symbiotic design)

`pipeline/feedback.py` collects every performer signal into one schema
(`FeedbackSignal {source, content_id, character_id, score_0_100, metrics}`),
then fuses them by source weight:

| Source | Weight | State | Cadence |
|---|---|---|---|
| arena.votes (Elo+Wilson) | 0.25 | live when app runs | on vote |
| pogs (laugh events) | 0.20 | live when app runs | realtime |
| watch.retention | 0.15 | live when app runs | hourly |
| feedbacks (0-3 + room) | 0.12 | live when app runs | on submit |
| youtube.stats (Phoenix) | 0.10 | live | hourly |
| battle.scores | 0.08 | live | on record |
| performance.dials | 0.05 | live (Ari sets) | on publish |
| youtube.deep | 0.03 | partial (captions blocked) | weekly |
| rewards (laugh-rate) | 0.02 | built, no producers | on event |
| instagram / tiktok / x | 0.00 | stubs (need keys) | — |

Missing sources degrade, never crash. `collect_all()` never raises.

Fusion produces per-content verdicts (hot/growing/steady/cooling/cold) and
per-character reads (by_modulator, by_operator, by_scenario, direction_hint).
`workflows/feedback_collect.json` runs this on schedule (read-only + snapshots).
`workflows/character_direct.json` consumes the fused read for direction.

---

## File map

```
workflows/
  analytics_review.json   post/video analytics → digest
  content_decide.json     digest + voice → brief (in-character)
  release_gate.json       title + description → PASS/FAIL
  character_direct.json   character + fused signals → direction
  feedback_collect.json   scheduled multi-source collection → fused read
  run.mjs                 runner (--validate, --inspect, live run)

dash/
  agentrun_host.mjs       runEffect / runJudge / runNode + 8 local ops
  mcp.py                  agentrun.list/runs/validate (+3 tools)
  agent_chat.py           agentrun tools allowlisted

pipeline/
  jev_openrouter.py       Python Jev client (OpenRouter typesafe/jev-router)
  content_score.py        Phoenix-style scorer (X algo weights)
  momentum.py             RSI + EMA + divergence
  learn.py                record_snapshot() + ensure_item()
  feedback.py             unified harness: 12 sources → fused signals

scripts/
  seed_test_data.py       winners/mixed/losers test scenarios

docs/
  HOWITWORKS.md           this file
  agentrun/               imported AgentRun docs + OPERATIONS.md
```
