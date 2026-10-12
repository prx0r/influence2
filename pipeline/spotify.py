"""Spotify outlet — analytics collector + video/audio upload prep.

Two doors (see session notes):
  PODCAST (free): Spotify for Creators — RSS everywhere, Partner Program revenue.
    Upload: dashboard (manual) or unofficial API (reverse-engineered, careful).
    Analytics: Web API (OAuth) or Creators dashboard export.
  MUSIC ($24.99/yr DistroKid): Spotify/Apple/TikTok placement for original songs.

This module:
  - Public Web API (client credentials): search, episode/show metadata. No user auth.
  - Private analytics: STUB until show-owner OAuth (documented below).
  - Video/audio prep: MP3/MP4 + metadata packages ready for upload.
  - Feedback source: plays + completion → fused signals (weight 0.08).

OAuth setup (human, one-time):
  1. https://developer.spotify.com/dashboard → Create app
  2. Add redirect URI, note client_id + client_secret
  3. Vault: SPOTIFY_CLIENT_ID + SPOTIFY_CLIENT_SECRET (oracle)
  4. For private show stats: owner OAuth flow → SPOTIFY_REFRESH_TOKEN
     (scopes: user-read-playback-position for resume data;
      show stats via Creators dashboard export until API covers it)

Pure stdlib (urllib). No dependencies.
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import urllib.parse
import urllib.request

TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE = "https://api.spotify.com/v1"

# Spotify podcast specs (for upload prep validation)
AUDIO_SPECS = {"formats": ["mp3", "m4a", "wav"], "channels": ["mono", "stereo"],
               "note": "no file size limit, larger = slower processing"}
VIDEO_SPECS = {"note": "upload video episode, delivered as video on Spotify, "
                       "audio via RSS elsewhere. 350M streamed video podcasts last year."}


def _vault(key: str) -> str:
    if os.environ.get(key):
        return os.environ[key]
    try:
        r = subprocess.run(
            ["agent-vault", "vault", "credential", "get", key,
             "--vault", "oracle"],
            capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except Exception:
        return ""


def _app_token() -> str:
    """Client-credentials token (public catalog only, no user data)."""
    cid = _vault("SPOTIFY_CLIENT_ID")
    sec = _vault("SPOTIFY_CLIENT_SECRET")
    if not (cid and sec):
        raise RuntimeError("no SPOTIFY_CLIENT_ID/SECRET in env or vault")
    basic = base64.b64encode(f"{cid}:{sec}".encode()).decode()
    data = urllib.parse.urlencode(
        {"grant_type": "client_credentials"}).encode()
    req = urllib.request.Request(
        TOKEN_URL, data=data,
        headers={"Authorization": f"Basic {basic}",
                 "Content-Type": "application/x-www-form-urlencoded"},
        method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())["access_token"]


def _get(path: str, token: str, params: dict | None = None) -> dict:
    url = API_BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def search_podcasts(query: str, limit: int = 10) -> list[dict]:
    """Search Spotify podcast catalog (public, no user auth)."""
    token = _app_token()
    d = _get("/search", token, {"q": query, "type": "show",
                                "limit": max(1, min(limit, 50))})
    out = []
    for s in (d.get("shows") or {}).get("items", []):
        out.append({"id": s.get("id"), "name": s.get("name"),
                    "publisher": s.get("publisher"),
                    "total_episodes": s.get("total_episodes")})
    return out


def get_show_episodes(show_id: str, limit: int = 20) -> list[dict]:
    """List episodes with durations (public metadata, no play counts).

    Play counts are NOT in the public API — those need show-owner OAuth
    or Creators dashboard export. This gives catalog structure for
    competitive research (format, cadence, duration).
    """
    token = _app_token()
    d = _get(f"/shows/{show_id}/episodes", token,
             {"limit": max(1, min(limit, 50))})
    out = []
    for e in d.get("items", []):
        out.append({"id": e.get("id"), "name": e.get("name"),
                    "duration_ms": e.get("duration_ms"),
                    "duration_min": round((e.get("duration_ms") or 0) / 60000, 1),
                    "release_date": e.get("release_date"),
                    "explicit": e.get("explicit", False)})
    return out


def show_analytics(show_id: str) -> dict:
    """Private show stats (plays, retention, audience). STUB — needs owner OAuth.

    Returns {"ok": False, "next": <human steps>} until SPOTIFY_REFRESH_TOKEN
    exists. When wired: plays (30s+), completion rate, follower growth,
    discovery sources → fused as spotify.stats (weight 0.08).
    """
    refresh = _vault("SPOTIFY_REFRESH_TOKEN")
    if not refresh:
        return {"ok": False,
                "reason": "no SPOTIFY_REFRESH_TOKEN",
                "next": "owner OAuth flow (Spotify dashboard → authorize → "
                        "seal refresh token to vault oracle as SPOTIFY_REFRESH_TOKEN). "
                        "Until then: export CSV from Creators dashboard → "
                        "ingest via ingest_dashboard_csv()."}
    # TODO: refresh → access token → creators-graph.spotify.com queries
    # (see higuchiki/spotify-for-creators-api for endpoint shapes)
    return {"ok": False, "reason": "refresh token present, queries not yet wired",
            "next": "implement creators-graph queries (see module docstring)"}


def ingest_dashboard_csv(path: str, show_id: str = "") -> dict:
    """Ingest Creators dashboard CSV export → episode stats.

    Manual path until OAuth lands: owner exports from dashboard,
    drops CSV here, we parse plays/completion into feedback signals.
    Expected columns (flexible): episode, plays, completion_%, followers_gained.
    """
    import csv
    episodes = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        cols = {c.lower().strip(): c for c in (reader.fieldnames or [])}
        def _get(row, *names):
            for n in names:
                if n in cols:
                    return row[cols[n]]
            return ""
        for row in reader:
            try:
                episodes.append({
                    "name": _get(row, "episode", "title", "name"),
                    "plays": int(float(_get(row, "plays", "streams",
                                            "listens") or 0)),
                    "completion": float(_get(row, "completion", "completion_%",
                                             "completion_rate") or 0),
                    "followers": int(float(_get(row, "followers",
                                                "followers_gained") or 0)),
                })
            except (ValueError, TypeError):
                continue
    return {"ok": True, "show_id": show_id, "episodes": episodes,
            "count": len(episodes)}


def prep_audio_package(audio_path: str, title: str, description: str = "",
                       show: str = "") -> dict:
    """Validate + package audio for Spotify podcast upload.

    Checks format, returns upload-ready manifest. Actual upload is
    dashboard (manual) until unofficial API is vetted.
    Returns {ok, package} or {ok: False, reason}.
    """
    ext = os.path.splitext(audio_path)[1].lower().lstrip(".")
    if ext not in AUDIO_SPECS["formats"]:
        return {"ok": False,
                "reason": f".{ext} not accepted (need mp3/m4a/wav)"}
    if not os.path.exists(audio_path):
        return {"ok": False, "reason": f"file not found: {audio_path}"}
    size_mb = round(os.path.getsize(audio_path) / 1024 / 1024, 1)
    return {"ok": True, "package": {
        "file": audio_path, "format": ext, "size_mb": size_mb,
        "title": title[:200], "description": description[:4000],
        "show": show,
        "next": "upload via Spotify for Creators dashboard → New episode. "
                "RSS distributes to Apple/Amazon/etc automatically."}}


def prep_video_package(video_path: str, title: str, description: str = "",
                       show: str = "") -> dict:
    """Validate + package video for Spotify video podcast + YouTube.

    Same MP4 serves both: Spotify video podcast (Premium revenue) +
    YouTube upload (ad revenue). Validates existence + metadata completeness.
    Returns {ok, package} with per-platform next steps.
    """
    ext = os.path.splitext(video_path)[1].lower()
    if ext not in (".mp4", ".mov"):
        return {"ok": False,
                "reason": f"{ext} not ideal (use .mp4 h264+AAC for both platforms)"}
    if not os.path.exists(video_path):
        return {"ok": False, "reason": f"file not found: {video_path}"}
    size_mb = round(os.path.getsize(video_path) / 1024 / 1024, 1)
    return {"ok": True, "package": {
        "file": video_path, "size_mb": size_mb,
        "title": title[:100], "description": description[:5000],
        "show": show,
        "spotify_next": "upload via Creators dashboard → New episode → "
                        "video file. Delivered as video on Spotify, "
                        "audio via RSS elsewhere.",
        "youtube_next": "upload via YT adapter (needs OAuth: "
                        "YOUTUBE_CLIENT_ID/SECRET/REFRESH_TOKEN in vault). "
                        "Privacy: unlisted first, human flips public."}}


def youtube_upload_status() -> dict:
    """Check YouTube upload readiness (OAuth, not just API key)."""
    cid = _vault("YOUTUBE_CLIENT_ID")
    sec = _vault("YOUTUBE_CLIENT_SECRET")
    ref = _vault("YOUTUBE_REFRESH_TOKEN")
    missing = [k for k, v in
               [("YOUTUBE_CLIENT_ID", cid),
                ("YOUTUBE_CLIENT_SECRET", sec),
                ("YOUTUBE_REFRESH_TOKEN", ref)] if not v]
    if missing:
        return {"ok": False, "missing": missing,
                "has_api_key": bool(_vault("YOUTUBE_API_KEY_LONGHAULS")),
                "note": "API key is read-only (stats). Upload needs OAuth app: "
                        "Google Cloud Console → YouTube Data API → OAuth client → "
                        "authorize → seal 3 keys to vault. Publish app to avoid "
                        "7-day testing-token death.",
                "adapter": "stevejobless/publisher/adapters/youtube.py "
                           "(resumable upload, already built)"}
    return {"ok": True, "adapter": "stevejobless/publisher/adapters/youtube.py"}
