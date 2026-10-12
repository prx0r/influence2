/** AgentRun host for influence2 — wires DSL to real tools.
 *
 * Deps supplied to runWorkflow():
 *   runEffect → influence2 MCP tools (read-only) + runtime.execute (grant-gated)
 *   runJudge  → Jev via OpenRouter typesafe/jev-router (no TypeSafe key needed)
 *   runNode   → OpenRouter chat for agent/decide/extract steps
 *
 * Safety: this host NEVER spends, publishes, sends, or mutates.
 * Consequence paths must call runtime.execute with a grant, which
 * fails closed without human approval. escalate nodes stop the
 * workflow and return state to the dash review queue.
 */
import { execFileSync } from "node:child_process";

const MCP_URL = process.env.INFLUENCE_MCP_URL || "http://127.0.0.1:8793/mcp";
const OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions";
const JEV_MODEL = "typesafe/jev-router";
const AGENT_MODEL = process.env.AGENTRUN_AGENT_MODEL || "openai/gpt-6-luna";

function openrouterKey() {
  if (process.env.OPENROUTER_API_KEY) return process.env.OPENROUTER_API_KEY;
  try {
    const out = execFileSync(
      "agent-vault",
      ["vault", "credential", "get", "OPENROUTER_API_KEY", "--vault", "oracle"],
      { encoding: "utf8", timeout: 10000 }
    ).trim();
    if (out) return out;
  } catch {}
  throw new Error("no OPENROUTER_API_KEY in env or vault oracle");
}

async function orChat(messages, maxTokens = 800, temperature = 0) {
  const res = await fetch(OPENROUTER_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${openrouterKey()}`,
      "Content-Type": "application/json",
      "HTTP-Referer": "https://influence2.local",
      "X-Title": "influence2-agentrun",
    },
    body: JSON.stringify({
      model: AGENT_MODEL,
      messages,
      max_tokens: maxTokens,
      temperature,
    }),
  });
  if (!res.ok) throw new Error(`openrouter ${res.status}: ${(await res.text()).slice(0, 300)}`);
  const body = await res.json();
  return body.choices[0].message.content;
}

/** runEffect: dispatch `call` nodes. Tool names map to MCP tools or local ops. */
export async function runEffect(params) {
  const { node, input } = params;
  const tool = node.tool || node.via;
  if (!tool) throw new Error(`call node ${node.label} has no tool`);

  // Local ops (no MCP round-trip)
  if (tool === "local.youtube_channel_stats") {
    return await youtubeChannelStats(input.handle, input.brand);
  }
  if (tool === "local.youtube_recent_videos") {
    return await youtubeRecentVideos(input.channel_id, input.max || 10);
  }
  if (tool === "local.log_receipt") {
    return await logReceipt(input);
  }
  if (tool === "local.character_snapshot_write") {
    return await characterSnapshotWrite(input);
  }
  if (tool === "local.character_graph") {
    return await characterGraph(input.character_id);
  }
  if (tool === "local.score_videos") {
    return await scoreVideos(input.videos || []);
  }
  if (tool === "local.channel_momentum") {
    return await channelMomentum(input.daily_views || [], input.daily_subs || null);
  }
  if (tool === "local.fuse_feedback") {
    return await fuseFeedback(input);
  }
  if (tool === "local.validate_character_market") {
    return await validateCharacterMarket(input);
  }
  if (tool === "local.catalog_character_assets") {
    return await catalogCharacterAssets(input);
  }

  // Everything else → dash MCP tools/call
  const res = await fetch(MCP_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ method: "tools/call", params: { name: tool, arguments: input } }),
  });
  if (!res.ok) throw new Error(`mcp ${res.status}: ${(await res.text()).slice(0, 300)}`);
  const body = await res.json();
  if (body.error) throw new Error(`mcp tool ${tool}: ${JSON.stringify(body.error).slice(0, 300)}`);
  return body.result;
}

/** runJudge: custom Jev client over OpenRouter typesafe/jev-router.
 * Implements the JevClient.systemOne(request, options) interface.
 */
export async function runJudge(params) {
  const { label, kind, state, questions } = params;
  const stateText = typeof state === "string" ? state : JSON.stringify(state);
  const system =
    "You are a typed-question answering system (Jev/System One). " +
    "Given a STATE and QUESTIONS, answer each with the required type. " +
    'Return ONLY JSON: {"answers": {"<id>": {"type": "noul"|"choice"|"score", ...}}} ' +
    "noul → float 0-1. choice → {choice, confidence, probabilities}. " +
    "score → {score, confidence, probabilities}. No prose. No markdown.";
  const user = `STATE:\n${stateText}\n\nQUESTIONS:\n${JSON.stringify(questions)}\n\nAnswer. JSON only.`;
  const text = await orChat(
    [
      { role: "system", content: system },
      { role: "user", content: user },
    ],
    600,
    0
  );
  const raw = parseAnswers(text);
  const answers = normalizeAnswers(raw, questions);
  return { answers, label, kind };
}

/** Normalize model output to exact System One answer shapes.
 *  The router sometimes returns {type:'noul', value:0.7} instead of
 *  {type:'noul', noul:0.7}. Choice/score need probabilities maps.
 */
function normalizeAnswers(raw, questions) {
  const out = {};
  for (const [id, q] of Object.entries(questions || {})) {
    const a = raw[id];
    if (!a || typeof a !== "object") continue;
    if (q.type === "noul") {
      const p = num(a.noul ?? a.value ?? a.probability ?? a.score);
      if (p !== null) out[id] = { type: "noul", noul: clamp01(p) };
    } else if (q.type === "choice") {
      const opts = Object.keys(q.criteria || {});
      let choice = typeof a.choice === "string" ? a.choice : null;
      if (!choice && typeof a.value === "string") choice = a.value;
      if (!choice && opts.length) choice = opts[0];
      const probs = {};
      const rawProbs = a.probabilities || {};
      let sum = 0;
      for (const o of opts) {
        const v = num(rawProbs[o]) ?? 0;
        probs[o] = Math.max(0, v);
        sum += probs[o];
      }
      if (sum <= 0) {
        // model gave choice but no distribution — put mass on choice
        for (const o of opts) probs[o] = o === choice ? 1 : 0;
        sum = 1;
      } else {
        for (const o of opts) probs[o] = probs[o] / sum;
      }
      const conf = num(a.confidence) ?? (probs[choice] ?? 0);
      out[id] = { type: "choice", choice, confidence: clamp01(conf), probabilities: probs };
    } else if (q.type === "score") {
      const levels = Array.isArray(q.criteria) ? q.criteria.length : 3;
      const sc = num(a.score ?? a.value) ?? 0;
      const probs = {};
      const rawProbs = a.probabilities || {};
      let sum = 0;
      for (let i = 0; i < levels; i++) {
        const v = num(rawProbs[String(i)]) ?? 0;
        probs[String(i)] = Math.max(0, v);
        sum += probs[String(i)];
      }
      if (sum <= 0) {
        const idx = Math.round(Math.min(Math.max(sc, 0), levels - 1));
        for (let i = 0; i < levels; i++) probs[String(i)] = i === idx ? 1 : 0;
        sum = 1;
      } else {
        for (let i = 0; i < levels; i++) probs[String(i)] /= sum;
      }
      out[id] = { type: "score", score: sc, confidence: clamp01(num(a.confidence) ?? 0.5), probabilities: probs };
    }
  }
  return out;
}

function num(v) {
  const n = typeof v === "string" ? parseFloat(v) : v;
  return typeof n === "number" && isFinite(n) ? n : null;
}
function clamp01(v) {
  return Math.min(1, Math.max(0, v));
}

function parseAnswers(text) {
  let t = text.trim();
  if (t.startsWith("```")) {
    const parts = t.split("```");
    t = (parts[1] || parts[0]).replace(/^json/, "").trim();
  }
  const start = t.indexOf("{");
  if (start === -1) throw new Error(`no JSON in judge response: ${t.slice(0, 200)}`);
  let depth = 0;
  for (let i = start; i < t.length; i++) {
    if (t[i] === "{") depth++;
    else if (t[i] === "}") {
      depth--;
      if (depth === 0) {
        const obj = JSON.parse(t.slice(start, i + 1));
        return obj.answers || obj;
      }
    }
  }
  throw new Error(`unbalanced JSON: ${t.slice(0, 200)}`);
}

/** runNode: agent/decide/extract via OpenRouter chat with schema constraint. */
export async function runNode(params) {
  const { kind, label, system, user, schema } = params;
  const sysText = (system || []).join("\n");
  const prompt =
    `${sysText}\n\nINPUT (JSON):\n${user}\n\n` +
    `Return your answer as JSON matching this schema:\n${JSON.stringify(schema)}\n` +
    `JSON only. No prose.`;
  const text = await orChat([{ role: "user", content: prompt }], 1500, 0.2);
  return parseAnswers(text);
}

// --- local ops (direct pipeline calls, no MCP round-trip) ---

async function youtubeChannelStats(handle, brand) {
  // test mode: handle "test-<brand>" aggregates seeded learn tables
  if ((handle || "").startsWith("test-")) {
    const vids = await testVideos(handle.slice(5), 50);
    const vs = vids.videos || [];
    const views = vs.reduce((a, v) => a + (v.views || 0), 0);
    return {
      ok: true, channel_id: `test-${handle.slice(5)}`, title: `Test: ${handle}`,
      subs: 1000, views, videos: vs.length, test_mode: true,
    };
  }
  const key = youtubeKey();
  const url = `https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics&forHandle=${encodeURIComponent(
    (handle || "").replace(/^@/, "")
  )}&key=${key}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`youtube api ${res.status}`);
  const body = await res.json();
  const item = (body.items || [])[0];
  if (!item) return { ok: false, reason: "channel not found" };
  return {
    ok: true,
    channel_id: item.id,
    title: item.snippet?.title,
    subs: parseInt(item.statistics?.subscriberCount || "0"),
    views: parseInt(item.statistics?.viewCount || "0"),
    videos: parseInt(item.statistics?.videoCount || "0"),
  };
}

async function youtubeRecentVideos(channelId, max) {
  // test mode: channel_id "test-<brand>" reads seeded learn tables
  if ((channelId || "").startsWith("test-")) {
    return await testVideos(channelId.slice(5), max);
  }
  const key = youtubeKey();
  const url =
    `https://www.googleapis.com/youtube/v3/search?part=snippet&channelId=${channelId}` +
    `&order=date&type=video&maxResults=${max}&key=${key}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`youtube api ${res.status}`);
  const body = await res.json();
  const videos = [];
  for (const item of body.items || []) {
    const vid = item.id?.videoId;
    if (!vid) continue;
    const st = await videoStats(vid, key);
    videos.push({
      id: vid,
      title: item.snippet?.title,
      published: item.snippet?.publishedAt,
      views: st.views,
      likes: st.likes,
      comments: st.comments,
    });
  }
  return { ok: true, videos };
}

async function videoStats(videoId, key) {
  const url = `https://www.googleapis.com/youtube/v3/videos?part=statistics&id=${videoId}&key=${key}`;
  const res = await fetch(url);
  if (!res.ok) return { views: 0, likes: 0, comments: 0 };
  const item = (await res.json()).items?.[0];
  const s = item?.statistics || {};
  return {
    views: parseInt(s.viewCount || "0"),
    likes: parseInt(s.likeCount || "0"),
    comments: parseInt(s.commentCount || "0"),
  };
}

/** Character asset catalog + product proposals for commerce. */
async function catalogCharacterAssets(input) {
  const { execFileSync: ef } = await import("node:child_process");
  const script = `
import json, sys
sys.path.insert(0, "/root/influence2")
from pipeline import character_commerce as _cc
inp = json.loads(sys.argv[1])
print(json.dumps(_cc.propose_products(
    inp.get("character_id", ""),
    inp.get("character_name", ""),
    int(inp.get("max_products") or 5))))
`;
  const out = ef("python3", ["-c", script, JSON.stringify(input)],
    { encoding: "utf8", timeout: 30000 });
  return JSON.parse(out);
}

/** Character market validation — AvatarChannels-informed code checks. */
async function validateCharacterMarket(input) {
  const { execFileSync: ef } = await import("node:child_process");
  const script = `
import json, sys
sys.path.insert(0, "/root/influence2")
from pipeline import character_market as _cm
inp = json.loads(sys.argv[1])
print(json.dumps(_cm.validate_character({
    "name": inp.get("name", ""), "handle": inp.get("handle", ""),
    "persona": inp.get("persona", "other"), "gender": inp.get("gender", ""),
    "age": inp.get("age", ""), "niche": inp.get("niche", ""),
    "video_length_min": inp.get("video_length_min") or 0,
    "uploads_per_week": inp.get("uploads_per_week") or 0,
    "products": inp.get("products") or []})))
`;
  const out = ef("python3", ["-c", script, JSON.stringify(input)],
    { encoding: "utf8", timeout: 30000 });
  return JSON.parse(out);
}

/** Unified feedback fusion — all sources, one call. */
async function fuseFeedback(input) {
  const { execFileSync: ef } = await import("node:child_process");
  const script = `
import json, sys
sys.path.insert(0, "/root/influence2")
from pipeline import feedback as _fb
inp = json.loads(sys.argv[1])
print(json.dumps(_fb.collect_all(
    inp.get("character_id") or "",
    inp.get("videos") or [])))
`;
  const out = ef("python3", ["-c", script, JSON.stringify(input)],
    { encoding: "utf8", timeout: 60000 });
  return JSON.parse(out);
}

/** Phoenix-style scoring + RSI momentum, via Python pipeline (one process). */
async function scoreVideos(videos) {
  const { execFileSync: ef } = await import("node:child_process");
  const script = `
import json, sys
sys.path.insert(0, "/root/influence2")
from pipeline import content_score as _cs
vids = json.loads(sys.argv[1])
print(json.dumps({"ranked": _cs.rank_videos(vids), "health": _cs.channel_health(vids)}))
`;
  const out = ef("python3", ["-c", script, JSON.stringify(videos)],
    { encoding: "utf8", timeout: 30000 });
  return JSON.parse(out);
}

async function channelMomentum(dailyViews, dailySubs) {
  const { execFileSync: ef } = await import("node:child_process");
  const script = `
import json, sys
sys.path.insert(0, "/root/influence2")
from pipeline import momentum as _m
print(json.dumps(_m.channel_momentum(json.loads(sys.argv[1]), json.loads(sys.argv[2]))))
`;
  const out = ef("python3", ["-c", script, JSON.stringify(dailyViews || []),
    JSON.stringify(dailySubs)], { encoding: "utf8", timeout: 30000 });
  return JSON.parse(out);
}

/** Test mode: read seeded videos from learn tables instead of YouTube API. */
async function testVideos(brand, max) {
  const { execFileSync: ef } = await import("node:child_process");
  const script = `
import json, sys, sqlite3
brand = sys.argv[1]
maxn = int(sys.argv[2])
db = sqlite3.connect("/root/influence2/dash/influence.db")
db.row_factory = sqlite3.Row
rows = db.execute(
    "SELECT ci.external_id, ci.title, ci.url, ps.views, ps.likes, ps.comments"
    " FROM content_items ci JOIN performance_snapshots ps ON ps.item_id=ci.id"
    " WHERE ci.brand_slug=? AND ci.channel='youtube' ORDER BY ps.views DESC LIMIT ?",
    (brand, maxn)).fetchall()
vids = [{"id": r["external_id"].replace("yt:",""), "title": r["title"],
         "url": r["url"], "views": r["views"] or 0,
         "likes": r["likes"] or 0, "comments": r["comments"] or 0} for r in rows]
print(json.dumps({"ok": True, "videos": vids, "test_mode": True}))
`;
  const out = ef("python3", ["-c", script, brand, String(max || 10)], { encoding: "utf8" });
  return JSON.parse(out);
}

function youtubeKey() {  if (process.env.YOUTUBE_API_KEY_LONGHAULS) return process.env.YOUTUBE_API_KEY_LONGHAULS;
  try {
    return execFileSync(
      "agent-vault",
      ["vault", "credential", "get", "YOUTUBE_API_KEY_LONGHAULS", "--vault", "oracle"],
      { encoding: "utf8", timeout: 10000 }
    ).trim();
  } catch {}
  throw new Error("no YOUTUBE_API_KEY_LONGHAULS in env or vault");
}

/** Read a character graph directly (local file, no MCP round-trip).
 *  Returns summary: id, name, status, seed, instance/edge counts, branches, analytics.
 */
async function characterGraph(characterId) {
  if (!characterId) return { empty: true };
  const { readFileSync } = await import("node:fs");
  const dir = process.env.CHARACTER_GRAPH_DIR || "/root/bgraph2/registry/characters";
  try {
    const raw = readFileSync(`${dir}/${characterId}.json`, "utf8");
    const g = JSON.parse(raw);
    return {
      character_id: g.character_id,
      name: g.name,
      status: g.status,
      version: g.version,
      seed: g.seed,
      instances: (g.instances || []).length,
      recent_instances: (g.instances || []).slice(-5),
      edges: (g.edges || []).length,
      branches: ((g.profile || {}).branches || []),
      analytics: g.analytics || {},
    };
  } catch {
    return { empty: true, character_id: characterId };
  }
}

async function logReceipt(input) {
  // append to dash receipts.jsonl via python (keeps one writer)
  const { execFileSync: ef } = await import("node:child_process");
  const script = `
import json, sys, time
r = {"ts": time.time(), "kind": "agentrun", **json.loads(sys.argv[1])}
open("/root/influence2/dash/receipts.jsonl", "a").write(json.dumps(r) + "\\n")
print(json.dumps({"ok": True}))
`;
  const out = ef("python3", ["-c", script, JSON.stringify(input)], { encoding: "utf8" });
  return JSON.parse(out);
}

/** Write manager direction + analytics back to the character graph.
 *  - ingest_analytics_snapshot: platform metrics → graph analytics + measured edge
 *  - direction brief → stored as a feedback edge on the graph (queryable for jev training)
 *  - performance_snapshots row → unblocks learn.analyze (currently starved)
 *  Never auto-publishes. Never mints grants. Pure write-back of manager judgment.
 */
async function characterSnapshotWrite(input) {
  const { execFileSync: ef } = await import("node:child_process");
  const script = `
import json, sys, os
sys.path.insert(0, "/root/characters/sdk")
sys.path.insert(0, "/root/influence2")
inp = json.loads(sys.argv[1])
cid = inp.get("character_id")
direction = inp.get("direction") or {}
out = {"ok": True, "writes": []}
# 1. direction brief → graph edge (manager feedback, queryable)
if cid:
    try:
        import character_sdk as sdk
        g = sdk.load_character(cid)
        ev = json.dumps({"strategy": (direction.get("strategy") or "hold"),
                         "make_more": ((direction.get("brief") or {}).get("make_more") or "")[:300],
                         "because": ((direction.get("brief") or {}).get("because") or "")[:300]})
        g.setdefault("edges", []).append({"from": cid, "rel": "directed",
            "to": "strategy:" + (direction.get("strategy") or "hold"),
            "evidence": ev[:500]})
        sdk.save_character(cid, g)
        out["writes"].append("graph-directed-edge")
    except FileNotFoundError:
        out["writes"].append("graph-missing:" + str(cid))
    except Exception as e:
        out["writes"].append("graph-error:" + str(e)[:100])
# 2. per-video snapshots → unblocks learn.analyze
try:
    from pipeline import learn as _learn
    vids = (inp.get("videos") or [])
    for v in vids:
        vid = v.get("id") or v.get("external_id") or ""
        if not vid:
            continue
        iid = _learn.ensure_item(channel="youtube",
            account=inp.get("handle") or "",
            external_id="yt:" + vid,
            title=(v.get("title") or "")[:200],
            url="https://www.youtube.com/watch?v=" + vid,
            brand_slug=inp.get("brand") or cid or "unknown",
            kind="video")
        _learn.record_snapshot(iid, window="7d",
            views=int(v.get("views") or 0),
            likes=int(v.get("likes") or 0),
            comments=int(v.get("comments") or 0))
        out["writes"].append("snapshot:" + vid)
except Exception as e:
    out["writes"].append("learn-error:" + str(e)[:100])
print(json.dumps(out))
`;
  const out = ef("python3", ["-c", script, JSON.stringify(input)], { encoding: "utf8", timeout: 30000 });
  return JSON.parse(out);
}

export const deps = { runEffect, runJudge, runNode };
