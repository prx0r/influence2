"""Pattern checks — score any content against the 7 proven farm patterns.

Mined from 681 avatar channels (data/avatarintel/export.json).
Each check returns {pattern, pass, score, note}. Used by release_gate
(pre-publish) and content_decide (brief quality). Jev judges the nuanced
questions; code checks the countable patterns.

The 7 patterns:
  1. one_x_per_video  — single topic, not a grab-bag
  2. numbered_countdown — N items with escalation (not flat list)
  3. mistake_hook     — "you're doing X wrong" / STOP / NEVER
  4. credential       — specific lived story, not generic authority
  5. thumbnail_template — same face + 2-5 caps words + arrow + object
  6. description_storefront — product link first line + chapters
  7. cadence           — 3+/week (sellers do 4.9)

Pure stdlib. No network. No model calls.
"""
from __future__ import annotations

import re

# Mistake-correction hook phrases (from title pattern mining)
HOOK_PHRASES = [
    r"\bwrong\b", r"\bstop\b", r"\bnever\b", r"\bdon't\b", r"\bmistake",
    r"\bthrow away\b", r"\bbefore you\b", r"\bmost people\b",
    r"\bsecreto\b", r"\bnunca\b",  # Spanish equivalents
]

# Numbered countdown: N + optional adjectives + items/ways/tricks
COUNTDOWN_PAT = re.compile(
    r"\b(\d{1,2})\s+(?:[A-Za-z]+\s+){0,2}(things|ways|tricks|mistakes|items|uses|moves|"
    r"habits|tips|secrets|reasons|signs|causes|products|recipes)\b", re.I)


def check_one_x(title: str, description: str = "") -> dict:
    """Single topic per video? Penalize grab-bag titles (multiple 'and/or' topics)."""
    title_only = title or ""
    # count in title only (descriptions legitimately contain URLs with slashes)
    and_count = len(re.findall(r"\band\b", title_only, re.I))
    slash_count = title_only.count("/")
    # one 'and' is fine (setup), 3+ suggests grab-bag
    if and_count >= 3 or slash_count >= 2:
        return {"pattern": "one_x_per_video", "pass": False, "score": 30,
                "note": "multiple topics — split into one video each"}
    return {"pattern": "one_x_per_video", "pass": True, "score": 90,
            "note": "single-topic focus"}


def check_numbered(title: str) -> dict:
    """Numbered countdown with escalation?"""
    m = COUNTDOWN_PAT.search(title or "")
    if m:
        n = int(m.group(1))
        if 5 <= n <= 17:
            return {"pattern": "numbered_countdown", "pass": True,
                    "score": 95,
                    "note": f"{n} items — farm sweet spot (5-17)"}
        return {"pattern": "numbered_countdown", "pass": True, "score": 70,
                "note": f"{n} items — outside 5-17 sweet spot but numbered"}
    # bare number without countdown words still counts partially
    if re.search(r"\b\d{1,2}\b", title or ""):
        return {"pattern": "numbered_countdown", "pass": False, "score": 40,
                "note": "has a number but no countdown structure"}
    return {"pattern": "numbered_countdown", "pass": False, "score": 20,
            "note": "no numbered structure — add N items"}


def check_hook(title: str) -> dict:
    """Mistake-correction hook? (highest-converting open)"""
    t = (title or "").lower()
    hits = [p for p in HOOK_PHRASES
            if re.search(p, t, re.I)]
    if hits:
        return {"pattern": "mistake_hook", "pass": True, "score": 90,
                "note": f"hook detected ({len(hits)} signals)"}
    # question hooks convert second-best
    if "?" in (title or ""):
        return {"pattern": "mistake_hook", "pass": False, "score": 50,
                "note": "question hook (weaker than mistake-correction)"}
    return {"pattern": "mistake_hook", "pass": False, "score": 20,
            "note": "no hook — add STOP/NEVER/wrong framing"}


def check_credential(description: str = "", sample_text: str = "") -> dict:
    """Specific lived story? (scars, not diplomas)"""
    text = f"{description or ''} {sample_text or ''}"
    # signals: first-person past-tense stories, specific numbers/years
    story_signals = len(re.findall(
        r"\b(I|my|we|our)\b.{0,40}\b(\d+\s*(years|winters|reports|cases)|"
        r"when I|my own|learned the hard way|failed|mistake I made)\b",
        text, re.I))
    year_ref = bool(re.search(r"\b\d+\s*(years|winters)\b", text, re.I))
    if story_signals >= 2 or (story_signals >= 1 and year_ref):
        return {"pattern": "credential", "pass": True, "score": 85,
                "note": "lived-experience credential present"}
    if story_signals >= 1:
        return {"pattern": "credential", "pass": False, "score": 55,
                "note": "weak credential — add specific years/failures"}
    return {"pattern": "credential", "pass": False, "score": 25,
            "note": "no credential — add 'I learned this over N years when...'"}


def check_thumbnail(thumb_brief: str = "") -> dict:
    """Same-face template signals? (checks the brief, not pixels)"""
    t = (thumb_brief or "").lower()
    score, notes = 50, []
    # face present + consistent
    if re.search(r"\bface\b|\bportrait\b|\bsame\b|\bnolan\b|\bcharacter\b", t):
        score += 15
        notes.append("face anchored")
    # short caps text (2-5 words)
    words = re.findall(r'"([^"]+)"', thumb_brief or "")
    for w in words:
        n = len(w.split())
        if 2 <= n <= 5:
            score += 15
            notes.append(f"text '{w}' in 2-5 word range")
            break
    # arrow/object pointer
    if re.search(r"\barrow\b|\bpoint", t):
        score += 10
        notes.append("directional cue")
    # emotion
    if re.search(r"\b(stare|concern|shock|smile|deadpan|angry|wide.eyed)\b", t):
        score += 10
        notes.append("emotional expression")
    score = min(100, score)
    return {"pattern": "thumbnail_template",
            "pass": score >= 70, "score": score,
            "note": "; ".join(notes) if notes else "no template signals in brief"}


def check_description(description: str = "", has_product_link: bool = False,
                      has_chapters: bool = False) -> dict:
    """Storefront description? (product first, chapters, fixed template)"""
    score, notes = 30, []
    if has_product_link:
        score += 30
        notes.append("product link present")
    elif re.search(r"https?://", description or ""):
        score += 15
        notes.append("has links (verify product first)")
    if has_chapters or re.search(r"\b\d{1,2}:\d{2}\b", description or ""):
        score += 20
        notes.append("chapters/timestamps")
    if len(description or "") > 200:
        score += 10
        notes.append("substantive description")
    score = min(100, score)
    return {"pattern": "description_storefront",
            "pass": score >= 60, "score": score,
            "note": "; ".join(notes) if notes else "bare description"}


def check_cadence(uploads_per_week: float = 0) -> dict:
    """Seller-grade cadence? (1.86x lift for daily, 0.31x for rare)"""
    upw = uploads_per_week or 0
    if upw >= 7:
        return {"pattern": "cadence", "pass": True, "score": 95,
                "note": f"{upw}/wk daily+ (1.86x seller lift)"}
    if upw >= 4:
        return {"pattern": "cadence", "pass": True, "score": 85,
                "note": f"{upw}/wk matches seller median 4.9"}
    if upw >= 3:
        return {"pattern": "cadence", "pass": True, "score": 70,
                "note": f"{upw}/wk meets minimum viable"}
    return {"pattern": "cadence", "pass": False, "score": 30,
            "note": f"{upw}/wk below minimum 3 (sellers do 4.9)"}


def check_all(title: str = "", description: str = "",
              sample_text: str = "", thumb_brief: str = "",
              uploads_per_week: float = 0,
              has_product_link: bool = False,
              has_chapters: bool = False) -> dict:
    """Run all 7 pattern checks. Returns per-pattern + aggregate."""
    results = [
        check_one_x(title, description),
        check_numbered(title),
        check_hook(title),
        check_credential(description, sample_text),
        check_thumbnail(thumb_brief),
        check_description(description, has_product_link, has_chapters),
        check_cadence(uploads_per_week),
    ]
    passed = sum(1 for r in results if r["pass"])
    avg = round(sum(r["score"] for r in results) / len(results), 1)
    return {"checks": {r["pattern"]: r for r in results},
            "passed": passed, "total": len(results),
            "score": avg,
            "verdict": "FOLLOWS" if passed >= 5 else
                       "PARTIAL" if passed >= 3 else "BREAKS",
            "note": f"{passed}/7 farm patterns followed"}
