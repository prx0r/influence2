# AgentRun × influence2 — Operations Map

*Grounded in the real system inventory. AgentRun docs: `docs/agentrun/`. Jev adapter: `pipeline/jev_openrouter.py` (live).*

---

## The real problem AgentRun solves

influence2 has 53 MCP tools, a full approval state machine, a learning loop, and a consequence runtime — but **almost nothing chains them**. Every multi-step operation is either:
- Manual MCP calls in sequence
- Buried in pipeline code with no quality gates
- Broken at a seam (grant minting TODO, severed social publish loop, starved analytics feedback)

AgentRun makes each chain an explicit, inspectable, testable workflow with typed Jev decisions at the judgment points and human gates at the consequence points.

---

## The 6 real seams AgentRun plugs into

| Seam | What it is | AgentRun node |
|---|---|---|
| `pipeline/jev_openrouter.py` | Live Jev via OpenRouter `typesafe/jev-router` | `judge`, `sift`, `pick`, `route` |
| MCP `POST /mcp` `tools/call` | 53 tools: read, dry-run, draft create | `call` |
| `effects.queue()` → `/api/review/decide` | Approval state machine (PROPOSED→APPROVED→GRANTED) | `escalate` (human gate) |
| `runtime.execute(spec, grant, executor)` | The ONE consequence syscall | `call` (grant-gated) |
| `scheduler.run_due` (systemd 5-min) | Social publish tick | `loop` (periodic) |
| `learn.record_publication` / `rate_item` / `analyze` | Learning pipeline (starved — needs snapshot writers) | `call` + `code` |

---

## Tier 1 — Fix the broken loops (highest leverage)

### 1. Analytics Snapshot Writer
**The problem:** `learn.analyze` needs `performance_snapshots` rows. Nothing writes them. The learning loop is fully built but starved.

```
loop (every 6h):
  → call (analytics.youtube_channel for each active handle)
  → code (compute deltas from last snapshot — NOT cumulative totals)
  → call (learn.record_publication snapshot write)
  → code (check if n >= 25 for power gate)
  → route (enough data → learn.analyze; not enough → sleep)
  → call (learn.analyze → strategy_weights update)
  → escalate (human reviews weight changes)
```
**Primitives:** loop + call + code + route + escalate
**Fixes:** pain point #4 (starved feedback loop), #4b (cumulative metrics bug — code node computes deltas)
**Cost:** ~$0.00/run (no Jev needed, pure code + API calls)

### 2. Grant Issuance Bridge
**The problem:** Effect tasks stop at `APPROVED_PENDING_QP`. No real Ed25519 grant is minted. Everything downstream needs hand-assembled grant dicts.

```
loop (poll effect_tasks where state=APPROVED):
  → code (read task payload, compute payload_hash)
  → call (qp.authority.Grant mint — issuer, subject, action, hash, expiry)
  → code (sign with Ed25519 key from vault)
  → call (transition task to GRANTED with grant_id)
  → report (receipt: task_id, grant_id, payload_hash)
```
**Primitives:** loop + code + call + report
**Fixes:** pain point #2 (grant minting TODO)
**Note:** This is infrastructure, not content. No Jev needed. Pure deterministic code + signing.
**Safety:** Grant only mints for tasks already APPROVED by human via `/api/review/decide`. Never auto-approves.

### 3. Social Publish Unsever
**The problem:** `queue_pack_social` calls `queue_post` without ctx → always FAIL CLOSED. Nothing successfully queues.

```
input: pack_id, compiled_variants, handles
  → code (resolve brand_slug from handle via channel_state)
  → call (mint grant for publish consequence — uses #2 bridge)
  → call (scheduler.queue_post with ctx.grant for each platform)
  → code (verify each queue returned ok)
  → escalate (human reviews queued posts → approve firing)
  → call (scheduler.run_due fires approved posts)
```
**Primitives:** code + call + escalate
**Fixes:** pain point #3 (severed publish loop)
**Safety:** Human approves each batch. `can_publish` budget/cooldown gates still enforced inside `queue_post`.

---

## Tier 2 — Analytics review pipelines (your ask)

### 4. Daily Analytics Digest
**The problem:** Analytics are pull-only + cached. No one reviews them. Anomalies go unnoticed.

```
loop (daily):
  → map (for each active channel_account):
      call (analytics.youtube_channel)
      call (yt_analytics.load_analysis for cached data)
      code (compute: views today vs 7d avg, retention delta, sub gain)
  → code (aggregate across channels → digest object)
  → Jev judge (anomaly detection: noul per channel — is this unusual?)
  → Jev route (severity: normal | watch | alert)
  → route (alert → escalate; watch → log; normal → done)
  → escalate (human reads digest with typed severity annotations)
```
**Primitives:** loop + map + call + code + judge + route + escalate
**Fixes:** pain point #12 (no monitoring), gives you the "review analytics" pipeline
**Cost:** ~$0.002/run (2-3 Jev judgments per channel)

### 5. Competitor Intelligence
**The problem:** `yt_analytics.compare_channels` exists but is manual. No competitive monitoring.

```
loop (weekly):
  → map (for each tracked competitor channel):
      call (yt.analyze → fresh pull + cache)
      code (diff against last cached: new videos, format changes, cadence shift)
  → Jev sift (which competitor moves matter? keep: noul >= 0.6)
  → agent (draft competitive briefing for material moves)
  → Jev judge (threat level: direct | adjacent | ignore)
  → escalate (human reads briefing → decides response)
```
**Primitives:** loop + map + call + code + sift + agent + judge + escalate
**Fixes:** pain point #11 (manual compare), adds competitive awareness
**Note:** Captions IP-blocked on this host — degrades to metadata-only analysis (title, views, cadence). Still useful.

### 6. Channel Health Monitor
**The problem:** `channel_state.can_publish` gates on budget/cooldown/quality, but nothing monitors whether an account is actually healthy (posting cadence, engagement trends).

```
loop (daily):
  → map (for each channel_account):
      call (analytics.youtube_channel → subs, views, videos)
      call (channel_state.list_accounts → status, posts_today, last_post)
      code (compute health score: cadence adherence, growth rate, engagement)
      Jev judge (health: healthy | degraded | critical)
  → route (critical → escalate; degraded → log; healthy → done)
  → escalate (human sees critical accounts with typed diagnosis)
```
**Primitives:** loop + map + call + code + judge + route + escalate
**Fixes:** gives you per-account health visibility across all channels

---

## Tier 3 — Content quality gates

### 7. Image QC Gate (the missing check)
**The problem:** `verifiers/image.py` QC exists (identity match, hallucination, OCR-absence) but `images_flow.generate`/`upload_batch` never calls it. Known live failure: unwanted text passes QC.

```
input: generated image path + expected prompt + slot metadata
  → call (verifiers.image.qc_identity — match score)
  → call (verifiers.image.qc_text — OCR-absence check)
  → call (verifiers.image.qc_no_hallucination)
  → Jev judge (subject correctness: does image match the SKU description?)
  → code (aggregate scores → pass/fail with reason)
  → route (all pass → queue for upload; any fail → regenerate or escalate)
  → escalate (human reviews failed images with typed diagnosis)
```
**Primitives:** call + judge + code + route + escalate
**Fixes:** pain point #6 (QC defined but not enforced), HANDOVER gate "nothing ships without OCR-absence + subject check"
**Cost:** ~$0.001 per image (1 Jev judgment)

### 8. Release Quality Gate (composite)
**The problem:** Multiple checks (brand safety, budget, content level, price resolution) happen in different systems. No single gate.

```
input: release draft (brand, channel, sku, payload)
  → parallel:
      call (catalog.level — is pack LISTABLE for this channel?)
      call (channel_state.can_publish — budget/cooldown OK?)
      code (resolve_price — catalog-only, never invent)
      Jev judge (brand safety: noul — is this payload on-brand?)
      Jev judge (title quality: score 1-5)
  → code (aggregate: all pass → ready; any fail → reject with reason)
  → route (ready → escalate; reject → escalate with failure detail)
  → escalate (human approves → transition release to APPROVED)
```
**Primitives:** parallel + call + code + judge + route + escalate
**Fixes:** pain point #5 (two parallel approval systems — this becomes THE gate)
**Cost:** ~$0.001 per release (2 Jev judgments)

### 9. Upload Preview Gate (LongHauls)
**The problem:** No preview-before-upload flow exists. YouTube method contract says "unlisted then human flips public."

```
input: video metadata + thumbnail + description
  → parallel:
      Jev judge (title quality: score)
      Jev judge (description accuracy: noul — does it match content?)
      code (check: handle present, privacy=unlisted, tags non-empty)
      code (thumbnail matches title keywords?)
  → code (aggregate → preview card object)
  → escalate (human reviews preview card → approve → upload unlisted)
  → call (YT adapter upload with privacy=unlisted)
  → report (receipt: video_id, thumbnail_path, judgments)
```
**Primitives:** parallel + judge + code + escalate + call + report
**Fixes:** the "preview before upload" you asked for
**Safety:** Upload is always unlisted. Human flips public separately.

---

## Tier 4 — Learning loop activation

### 10. Content Rating Pipeline
**The problem:** `learn.rate_item` uses Jev to rate published content but is manual. `learn.analyze` needs rated items + snapshots.

```
input: published content item (external_id, pack_id, channel)
  → call (learn.record_publication — gate: external_id + receipt_id required)
  → call (learn.rate_item — Jev ratings: novelty, brand_fit, hook_strength)
  → code (store ratings in content_features)
  → code (check if n >= 25 for this brand/channel)
  → route (enough → learn.analyze; not enough → accumulate)
  → call (learn.analyze → strategy_weights)
  → escalate (human reviews weight changes)
```
**Primitives:** call + code + route + escalate
**Fixes:** pain point #4 (starved loop) + #12 (no producers)
**Note:** This is the pipeline that makes the learning loop actually learn. Jev rates each piece; weights update from real data.

### 11. Weight Calibration
**The problem:** Handover gap #1: "weights asserted, not fitted." Battle weights are hardcoded, not learned.

```
input: ~20 judged battles with human ratings
  → map (for each battle: re-score with current weights via Jev)
  → code (compute calibration error: predicted vs human)
  → Jev (which weight adjustment would reduce error most?)
  → code (propose new weight vector)
  → escalate (human reviews delta → apply or reject)
```
**Primitives:** map + code + judge + escalate
**Fixes:** handover gap #1

---

## Tier 5 — Autonomous monitoring (bounded)

### 12. Anomaly Detector
```
loop (every 4h, maxIters: bounded):
  → call (yt_analytics refresh for each active channel)
  → code (detect outliers: view spike > 2σ, retention drop, sub gain)
  → route (no anomaly → sleep; anomaly → investigate)
  → Jev (classify cause: content_hit | algorithm | external | unknown)
  → agent (draft response action: double_down | pivot | monitor | alert_human)
  → escalate (always — human decides capital allocation)
```
**Safety:** Never acts without human on anything consequential. Surfaces typed diagnoses so the human decision is fast.

### 13. Supplier Chase Loop
```
loop (weekly):
  → call (suppliers.quiet(days=14) → chase list)
  → map (for each quiet supplier):
      call (suppliers.thread → last email status)
      code (check: are we waiting on them or on us?)
      route (waiting on them → draft follow-up; waiting on us → flag)
  → agent (draft follow-up email for each waiting-on-them supplier)
  → escalate (human approves each email → send)
```
**Fixes:** pain point (suppliers manual, chase list unused)

---

## What AgentRun does NOT replace

| System | Why it stays |
|---|---|
| `runtime.execute` + grants | Consequence authority. AgentRun orchestrates; runtime executes. |
| `effects` state machine | Human approval is the gate. AgentRun's `escalate` feeds it. |
| `channel_state.can_publish` | Budget/cooldown/quality gates. AgentRun calls it, never bypasses it. |
| `learn` statistics | Spearman, permutation p, BH FDR, power gate. AgentRun triggers; learn computes. |
| `law.acom` receipts | Content-addressed receipts. AgentRun's `report` is not a receipt. |
| `qp` authority + spend | Ed25519 grants, spend ledger, journal. AgentRun never mints grants directly. |

---

## Cost summary

| Workflow | Jev calls | Agent calls | Cost/run |
|---|---|---|---|
| Analytics Snapshot Writer | 0 | 0 | $0.00 |
| Grant Issuance Bridge | 0 | 0 | $0.00 |
| Daily Analytics Digest | 2-3/channel | 0 | ~$0.002 |
| Competitor Intelligence | 3-5 | 1 | ~$0.005 |
| Image QC Gate | 1/image | 0 | ~$0.001 |
| Release Quality Gate | 2 | 0 | ~$0.001 |
| Content Rating Pipeline | 3/item | 0 | ~$0.003 |
| **Full day (all monitors)** | ~20 | ~2 | **~$0.02** |

---

## Build order (by leverage)

| Order | Workflow | Why first |
|---|---|---|
| 1 | **Grant Issuance Bridge** (#2) | Unblocks everything downstream of APPROVED. Pure code, no Jev. |
| 2 | **Analytics Snapshot Writer** (#1) | Unblocks the learning loop. Pure code + API. |
| 3 | **Daily Analytics Digest** (#4) | First visible win. You see typed anomalies every morning. |
| 4 | **Image QC Gate** (#7) | Catches the known live failure (unwanted text). |
| 5 | **Release Quality Gate** (#8) | Single gate for all releases. |
| 6 | **Social Publish Unsever** (#3) | Needs #2 (grants) first. |
| 7 | **Content Rating Pipeline** (#10) | Makes the learning loop actually learn. |
| 8 | **Competitor Intelligence** (#5) | Weekly competitive awareness. |
| 9 | **Upload Preview Gate** (#9) | LongHauls-specific, after channel has content. |
| 10 | **Anomaly Detector** (#12) | Autonomous monitoring, after digest proves useful. |
