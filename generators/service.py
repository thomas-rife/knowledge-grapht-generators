"""The questions service: catalog, preview, new question, check answer.

Apps (Studio, admin) call this from their servers. A question travels as a
signed token holding generator id, version, seed, difficulty, settings and
format, so nothing is stored here and the answer never reaches the browser:
`check` rebuilds the question from the token and marks the response.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from .core import CODE, MCQ, STEPS, Question, as_text, describe, make_question, resolve_settings
from .graphs import diagram_to_svg
from .registry import GENERATORS, SUBJECTS

TOKEN_TTL = 60 * 60 * 24  # a question stays answerable for a day


class ServiceError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def _secret() -> bytes:
    secret = os.environ.get("GENERATORS_SECRET", "")
    if len(secret) < 16:
        raise ServiceError("GENERATORS_SECRET is not configured (16+ characters).", 500)
    return secret.encode()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def sign(payload: Dict[str, Any]) -> str:
    body = _b64(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
    mac = _b64(hmac.new(_secret(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{mac}"


def verify(token: str) -> Dict[str, Any]:
    try:
        body, mac = token.split(".", 1)
    except ValueError:
        raise ServiceError("Invalid question token.")
    expected = _b64(hmac.new(_secret(), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(mac, expected):
        raise ServiceError("Invalid question token.")
    payload = json.loads(_unb64(body))
    if time.time() - payload.get("iat", 0) > TOKEN_TTL:
        raise ServiceError("This question has expired. Start a new one.")
    return payload


def _generator(generator_id: str, version: Optional[int] = None):
    gen = GENERATORS.get(generator_id)
    if gen is None:
        raise ServiceError(f"Unknown generator {generator_id!r}.", 404)
    if version is not None and int(version) != gen.version:
        raise ServiceError("This practice set uses an older generator version. Ask your instructor to re-add it.", 409)
    return gen


def _build(gen, seed: int, difficulty: str, settings: Optional[dict], fmt: Optional[str]) -> Question:
    try:
        return make_question(gen, seed, difficulty, fmt, settings)
    except ValueError as e:
        raise ServiceError(str(e))
    except RuntimeError as e:
        raise ServiceError(str(e), 422)


def _view(q: Question) -> Dict[str, Any]:
    view = q.student_view()
    view["diagram_svg"] = diagram_to_svg(q.diagram) if q.diagram else None
    return view


def _steps(q: Question) -> List[Dict[str, Any]]:
    out = []
    for s in q.steps:
        value = None if s.value is None else (f"{s.value:.4g}" if isinstance(s.value, float) else as_text(s.value))
        out.append({"label": s.label, "work": s.work, "value": value})
    return out


# ---- endpoints ----------------------------------------------------------------------------
def catalog() -> Dict[str, Any]:
    items = []
    for gid, gen in GENERATORS.items():
        info = describe(gen)
        info["subject"] = SUBJECTS[gid]
        items.append(info)
    return {"generators": items}


def preview(generator_id: str, difficulty: str = "medium", settings: Optional[dict] = None,
            format: Optional[str] = None, seed: Optional[int] = None) -> Dict[str, Any]:
    """For instructors choosing a generator: a sample question WITH its answer."""
    gen = _generator(generator_id)
    q = _build(gen, seed if seed is not None else secrets.randbelow(2 ** 31), difficulty, settings, format)
    view = _view(q)
    view.update({"answer": q.answer, "steps": _steps(q),
                 "options_detail": [{"text": o, "correct": q.check(o),
                                     "misconception": gen.misconceptions.get(q.diagnose(o) or "", None)}
                                    for o in (q.options or [])]})
    return view


def new_question(generator_id: str, version: Optional[int] = None, difficulty: str = "medium",
                 settings: Optional[dict] = None, formats: Optional[List[str]] = None,
                 format: Optional[str] = None) -> Dict[str, Any]:
    """For students: a fresh question and a signed token; no answer included."""
    gen = _generator(generator_id, version)
    allowed = [f for f in (formats or gen.formats) if f in gen.formats]
    if not allowed:
        raise ServiceError("None of the chosen formats are offered by this generator.")
    if format is not None and format not in allowed:
        raise ServiceError("That format isn't enabled for this practice set.")
    seed = secrets.randbelow(2 ** 31)
    chosen = format or allowed[seed % len(allowed)]
    resolved = resolve_settings(gen, difficulty, settings) if gen.levels else {}
    q = _build(gen, seed, difficulty, settings, chosen)
    token = sign({"g": gen.id, "v": gen.version, "s": seed, "d": difficulty, "st": settings or {}, "f": chosen,
                  "iat": int(time.time())})
    view = _view(q)
    view["token"] = token
    view["settings"] = resolved
    return view


def check(token: str, response: Optional[str] = None, step_responses: Optional[List[str]] = None) -> Dict[str, Any]:
    p = verify(token)
    gen = _generator(p["g"], p["v"])
    q = _build(gen, p["s"], p["d"], p["st"], p["f"])
    result: Dict[str, Any] = {"generator_id": gen.id, "generator_version": gen.version, "seed": p["s"],
                              "difficulty": p["d"], "settings": p["st"], "format": p["f"], "concepts": q.concepts}
    if q.format == STEPS:
        responses = list(step_responses or [])
        blanks = q.blanks
        marks = [bool(r) and q.check_step(i, r) for i, r in enumerate(responses[: len(blanks)])]
        marks += [False] * (len(blanks) - len(marks))
        final = responses[len(blanks) - 1] if len(responses) >= len(blanks) else ""
        result.update({"correct": all(marks), "step_correct": marks,
                       "step_answers": [as_text(b.value) if not isinstance(b.value, float) else f"{b.value:.4g}"
                                        for b in blanks]})
    else:
        final = response or ""
        result["correct"] = bool(final.strip()) and q.check(final)
    tag = None if result["correct"] or not final.strip() else q.diagnose(final)
    result.update({"answer": q.answer, "steps": _steps(q), "misconception": tag,
                   "misconception_text": gen.misconceptions.get(tag) if tag else None})
    if q.format == CODE and final.strip():
        result["tests"] = q.answer_value.feedback(final)
    return result
