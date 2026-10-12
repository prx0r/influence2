"""Timing authority — one plan drives voice, subtitles, and schedule.

Port of agent-theater subtitleVoiceTiming: a single timing computation
consumed by audio rendering, subtitle reveal, and performance timelines.
No drift between what you hear, what you read, and how long the timeline
thinks it is.

Constants tuned for comedy/sleep narration (from their battle-tested values):
  VOICE_START_MS 1200 — pre-gesture audio gate (mouth moves before sound)
  BREATH_MS 320       — pause between speakers (natural turn-taking)
  TAIL_MS 450         — audio tail after last word (reverb settle)
  DUCK_TO 0.35        — music bed level under voice
  DUCK_MS 260         — duck attack time

Pure stdlib. No network.
"""
from __future__ import annotations

import re

VOICE_START_MS = 1200
BREATH_MS = 320
TAIL_MS = 450
DUCK_TO = 0.35
DUCK_MS = 260
MUSIC_LEVEL = 0.32
CUE_LEVEL = 0.45

# avg English speech: ~150 WPM = 2.5 words/sec = 400ms/word
# slow narration (sleep): ~115 WPM = ~520ms/word
MS_PER_WORD = {"normal": 400, "slow": 520, "fast": 320}


def estimate_duration_ms(text: str, pace: str = "normal") -> int:
    """Word-count duration estimate (FastVid-style weights).

    Function words (the/a/and/of) discounted 20% (spoken faster).
    Punctuation adds pauses: period 300ms, comma 150ms, ?/! 250ms.
    """
    words = (text or "").split()
    if not words:
        return 0
    msw = MS_PER_WORD.get(pace, 400)
    func_words = {"the", "a", "an", "and", "of", "to", "in", "it",
                  "is", "you", "that", "was", "for", "on", "are"}
    total = 0.0
    for w in words:
        clean = re.sub(r"[^\w']", "", w.lower())
        total += msw * (0.8 if clean in func_words else 1.0)
        if w.endswith("."):
            total += 300
        elif w.endswith(","):
            total += 150
        elif w.endswith(("?", "!")):
            total += 250
    return int(total)


def timing_plan(text: str, voice: dict | None = None,
                pace: str = "normal") -> dict:
    """Single timing plan: duration + subtitle tokens + schedule offsets.

    voice: {age 0-1, tone 0-1, speed 0-2} (agent-theater SubtitleVoice shape).
    Returns {duration_ms, audible_ms, tokens, schedule} where schedule has
    voice_start, breath_before, tail_after for timeline assembly.
    """
    voice = voice or {}
    speed = float(voice.get("speed", 1.0) or 1.0)
    # non-linear speed map (their tuned curve)
    if speed <= 1:
        rate_mult = 1 + 0.7 * (1 - speed) if speed < 1 else 1.0
        # speed<1 = slower = longer; speed=1 → 1.0
        rate_mult = 1.0 / max(0.3, speed) if speed > 0 else 2.0
    else:
        rate_mult = 1.0 / (1.7 + 0.3 * (speed - 1))
    base_ms = estimate_duration_ms(text, pace)
    audible_ms = int(base_ms * rate_mult)
    # subtitle tokens with per-token timing (for reveal + retention join keys)
    words = (text or "").split()
    tokens = []
    t = 0
    per_word = audible_ms / max(1, len(words))
    for i, w in enumerate(words):
        # function words shorter, content words longer (matches estimate)
        clean = re.sub(r"[^\w']", "", w.lower())
        func = clean in {"the", "a", "an", "and", "of", "to", "in"}
        dur = per_word * (0.8 if func else 1.1)
        tokens.append({"word": w, "start_ms": int(t), "dur_ms": int(dur)})
        t += dur
        if w.endswith("."):
            t += 300 * rate_mult
        elif w.endswith(","):
            t += 150 * rate_mult
    return {
        "duration_ms": audible_ms + TAIL_MS,
        "audible_ms": audible_ms,
        "tokens": tokens,
        "schedule": {
            "voice_start_ms": VOICE_START_MS,
            "breath_before_ms": BREATH_MS,
            "tail_after_ms": TAIL_MS,
            "total_ms": VOICE_START_MS + audible_ms + TAIL_MS,
        },
        "mix": {"music_level": MUSIC_LEVEL, "cue_level": CUE_LEVEL,
                "duck_to": DUCK_TO, "duck_ms": DUCK_MS},
    }


def revealed_length(text: str, timing: dict, elapsed_ms: int) -> int:
    """Characters revealed at elapsed time (for subtitle rendering)."""
    tokens = timing.get("tokens", [])
    n = 0
    for tok in tokens:
        if tok.get("start_ms", 0) <= elapsed_ms:
            n += len(tok.get("word", "")) + 1
        else:
            break
    return min(len(text or ""), n)
