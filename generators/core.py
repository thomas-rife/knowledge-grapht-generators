"""Practice-question generators: write three methods, get every question format.

    generate(rng, settings)   -> Problem      a random scenario and its question text
    solve(problem)            -> answer       the correct answer, computed in code
    answer_options(problem, answer, rng)      wrong answers, ideally one per misconception
    explain(problem, answer)  -> [Step]       optional worked solution; steps marked
                                              ask=True become blanks in the "steps" format

The harness turns that into multiple choice, fill in the blank or a
step-by-step worked problem, marks responses, and names the misconception
behind a wrong one. Answers can be text, numbers, booleans, sets (lists) or
any object with an `accepts(response)` method; marking adapts to the type.

Size and difficulty are settings. Each generator declares `params` (what can
be adjusted, with ranges) and `levels` (easy / medium / hard presets). Any
setting can be overridden per question, and the settings are stored with the
question so it can be rebuilt exactly.
"""
from __future__ import annotations

import json
import math
import random
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any, ClassVar, Dict, List, Mapping, Optional, Sequence, Tuple

MCQ = "mcq"
FILL_BLANK = "fill_blank"
STEPS = "steps"
CODE = "code"  # the student writes code, marked by running tests
DIFFICULTIES = ("easy", "medium", "hard")
NONE_WORDS = {"none", "nothing", "empty", "{}", "∅"}
TRUE_WORDS = {"t", "true", "yes", "y"}
FALSE_WORDS = {"f", "false", "no", "n"}
MIN_NUMBER_GAP = 0.01  # numeric options closer than this are too confusing to show together


@dataclass
class Diagram:
    """Laid-out picture every client draws the same way."""

    nodes: List[dict]  # {"id", "x", "y", "observed": bool, "role": "query" | None}
    edges: List[dict]  # {"from", "to", "curve": 0 for straight}
    width: float
    height: float


@dataclass
class Table:
    """A table shown with the question (CPTs, data counts, clauses, ...)."""

    title: str
    columns: List[str]
    rows: List[List[str]]


@dataclass
class Problem:
    prompt: str
    data: dict = field(default_factory=dict)  # whatever solve() needs; JSON-safe
    diagram: Optional[Diagram] = None
    tables: List[Table] = field(default_factory=list)
    code: Optional[str] = None  # a program shown with the question (monospace)
    language: Optional[str] = None


@dataclass
class Option:
    """A wrong answer, optionally tagged with the misconception that produces it."""

    answer: Any
    misconception: Optional[str] = None


@dataclass
class Step:
    """One line of a worked solution. ask=True makes it a blank in the steps format."""

    label: str
    value: Any = None
    work: str = ""
    ask: bool = False


@dataclass(frozen=True)
class Param:
    """An adjustable setting. Numbers use min/max; `choices` means a list picked from them."""

    description: str
    min: Optional[float] = None
    max: Optional[float] = None
    choices: Optional[Tuple[str, ...]] = None


class InvalidProblem(Exception):
    """Raise from generate() when a random scenario is unsuitable; the harness retries."""


class Generator:
    id: ClassVar[str]
    version: ClassVar[int] = 1
    summary: ClassVar[str] = ""  # one line: what kinds of questions this generates
    concepts: ClassVar[Sequence[str]] = ()
    misconceptions: ClassVar[Mapping[str, str]] = {}  # tag -> plain-language description
    formats: ClassVar[Sequence[str]] = (MCQ, FILL_BLANK)
    option_count: ClassVar[int] = 4
    abs_tol: ClassVar[Optional[float]] = None  # numeric answers: allowed error (default 0.1% relative)
    params: ClassVar[Mapping[str, Param]] = {}  # what can be adjusted
    levels: ClassVar[Mapping[str, Mapping[str, Any]]] = {}  # easy / medium / hard presets

    def generate(self, rng: random.Random, settings: Mapping[str, Any]) -> Problem:
        raise NotImplementedError

    def solve(self, problem: Problem) -> Any:
        raise NotImplementedError

    def answer_options(self, problem: Problem, answer: Any, rng: random.Random) -> List[Any]:
        """Wrong answers, best first. Plain values or Option(value, misconception)."""
        raise NotImplementedError

    def explain(self, problem: Problem, answer: Any) -> List[Step]:
        return []


@dataclass
class Question:
    generator_id: str
    generator_version: int
    seed: int
    difficulty: str
    format: str
    concepts: List[str]
    settings: Dict[str, Any]
    prompt: str
    diagram: Optional[Diagram]
    tables: List[Table]
    code: Optional[str]
    language: Optional[str]
    options: Optional[List[str]]  # shown choices (mcq only), correct one included
    answer: str  # correct answer as text
    steps: List[Step]  # worked solution
    # Server-side only:
    answer_value: Any = None
    tolerance: Optional[float] = None
    wrong: List[Option] = field(default_factory=list)
    problem: Optional[Problem] = None

    @property
    def explanation(self) -> str:
        return "\n".join(step_text(s) for s in self.steps)

    @property
    def blanks(self) -> List[Step]:
        """What the student fills in for the steps format: asked steps, then the answer."""
        return [s for s in self.steps if s.ask] + [Step("Answer", self.answer_value, ask=True)]

    def check(self, response: str) -> bool:
        return matches(self.answer_value, response, self.tolerance)

    def check_step(self, index: int, response: str) -> bool:
        blanks = self.blanks
        value = blanks[index].value
        if index == len(blanks) - 1:
            return self.check(response)
        # Intermediate numbers: allow 1% (students round partial results).
        tol = max(0.0005, 0.01 * abs(value)) if is_number(value) else None
        return matches(value, response, tol)

    def diagnose(self, response: str) -> Optional[str]:
        """The misconception behind a wrong final answer, if it matches a known one."""
        if self.check(response):
            return None
        return next(
            (o.misconception for o in self.wrong if matches(o.answer, response, self.tolerance)),
            None,
        )

    def student_view(self) -> dict:
        return {
            "generator_id": self.generator_id,
            "generator_version": self.generator_version,
            "seed": self.seed,
            "difficulty": self.difficulty,
            "settings": self.settings,
            "format": self.format,
            "prompt": self.prompt,
            "diagram": asdict(self.diagram) if self.diagram else None,
            "tables": [asdict(t) for t in self.tables],
            "code": self.code,
            "language": self.language,
            "options": self.options,
            "blanks": [b.label for b in self.blanks] if self.format == STEPS else None,
        }


def resolve_settings(
    generator: Generator, difficulty: str = "medium", overrides: Optional[Mapping[str, Any]] = None
) -> Dict[str, Any]:
    """Start from a preset, apply overrides, and check every value against `params`."""
    if difficulty not in generator.levels:
        raise ValueError(f"unknown difficulty {difficulty!r}; choose from {', '.join(generator.levels)}")
    out = dict(generator.levels[difficulty])
    for key, value in (overrides or {}).items():
        if key not in generator.params:
            raise ValueError(f"{generator.id} has no setting {key!r}; choose from {', '.join(generator.params)}")
        out[key] = value
    for key, p in generator.params.items():
        if key not in out:
            raise ValueError(f"{generator.id}: preset {difficulty!r} is missing {key!r}")
        value = out[key]
        if p.choices is not None:
            value = list(value) if is_set(value) else [value]
            bad = [v for v in value if v not in p.choices]
            if bad or not value:
                raise ValueError(f"{key}: pick one or more of {', '.join(p.choices)}")
        else:
            if not is_number(value):
                raise ValueError(f"{key} must be a number")
            if (p.min is not None and value < p.min) or (p.max is not None and value > p.max):
                raise ValueError(f"{key} must be between {p.min} and {p.max}")
            whole = all(isinstance(b, int) for b in (p.min, p.max) if b is not None)
            value = int(value) if whole and float(value).is_integer() else float(value)
        out[key] = value
    return out


def describe(generator: Generator) -> dict:
    """Everything a picker UI needs: formats, adjustable settings and presets."""
    return {
        "id": generator.id,
        "version": generator.version,
        "summary": generator.summary,
        "concepts": list(generator.concepts),
        "formats": list(generator.formats),
        "misconceptions": dict(generator.misconceptions),
        "params": {k: asdict(p) for k, p in generator.params.items()},
        "levels": {k: dict(v) for k, v in generator.levels.items()},
    }


def make_question(
    generator: Generator,
    seed: int,
    difficulty: str = "medium",
    fmt: Optional[str] = None,
    settings: Optional[Mapping[str, Any]] = None,
    max_attempts: int = 300,
) -> Question:
    """Same arguments always give the same question.

    `difficulty` picks a preset; `settings` overrides any individual value.
    """
    resolved = resolve_settings(generator, difficulty, settings)
    if fmt is not None and fmt not in generator.formats:
        raise ValueError(f"{generator.id} does not offer {fmt!r}")
    key = json.dumps(resolved, sort_keys=True)
    for attempt in range(max_attempts):
        rng = random.Random(f"{generator.id}:{generator.version}:{seed}:{key}:{fmt}:{attempt}")
        chosen = fmt or rng.choice(list(generator.formats))
        try:
            problem = generator.generate(rng, resolved)
        except InvalidProblem:
            continue
        answer = generator.solve(problem)
        wrong = _distinct_wrong(
            generator.answer_options(problem, answer, rng), answer, generator.abs_tol
        )
        options = None
        if chosen == MCQ:
            if len(wrong) < generator.option_count - 1:
                continue
            options = [as_text(o.answer) for o in wrong[: generator.option_count - 1]] + [as_text(answer)]
            rng.shuffle(options)
        return Question(
            generator_id=generator.id,
            generator_version=generator.version,
            seed=seed,
            difficulty=difficulty,
            format=chosen,
            concepts=list(generator.concepts),
            settings=resolved,
            prompt=problem.prompt,
            diagram=problem.diagram,
            tables=problem.tables,
            code=problem.code,
            language=problem.language,
            options=options,
            answer=as_text(answer),
            steps=generator.explain(problem, answer) or [],
            answer_value=answer,
            tolerance=generator.abs_tol,
            wrong=wrong,
            problem=problem,
        )
    raise RuntimeError(
        f"{generator.id}: no valid problem after {max_attempts} attempts; these settings may be too restrictive"
    )


def _distinct_wrong(raw: List[Any], answer: Any, tol: Optional[float]) -> List[Option]:
    seen, out = {as_text(answer)}, []
    numbers = [answer] if is_number(answer) else []
    for item in raw:
        option = item if isinstance(item, Option) else Option(item)
        text = as_text(option.answer)
        if text in seen or matches(answer, text, tol):
            continue
        if is_number(option.answer):
            if any(abs(option.answer - n) < MIN_NUMBER_GAP for n in numbers):
                continue
            numbers.append(option.answer)
        seen.add(text)
        out.append(option)
    return out


def step_text(step: Step) -> str:
    out = f"• {step.label}"
    if step.work:
        out += f": {step.work}"
    if step.value is not None:
        shown = f"{step.value:.4g}" if isinstance(step.value, float) else as_text(step.value)
        out += f" {'→' if step.work else '='} {shown}"
    return out


# ---- answer types ------------------------------------------------------------
def is_set(value: Any) -> bool:
    return isinstance(value, (list, tuple, set, frozenset))


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def as_text(value: Any) -> str:
    if isinstance(value, bool):
        return "True" if value else "False"
    if is_set(value):
        items = sorted(str(v) for v in value)
        return ", ".join(items) if items else "none"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def normalize(text: Any) -> str:
    text = unicodedata.normalize("NFKC", str(text)).lower()
    return re.sub(r"\s+", " ", text).strip()


def parse_set(text: Any) -> set:
    text = normalize(text)
    if text in NONE_WORDS:
        return set()
    return {t for t in re.split(r"[\s,;{}()\[\]]+|\band\b", text) if t}


def parse_number(text: Any) -> Optional[float]:
    """Accepts 0.625, .625, 5/8, 62.5%."""
    t = normalize(text).replace(" ", "")
    try:
        if t.endswith("%"):
            return float(t[:-1]) / 100
        if "/" in t:
            num, den = t.split("/", 1)
            return float(num) / float(den)
        return float(t)
    except (ValueError, ZeroDivisionError):
        return None


def matches(expected: Any, response: Any, abs_tol: Optional[float] = None) -> bool:
    """Type-aware marking."""
    if hasattr(expected, "accepts"):
        return expected.accepts(response)
    if isinstance(expected, bool):
        word = normalize(response)
        return word in (TRUE_WORDS if expected else FALSE_WORDS)
    if is_set(expected):
        return parse_set(response) == {normalize(v) for v in expected}
    if is_number(expected):
        got = parse_number(response)
        if got is None:
            return False
        if abs_tol is not None:
            return abs(got - expected) <= abs_tol + 1e-12
        return math.isclose(got, float(expected), rel_tol=1e-3, abs_tol=1e-9)
    return normalize(response) == normalize(expected)
