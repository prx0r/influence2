"""Jev runner via OpenRouter — custom client for @parcha/agentrun-jev.

Routes TypeSafe System One (Jev) questions through OpenRouter's
`typesafe/jev-router` model using the existing OPENROUTER_API_KEY.
No separate TYPESAFE_API_KEY needed.

Usage:
    from pipeline.jev_openrouter import make_jev_runner
    run_judge = make_jev_runner()
    result = await run_judge({label, kind, state, questions})

The client implements systemOne(request, options) matching the
@parcha/agentrun-jev JevClient interface.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
JEV_MODEL = "typesafe/jev-router"


def _get_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if key:
        return key
    # vault fallback
    import subprocess
    r = subprocess.run(
        ["agent-vault", "vault", "credential", "get", "OPENROUTER_API_KEY", "--vault", "oracle"],
        capture_output=True, text=True,
    )
    key = r.stdout.strip()
    if not key:
        raise RuntimeError("no OPENROUTER_API_KEY in env or vault oracle")
    return key


def _system_prompt() -> str:
    return (
        "You are a typed-question answering system (Jev/System One). "
        "Given a STATE and QUESTIONS, answer each question with the required type. "
        "Return ONLY a JSON object of the form: "
        '{"answers": {"<question_id>": {"type": "noul"|"choice"|"score", ...}}} '
        "where noul answers have a float field 'noul' (0-1), "
        "choice answers have 'choice' (string), 'confidence' (float), and 'probabilities' (object), "
        "score answers have 'score' (float), 'confidence' (float), and 'probabilities' (object). "
        "No prose. No markdown. Pure JSON only."
    )


def _build_user_prompt(request: dict) -> str:
    state = request.get("state", "")
    questions = request.get("questions", {})
    if not isinstance(state, str):
        state = json.dumps(state, ensure_ascii=False)
    return (
        f"STATE:\n{state}\n\n"
        f"QUESTIONS:\n{json.dumps(questions, ensure_ascii=False)}\n\n"
        "Answer each question. Return ONLY the JSON answers object."
    )


def _parse_answer(text: str) -> dict:
    """Extract the answers JSON from a model response, tolerating prose/markdown."""
    text = text.strip()
    # strip markdown fences if present
    if text.startswith("```"):
        text = text.split("```", 2)[1] if "```" in text[3:] else text[3:]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    # find first { ... } block
    start = text.find("{")
    if start == -1:
        raise ValueError(f"no JSON in response: {text[:200]}")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError(f"unbalanced JSON in response: {text[:200]}")


async def system_one(request: dict, options: Any = None) -> dict:
    """JevClient.systemOne — call OpenRouter jev-router and return answers.

    request: {state, questions, model?}
    options: AbortSignal-like with .signal or .throwIfAborted (optional)
    """
    signal = getattr(options, "signal", None) or getattr(options, "_signal", None)
    if signal is not None and hasattr(signal, "throwIfAborted"):
        signal.throwIfAborted()

    key = _get_key()
    payload = {
        "model": JEV_MODEL,
        "messages": [
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": _build_user_prompt(request)},
        ],
        "max_tokens": 500,
        "temperature": 0.0,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        OPENROUTER_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://influence2.local",
            "X-Title": "influence2-jev",
        },
        method="POST",
    )

    # blocking HTTP in async context — fine for beta, swap for aiohttp later
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"openrouter HTTP {e.code}: {e.read()[:300]}") from e

    content = body["choices"][0]["message"]["content"]
    answers_obj = _parse_answer(content)
    # normalize: ensure answers key exists
    if "answers" not in answers_obj:
        answers_obj = {"answers": answers_obj}
    # attach model/usage if present
    if "model" in body:
        answers_obj["model"] = body["model"]
    if "usage" in body:
        answers_obj["usage"] = body["usage"]
    return answers_obj


def make_jev_runner(**kwargs):
    """Create a Jev runner backed by OpenRouter.

    Returns a callable suitable as runJudge for @parcha/agentrun-jev
    or for direct use. kwargs pass through to createJevRunner if available,
    otherwise returns the raw system_one client wrapped as a runner.
    """
    # raw client as async runner — the JS adapter wraps this in Node;
    # on the Python side this IS the runner.
    # For the JS @parcha/agentrun-jev adapter, see dash/agentrun_host.mjs
    async def run_judge(request: dict) -> dict:
        return await system_one(request, None)

    return run_judge
