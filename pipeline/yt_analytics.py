"""YouTube channel deep analytics — transcript extraction + quantitative analysis.

Vendored (MIT, with attribution) from:
  KewkLW/yt-analytics-mcp — scripts/analyze_channel.py
  https://github.com/KewkLW/yt-analytics-mcp
  License: MIT (per package.json). No LICENSE file ships upstream;
  attribution is kept here per our rule that MIT may be vendored
  with attribution (influence AGENTS.md rule 6).

Vendored modifications (all noted, behavior preserved otherwise):
  1. run_yt_dlp: runs via `sys.executable -m yt_dlp` with PATH-binary
     fallback, so it works when /root/.local/bin is not on PATH.
  2. get_channel_videos: raises RuntimeError instead of sys.exit(1) —
     sys.exit would kill the dash server when called from MCP tools.
  3. Added cache layer (save/load/list under pipeline/runs/yt/,
     gitignored) + analyze_channel() returning a dict + compare_channels()
     side-by-side aggregates for the judge/character loop.

Read-only. No spends, no posts, no grants needed.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timedelta
from html import unescape
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = Path(os.path.dirname(_HERE)) / "pipeline" / "runs" / "yt"
# _HERE is pipeline/; runs/yt sits at pipeline/runs/yt (gitignored).

PROFANITY = {
    "shit", "damn", "hell", "ass", "crap", "bullshit", "dumbass", "badass",
    "goddamn", "bastard", "piss", "suck", "sucks", "sucking", "bitch",
    "dick", "balls", "nuts", "butt", "screw", "screwed", "freaking",
    "frickin", "freakin", "friggin",
}

CONNECTORS = ["but", "so", "because", "now", "if you", "for example", "the fact that",
              "turns out", "actually", "literally", "basically", "obviously", "honestly"]

HUMOR_CRUDE_PATTERNS = [
    r"\bballs?\b", r"\bnuts?\b", r"\bdick\b", r"\bbutt\b", r"\bass\b",
    r"\bboner\b", r"\berect\b", r"\bhard[- ]?on\b", r"\bpenis\b",
    r"\bsex\w*\b", r"\bhorn[yi]\b", r"\bnaked\b", r"\bstrip\b",
    r"\bjerk\w*\b", r"\bwank\b", r"\bpleasur\w*\b", r"\bvirgin\b",
    r"\bturn\w* (?:me |you )?on\b", r"\bsize\b.*\b(?:matter|big|small|huge)\b",
]

HUMOR_SELF_DEPRECATING = [
    r"\bi(?:'m| am) (?:stupid|dumb|idiot|wrong|bad|terrible|ugly|fat|skinny)\b",
    r"\bmy (?:stupid|dumb|ugly|fat|skinny)\b",
    r"\bi suck\b", r"\bi(?:'m| am) not (?:smart|good|great)\b",
    r"\bdon'?t judge me\b", r"\bdon'?t look at me\b",
]

HUMOR_CONFRONTATIONAL = [
    r"\byou(?:'re| are) (?:wrong|stupid|dumb|an idiot)\b",
    r"\bstop (?:doing|being|saying)\b", r"\bwhat are you doing\b",
    r"\bnobody (?:cares|asked)\b", r"\bget out of here\b",
    r"\bshut up\b", r"\bfight me\b", r"\bcome at me\b",
]

HUMOR_HYPERBOLIC = [
    r"\b(?:literally|actually) (?:die|dead|dying|kill|insane|crazy)\b",
    r"\bblow\w* (?:your |my )?mind\b", r"\bgame[ -]?changer\b",
    r"\blife[ -]?changing\b", r"\bworld.?ending\b",
    r"\bmillion\b", r"\bbillion\b",
    r"\bthe (?:best|worst|greatest|most insane)\b",
]


def run_yt_dlp(args_list):
    """Run yt-dlp via module (PATH-independent) with binary fallback."""
    try:
        cmd = [sys.executable, "-m", "yt_dlp"] + args_list
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if result.returncode == 0 or "No module named" not in (result.stderr or ""):
            return result
    except Exception:
        pass
    cmd = ["yt-dlp"] + args_list
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")


def fetch_upload_dates(channel_url, count):
    """Fetch upload dates using yt-dlp --print (fast, no full metadata)."""
    args = ["--skip-download", "--print", "%(id)s %(upload_date)s",
            "--playlist-end", str(count), channel_url + "/videos"]
    result = run_yt_dlp(args)
    dates = {}
    if result.returncode == 0 and result.stdout.strip():
        for line in result.stdout.strip().split("\n"):
            parts = line.strip().split(" ", 1)
            if len(parts) == 2 and parts[1] and parts[1] != "NA":
                dates[parts[0]] = parts[1]
    return dates


def get_channel_videos(channel_url, limit=None, max_age_days=None):
    """Fetch video list from channel using yt-dlp flat playlist."""
    args = ["--flat-playlist", "-J", channel_url + "/videos"]
    result = run_yt_dlp(args)
    if result.returncode != 0:
        # Vendored change: raise instead of sys.exit (server-safe).
        raise RuntimeError(f"channel fetch failed: {(result.stderr or '')[:200]}")

    data = json.loads(result.stdout)
    entries = data.get("entries", [])

    has_dates = any(e.get("upload_date") for e in entries[:5])

    if max_age_days and limit:
        fetch_count = min(len(entries), limit * 3, 100)
    else:
        fetch_count = limit if limit else min(len(entries), 60)
    if not has_dates and entries:
        date_map = fetch_upload_dates(channel_url, fetch_count)
        for e in entries:
            if e.get("id") in date_map:
                e["upload_date"] = date_map[e["id"]]

    cutoff = None
    if max_age_days:
        cutoff = datetime.now() - timedelta(days=max_age_days)

    videos = []
    for e in entries:
        upload_date_str = e.get("upload_date")
        upload_date = None
        if upload_date_str:
            try:
                upload_date = datetime.strptime(upload_date_str, "%Y%m%d")
            except ValueError:
                pass

        if cutoff and upload_date and upload_date < cutoff:
            continue

        vid = {
            "id": e.get("id"),
            "title": e.get("title", ""),
            "duration": e.get("duration"),
            "url": f"https://www.youtube.com/watch?v={e.get('id')}",
            "upload_date": upload_date.strftime("%Y-%m-%d") if upload_date else None,
        }
        videos.append(vid)

    if limit:
        videos = videos[:limit]

    return videos, data.get("channel", data.get("uploader", "Unknown"))


def download_transcript(video_id, work_dir):
    """Download auto-generated subtitles via yt-dlp srv1 format."""
    out_path = work_dir / f"{video_id}"
    srv1_path = work_dir / f"{video_id}.en.srv1"

    if srv1_path.exists():
        return srv1_path

    args = [
        "--write-auto-sub", "--sub-lang", "en", "--sub-format", "srv1",
        "--skip-download", "-o", str(out_path),
        f"https://www.youtube.com/watch?v={video_id}"
    ]
    run_yt_dlp(args)

    if srv1_path.exists():
        return srv1_path

    vtt_path = work_dir / f"{video_id}.en.vtt"
    if vtt_path.exists():
        return vtt_path

    return None


def try_innertube(video_id, timeout=20):
    """Fetch transcript via YouTube InnerTube API (ANDROID client).

    Pattern from neurelectra-oss/youtube-captions + rapha30/yt-youtube-transcript:
    ANDROID/IOS InnerTube clients get signed caption URLs that work without
    auth tokens, on a different path than yt-dlp/transcript-API. When those
    are IP-blocked, InnerTube often still works (separate egress reputation).

    The API key below is the public YouTube Android client key (same in every
    app install, not a secret). No auth, no cookies, no account needed.
    Returns (text, duration) or (None, None).
    """
    import urllib.request

    # Public Android client key — identical in every YouTube app install.
    ANDROID_KEY = "AIzaSyA8eiZmM1FaDVjRy-df2OKiwaqSkS6Eo4"
    PLAYER_URL = ("https://www.youtube.com/youtubei/v1/player?key="
                  + ANDROID_KEY)

    def _post(payload):
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            PLAYER_URL, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "com.google.android.youtube/19.09.37 "
                                   "(Linux; U; Android 13) gzip"},
            method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())

    # cascade: ANDROID → IOS → WEB (different client reputations)
    clients = [
        {"clientName": "ANDROID", "clientVersion": "20.10.38",
         "androidSdkVersion": 34,
         "hl": "en", "gl": "US"},
        {"clientName": "IOS", "clientVersion": "20.10.3",
         "deviceModel": "iPhone16,2",
         "hl": "en", "gl": "US"},
        {"clientName": "WEB", "clientVersion": "2.20250101.00",
         "hl": "en", "gl": "US"},
    ]
    for client in clients:
        try:
            player = _post({"videoId": video_id, "context": {"client": client}})
        except Exception:
            continue
        try:
            tracks = (player.get("captions", {})
                      .get("playerCaptionsTracklistRenderer", {})
                      .get("captionTracks", []))
        except (AttributeError, TypeError):
            tracks = []
        # prefer manual English, then auto-generated English, then any English
        def _rank(t):
            lang = (t.get("languageCode") or "")
            kind = (t.get("kind") or "")
            if lang == "en" and kind != "asr":
                return 0
            if lang.startswith("en"):
                return 1
            return 2
        for track in sorted(tracks, key=_rank):
            url = track.get("baseUrl")
            if not url:
                continue
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    xml = resp.read().decode("utf-8", errors="replace")
                text, dur = parse_caption_xml(xml)
                if text and len(text.split()) >= 20:
                    return text, dur
            except Exception:
                continue
    return None, None


def parse_caption_xml(xml):
    """Parse InnerTube caption XML (srv3/ttml/timedtext) into text + duration.

    Handles both <text start dur> (srv1) and <p t d> (timedtext format 3).
    """
    # timedtext format 3: <p t="1360" d="1680">words</p> (t/d in milliseconds)
    matches = re.findall(
        r'<p[^>]*\bt="([^"]*)"[^>]*\bd="([^"]*)"[^>]*>(.*?)</p>',
        xml, re.DOTALL)
    if matches:
        texts, max_end = [], 0.0
        for t_s, d_s, txt in matches:
            clean = re.sub(r'<[^>]+>', '', txt)
            texts.append(unescape(clean).replace("\n", " "))
            try:
                end = (float(t_s) + float(d_s)) / 1000.0
                max_end = max(max_end, end)
            except ValueError:
                pass
        text = re.sub(r'\s+', ' ', " ".join(texts)).strip()
        if len(text.split()) >= 20:
            return text, max_end if max_end > 0 else None
        return None, None
    # srv1: <text start="1.2" dur="3.4">words</text> (seconds)
    matches = re.findall(
        r'<text[^>]*start="([^"]*)"[^>]*dur="([^"]*)"[^>]*>(.*?)</text>',
        xml, re.DOTALL)
    if not matches:
        # fallback: strip all tags, keep text
        stripped = re.sub(r'<[^>]+>', ' ', xml)
        text = re.sub(r'\s+', ' ', unescape(stripped)).strip()
        return (text, None) if len(text.split()) >= 20 else (None, None)
    texts, max_end = [], 0.0
    for start_s, dur_s, txt in matches:
        clean = re.sub(r'<[^>]+>', '', txt)
        texts.append(unescape(clean).replace("\n", " "))
        try:
            end = float(start_s) + float(dur_s)
            max_end = max(max_end, end)
        except ValueError:
            pass
    text = re.sub(r'\s+', ' ', " ".join(texts)).strip()
    if len(text.split()) < 20:
        return None, None
    return text, max_end if max_end > 0 else None


def try_transcript_api(video_id):
    """Try youtube_transcript_api first (faster, no file needed).

    Supports v1.x (instance .fetch) and pre-1.0 (static .get_transcript).
    Returns (text, duration) or (None, None). IP-blocked environments
    return None cleanly — caller falls back to yt-dlp srv1.
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        fetch = getattr(YouTubeTranscriptApi, "fetch", None)
        if callable(fetch):
            try:
                t = fetch(video_id)  # static in some builds
            except TypeError:
                t = YouTubeTranscriptApi().fetch(video_id)
            snips = getattr(t, "snippets", t)
            parts, dur = [], 0.0
            for s in snips:
                if isinstance(s, dict):
                    parts.append(s.get("text", ""))
                    dur += float(s.get("duration", 0) or 0)
                else:
                    parts.append(getattr(s, "text", ""))
                    dur += float(getattr(s, "duration", 0) or 0)
            text = " ".join(parts).strip()
            return (text, dur) if text else (None, None)
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join(t["text"] for t in transcript), sum(t.get("duration", 0) for t in transcript)
    except Exception:
        return None, None


def parse_srv1(filepath):
    """Parse srv1 XML subtitle file into plain text and duration."""
    content = filepath.read_text(encoding="utf-8", errors="replace")
    matches = re.findall(r'<text[^>]*start="([^"]*)"[^>]*dur="([^"]*)"[^>]*>(.*?)</text>', content, re.DOTALL)
    if not matches:
        matches_simple = re.findall(r'<text[^>]*>(.*?)</text>', content, re.DOTALL)
        text = " ".join(unescape(m).replace("\n", " ") for m in matches_simple)
        text = re.sub(r'\s+', ' ', text).strip()
        return text, None

    texts = []
    max_end = 0.0
    for start_s, dur_s, txt in matches:
        texts.append(unescape(txt).replace("\n", " "))
        try:
            end = float(start_s) + float(dur_s)
            if end > max_end:
                max_end = end
        except ValueError:
            pass

    text = " ".join(texts)
    text = re.sub(r'\s+', ' ', text).strip()
    return text, max_end if max_end > 0 else None


def parse_vtt(filepath):
    """Parse VTT subtitle file into plain text."""
    content = filepath.read_text(encoding="utf-8", errors="replace")
    lines = content.split("\n")
    texts = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
            continue
        if re.match(r'^\d{2}:\d{2}', line) or re.match(r'^\d+$', line):
            continue
        clean = re.sub(r'<[^>]+>', '', line)
        if clean.strip():
            texts.append(clean.strip())
    text = " ".join(texts)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def analyze_text(text, duration_sec):
    """Run all quantitative analyses on a transcript."""
    words = text.lower().split()
    word_count = len(words)
    duration_min = duration_sec / 60.0 if duration_sec else None
    wpm = word_count / duration_min if duration_min and duration_min > 0 else None

    profanity_count = sum(1 for w in words if w.strip(".,!?'\"()") in PROFANITY)
    profanity_per_min = profanity_count / duration_min if duration_min else None

    connector_counts = {}
    text_lower = text.lower()
    for c in CONNECTORS:
        count = len(re.findall(r'\b' + re.escape(c) + r'\b', text_lower))
        if count > 0:
            connector_counts[c] = round(count / (word_count / 1000), 1) if word_count > 0 else 0

    humor = {"crude_sexual": 0, "self_deprecating": 0, "confrontational": 0, "hyperbolic": 0, "absurd": 0}
    for pat in HUMOR_CRUDE_PATTERNS:
        humor["crude_sexual"] += len(re.findall(pat, text_lower))
    for pat in HUMOR_SELF_DEPRECATING:
        humor["self_deprecating"] += len(re.findall(pat, text_lower))
    for pat in HUMOR_CONFRONTATIONAL:
        humor["confrontational"] += len(re.findall(pat, text_lower))
    for pat in HUMOR_HYPERBOLIC:
        humor["hyperbolic"] += len(re.findall(pat, text_lower))

    sentences = re.split(r'[.!?]+', text)
    avg_sentence_len = sum(len(s.split()) for s in sentences if s.strip()) / max(len([s for s in sentences if s.strip()]), 1)

    return {
        "word_count": word_count,
        "duration_sec": round(duration_sec, 1) if duration_sec else None,
        "duration_min": round(duration_min, 1) if duration_min else None,
        "wpm": round(wpm, 1) if wpm else None,
        "profanity_count": profanity_count,
        "profanity_per_min": round(profanity_per_min, 2) if profanity_per_min else None,
        "connectors_per_1k": connector_counts,
        "humor_counts": humor,
        "avg_sentence_words": round(avg_sentence_len, 1),
    }


def analyze_title(title):
    """Analyze a video title for formula patterns."""
    caps_words = len(re.findall(r'\b[A-Z]{2,}\b', title))
    has_exclamation = "!" in title
    has_parenthetical = bool(re.search(r'\(.*?\)', title))
    has_pipe = "|" in title
    has_question = "?" in title
    word_count = len(title.split())

    return {
        "title": title,
        "word_count": word_count,
        "caps_words": caps_words,
        "has_exclamation": has_exclamation,
        "has_parenthetical": has_parenthetical,
        "has_pipe": has_pipe,
        "has_question": has_question,
    }


def compute_posting_schedule(results):
    """Analyze posting frequency and day-of-week distribution."""
    dates = []
    for r in results:
        d = r.get("upload_date")
        if d:
            try:
                dates.append(datetime.strptime(d, "%Y-%m-%d"))
            except ValueError:
                pass

    if len(dates) < 2:
        return None

    dates.sort()

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    day_counts = {d: 0 for d in day_names}
    for d in dates:
        day_counts[day_names[d.weekday()]] += 1

    gaps = []
    for i in range(1, len(dates)):
        gaps.append((dates[i] - dates[i - 1]).days)

    monthly = Counter()
    for d in dates:
        monthly[d.strftime("%Y-%m")] += 1

    months_sorted = sorted(monthly.keys())
    monthly_data = [{"month": m, "count": monthly[m]} for m in months_sorted]

    span_days = (dates[-1] - dates[0]).days or 1
    videos_per_week = len(dates) / (span_days / 7.0)
    videos_per_month = len(dates) / (span_days / 30.0)

    return {
        "total_videos_with_dates": len(dates),
        "date_range": {"start": dates[0].strftime("%Y-%m-%d"), "end": dates[-1].strftime("%Y-%m-%d")},
        "span_days": span_days,
        "avg_days_between_posts": round(sum(gaps) / len(gaps), 1),
        "median_days_between_posts": round(sorted(gaps)[len(gaps) // 2], 1),
        "min_gap_days": min(gaps),
        "max_gap_days": max(gaps),
        "videos_per_week": round(videos_per_week, 2),
        "videos_per_month": round(videos_per_month, 1),
        "day_of_week": day_counts,
        "monthly_activity": monthly_data,
    }


def aggregate(results):
    """Compute aggregate stats across all analyzed videos."""
    valid = [r for r in results if r["analysis"]["wpm"] is not None]
    if not valid:
        return {}

    wpms = [r["analysis"]["wpm"] for r in valid]
    durations = [r["analysis"]["duration_min"] for r in valid if r["analysis"]["duration_min"]]
    word_counts = [r["analysis"]["word_count"] for r in valid]
    prof_rates = [r["analysis"]["profanity_per_min"] for r in valid if r["analysis"]["profanity_per_min"] is not None]

    total_humor = Counter()
    for r in valid:
        for k, v in r["analysis"]["humor_counts"].items():
            total_humor[k] += v

    all_connectors = Counter()
    for r in valid:
        for k, v in r["analysis"]["connectors_per_1k"].items():
            all_connectors[k] += v
    avg_connectors = {k: round(v / len(valid), 1) for k, v in all_connectors.items()}
    avg_connectors = dict(sorted(avg_connectors.items(), key=lambda x: -x[1]))

    title_analyses = [r["title_analysis"] for r in results if "title_analysis" in r]
    avg_caps = sum(t["caps_words"] for t in title_analyses) / max(len(title_analyses), 1)
    pct_exclamation = sum(1 for t in title_analyses if t["has_exclamation"]) / max(len(title_analyses), 1) * 100
    pct_parenthetical = sum(1 for t in title_analyses if t["has_parenthetical"]) / max(len(title_analyses), 1) * 100

    posting_schedule = compute_posting_schedule(results)

    return {
        "video_count": len(results),
        "analyzed_count": len(valid),
        "total_words": sum(word_counts),
        "total_duration_min": round(sum(durations), 1) if durations else None,
        "avg_wpm": round(sum(wpms) / len(wpms), 1),
        "median_wpm": round(sorted(wpms)[len(wpms) // 2], 1),
        "min_wpm": round(min(wpms), 1),
        "max_wpm": round(max(wpms), 1),
        "avg_duration_min": round(sum(durations) / len(durations), 1) if durations else None,
        "median_duration_min": round(sorted(durations)[len(durations) // 2], 1) if durations else None,
        "avg_words_per_video": round(sum(word_counts) / len(word_counts)),
        "avg_profanity_per_min": round(sum(prof_rates) / len(prof_rates), 2) if prof_rates else None,
        "total_profanity": sum(r["analysis"]["profanity_count"] for r in valid),
        "humor_totals": dict(total_humor),
        "avg_connectors_per_1k": avg_connectors,
        "title_formula": {
            "avg_caps_words": round(avg_caps, 1),
            "pct_exclamation": round(pct_exclamation),
            "pct_parenthetical": round(pct_parenthetical),
        },
        "posting_schedule": posting_schedule,
    }


# --- Cache + orchestration layer (added for influence2; not upstream) ---

def slug_of(channel: str) -> str:
    """Cache slug for a channel URL or @handle."""
    s = (channel or "unknown").strip().lower()
    s = re.sub(r'^https?://(www\.)?youtube\.com/', '', s).strip('/')
    out, prev = [], "-"
    for ch in s:
        if ch.isalnum():
            out.append(ch)
            prev = ch
        elif prev != "-":
            out.append("-")
            prev = "-"
    return "".join(out).strip("-") or "unknown"


def _cache_path(slug: str) -> Path:
    return CACHE_DIR / f"{slug}.json"


def save_analysis(slug: str, output: dict) -> str:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    p = _cache_path(slug)
    p.write_text(json.dumps(output, indent=1, ensure_ascii=False))
    return str(p)


def load_analysis(slug: str) -> dict | None:
    p = _cache_path(slug)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def list_analyses() -> list[dict]:
    if not CACHE_DIR.exists():
        return []
    out = []
    for p in sorted(CACHE_DIR.glob("*.json")):
        try:
            d = json.loads(p.read_text())
            agg = d.get("aggregate") or {}
            out.append({"slug": p.stem,
                        "channel": d.get("channel"),
                        "analyzed_count": agg.get("analyzed_count"),
                        "avg_wpm": agg.get("avg_wpm")})
        except Exception:
            out.append({"slug": p.stem, "error": "unreadable"})
    return out


def analyze_channel(channel: str, limit: int = 10, sleep: float = 0.5,
                    max_age_days: int | None = None, work_dir: str | None = None) -> dict:
    """Analyze a channel, cache the JSON, return the full output dict.

    Raises RuntimeError on fetch failure (server-safe, no sys.exit).
    """
    channel_url = (channel or "").strip()
    if channel_url.startswith("@"):
        channel_url = f"https://www.youtube.com/{channel_url}"
    elif not channel_url.startswith("http"):
        channel_url = f"https://www.youtube.com/@{channel_url}"

    wd = Path(work_dir) if work_dir else (CACHE_DIR / "work")
    wd.mkdir(parents=True, exist_ok=True)

    videos, channel_name = get_channel_videos(channel_url, limit, max_age_days)

    results = []
    failed = []
    for i, video in enumerate(videos):
        vid_id = video["id"]
        title = video["title"]
        text = None
        duration = video.get("duration")

        t, api_dur = try_transcript_api(vid_id)
        if t:
            text = t
            if api_dur and api_dur > 0:
                duration = api_dur

        if not text:
            # InnerTube fallback: different egress path than yt-dlp/API.
            # Often works when both are IP-blocked (separate reputation).
            t, it_dur = try_innertube(vid_id)
            if t:
                text = t
                if it_dur and it_dur > 0:
                    duration = it_dur

        if not text:
            sub_path = download_transcript(vid_id, wd)
            if sub_path and sub_path.exists():
                if sub_path.suffix == ".srv1":
                    text, parsed_dur = parse_srv1(sub_path)
                    if parsed_dur:
                        duration = parsed_dur
                else:
                    text = parse_vtt(sub_path)

        if not text or len(text.split()) < 20:
            failed.append({"id": vid_id, "title": title, "reason": "no transcript"})
            continue

        if not duration or duration <= 0:
            duration = len(text.split()) / 200.0 * 60

        results.append({
            "id": vid_id,
            "title": title,
            "url": video["url"],
            "upload_date": video.get("upload_date"),
            "analysis": analyze_text(text, duration),
            "title_analysis": analyze_title(title),
        })

        if i < len(videos) - 1:
            time.sleep(sleep)

    output = {
        "channel": channel_name,
        "channel_url": channel_url,
        "aggregate": aggregate(results),
        "videos": sorted(results, key=lambda r: -(r["analysis"]["wpm"] or 0)),
        "failed": failed,
    }
    save_analysis(slug_of(channel), output)
    return output


def compare_channels(channels: list[str]) -> dict:
    """Side-by-side aggregates for cached (or freshly missing) channels.

    Only compares channels already cached — never triggers network.
    Returns {compared: [...], missing: [...]}.
    """
    compared, missing = [], []
    for ch in channels or []:
        d = load_analysis(slug_of(ch))
        if not d:
            missing.append(ch)
            continue
        agg = d.get("aggregate") or {}
        compared.append({
            "channel": d.get("channel"),
            "slug": slug_of(ch),
            "analyzed_count": agg.get("analyzed_count"),
            "avg_wpm": agg.get("avg_wpm"),
            "median_wpm": agg.get("median_wpm"),
            "avg_duration_min": agg.get("avg_duration_min"),
            "avg_profanity_per_min": agg.get("avg_profanity_per_min"),
            "humor_totals": agg.get("humor_totals"),
            "avg_connectors_per_1k": dict(list((agg.get("avg_connectors_per_1k") or {}).items())[:6]),
            "title_formula": agg.get("title_formula"),
            "videos_per_week": (agg.get("posting_schedule") or {}).get("videos_per_week"),
        })
    return {"compared": compared, "missing": missing}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="YouTube Channel Deep Analytics (influence2 vendor)")
    parser.add_argument("channel", help="Channel URL or @handle")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--sleep", type=float, default=0.5)
    parser.add_argument("--max-age-days", type=int, default=None)
    args = parser.parse_args()
    print(json.dumps(analyze_channel(args.channel, args.limit, args.sleep, args.max_age_days),
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
