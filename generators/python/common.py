"""Shared pieces for Python code generators.

`run` executes programs THIS package generated, to get their exact output.
It is never used on student code: student answers are outputs, numbers or
range(...) calls that are parsed, not executed. Running student-written code
needs an isolated runner (Pyodide in the browser, or a server sandbox).
"""
from __future__ import annotations

import builtins
import contextlib
import io
import random
import re
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

from ..core import FILL_BLANK, MCQ, STEPS, Generator, Option, Problem

SAFE_BUILTINS = {
    name: getattr(builtins, name)
    for name in ("print", "range", "len", "list", "str", "int", "float", "abs", "min", "max", "sum",
                 "sorted", "reversed", "enumerate", "bool", "round", "zip")
}


def run(source: str) -> str:
    """Run a generated program (trusted, no imports available) and return what it prints."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(compile(source, "<generated>", "exec"), {"__builtins__": SAFE_BUILTINS})
    return out.getvalue()


def tokens(text: Any) -> List[str]:
    """Output compared value by value: spacing, commas between values and quote style don't matter."""
    t = str(text).strip().replace("'", '"')
    if t.lower() in ("", "nothing", "(nothing)", "no output", "none printed"):
        return []
    return [x for x in re.split(r"[\s,]+", t) if x]


@dataclass
class Output:
    """Answer type: what a program prints."""

    text: str

    def __str__(self) -> str:
        shown = " ".join(self.text.split())
        return shown if shown else "(nothing)"

    def accepts(self, response: str) -> bool:
        return tokens(response) == tokens(self.text)


def printed(values) -> str:
    """What print(a, b, ...) shows for these values."""
    return " ".join(str(v) for v in values) + "\n"


class PythonGenerator(Generator):
    """Base for Python generators: the answer is what the code prints.

    Subclasses implement generate() and variants(), which returns
    (misconception tag or None, output text) pairs for wrong answers.
    """

    formats = (MCQ, FILL_BLANK, STEPS)

    def solve(self, problem: Problem) -> Any:
        return Output(run(problem.code))

    def variants(self, problem: Problem, rng: random.Random) -> List[Tuple[Optional[str], Any]]:
        raise NotImplementedError

    def answer_options(self, problem: Problem, answer: Any, rng: random.Random) -> list:
        variants = self.variants(problem, rng)
        tagged = [Option(wrap(v), tag) for tag, v in variants if tag]
        filler = [wrap(v) for tag, v in variants if not tag]
        rng.shuffle(tagged)
        rng.shuffle(filler)
        return tagged + filler


def wrap(value: Any) -> Any:
    return Output(value) if isinstance(value, str) else value


def code_problem(prompt: str, code: str, data: dict) -> Problem:
    return Problem(prompt=prompt, data=data, code=code, language="python")
