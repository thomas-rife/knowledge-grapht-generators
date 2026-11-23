"""range(): predict a loop's output, or write the range(...) call for a sequence."""
from __future__ import annotations

import ast
import random
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from ..core import FILL_BLANK, MCQ, STEPS, Generator, InvalidProblem, Option, Param, Problem, Step
from .common import Output, PythonGenerator, code_problem

MISCONCEPTIONS = {
    "stop_inclusive": "Includes the stop value: range stops BEFORE its second argument.",
    "starts_at_one": "Thinks range(n) counts 1..n instead of 0..n-1.",
    "ignored_start": "Ignores the start argument and counts from 0.",
    "ignored_step": "Ignores the step and counts by 1.",
    "forgot_negative_step": "Counts down without a negative step, which gives an empty range.",
}


def range_text(a: int, b: int, s: int, form: str) -> str:
    if form == "1":
        return f"range({b})"
    if form == "2":
        return f"range({a}, {b})"
    return f"range({a}, {b}, {s})"


def pick_range(rng: random.Random, level) -> Tuple[int, int, int, str]:
    form = rng.choice(level["range_args"])
    top, most = level["max_value"], level["max_iterations"]
    if form == "1":
        return 0, rng.randint(2, max(2, min(most, top))), 1, form
    if form == "2":
        a = rng.randint(1, max(1, top - 2))
        b = rng.randint(a + 2, max(a + 2, min(top, a + most)))
        return a, b, 1, form
    s = rng.randint(2, 5)
    count = rng.randint(2, most)
    if level["negative_step"] and rng.random() < 0.4:
        a = rng.randint(s * (count - 1), max(s * (count - 1), top))
        b = a - s * (count - 1) - rng.randint(1, s)
        return a, b, -s, form
    a = rng.randint(0, max(0, top // 2))
    b = a + s * (count - 1) + rng.randint(1, s)
    if b > top + s:
        raise InvalidProblem("too large")
    return a, b, s, form


class RangeLoop(PythonGenerator):
    id = "python.range_loop"
    summary = "Predict what a for loop over range(...) prints or sums, including steps and counting down."
    concepts = ("python-range", "for-loops", "off-by-one")
    misconceptions = MISCONCEPTIONS
    params = {
        "range_args": Param("Forms of range: 1 = range(stop), 2 = range(start, stop), 3 = range(start, stop, step)",
                            choices=("1", "2", "3")),
        "negative_step": Param("1 = allow counting down with a negative step", 0, 1),
        "max_value": Param("Largest start or stop value", 5, 50),
        "max_iterations": Param("Most loop iterations", 2, 12),
        "body": Param("print = print each value; sum = add the values up", choices=("print", "sum")),
    }
    levels = {
        "easy": dict(range_args=["1", "2"], negative_step=0, max_value=10, max_iterations=6, body=["print"]),
        "medium": dict(range_args=["2", "3"], negative_step=0, max_value=20, max_iterations=7, body=["print", "sum"]),
        "hard": dict(range_args=["3"], negative_step=1, max_value=30, max_iterations=8, body=["print", "sum"]),
    }

    def generate(self, rng: random.Random, level) -> Problem:
        a, b, s, form = pick_range(rng, level)
        if not 2 <= len(range(a, b, s)) <= level["max_iterations"]:
            raise InvalidProblem("length out of range")
        body = rng.choice(level["body"])
        r = range_text(a, b, s, form)
        if body == "print":
            code = f'for i in {r}:\n    print(i, end=" ")'
        else:
            code = f"total = 0\nfor i in {r}:\n    total += i\nprint(total)"
        return code_problem("What does this code print?", code, {"a": a, "b": b, "s": s, "form": form, "body": body})

    @staticmethod
    def _out(values, body) -> str:
        return " ".join(map(str, values)) if body == "print" else str(sum(values))

    def variants(self, problem: Problem, rng: random.Random):
        d = problem.data
        a, b, s, form, body = d["a"], d["b"], d["s"], d["form"], d["body"]
        out = []
        out.append(("stop_inclusive", self._out(range(a, b + (1 if s > 0 else -1), s), body)))
        if form == "1":
            out.append(("starts_at_one", self._out(range(1, b + 1), body)))
        if form in ("2", "3") and a != 0:
            out.append(("ignored_start", self._out(range(0, b, s), body)))
        if form == "3":
            out.append(("ignored_step", self._out(range(a, b, 1 if s > 0 else -1), body)))
        out += [(None, self._out(range(a + 1, b, s), body)), (None, self._out(range(a, b - s, s), body)),
                (None, self._out(range(a + s, b + s, s), body))]
        return out

    def explain(self, problem: Problem, answer) -> list:
        d = problem.data
        values = list(range(d["a"], d["b"], d["s"]))
        steps = [
            Step("Values of i", Output(" ".join(map(str, values))),
                 f"start at {d['a']}, step {d['s']}, stop BEFORE {d['b']}", ask=True),
            Step("Number of iterations", len(values), ask=True),
        ]
        if d["body"] == "sum":
            steps.append(Step("total", sum(values), " + ".join(map(str, values))))
        return steps


# ---- writing a range(...) call -------------------------------------------------------
def parse_range(text: str) -> Optional[List[int]]:
    """Values of a typed range(...) call, or None. Parsed with ast and never executed."""
    t = text.strip().rstrip(":").strip()
    t = re.sub(r"^for\s+\w+\s+in\s+", "", t)
    if t.startswith("list(") and t.endswith(")"):
        t = t[5:-1]
    try:
        node = ast.parse(t, mode="eval").body
    except SyntaxError:
        return None
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range"
            and 1 <= len(node.args) <= 3 and not node.keywords):
        return None
    args = []
    for arg in node.args:
        sign = 1
        if isinstance(arg, ast.UnaryOp) and isinstance(arg.op, ast.USub):
            sign, arg = -1, arg.operand
        if not (isinstance(arg, ast.Constant) and type(arg.value) is int and abs(arg.value) <= 10 ** 6):
            return None
        args.append(sign * arg.value)
    if len(args) == 3 and args[2] == 0:
        return None
    return list(range(*args))


@dataclass
class RangeCall:
    """Answer type: any range(...) call producing exactly these values."""

    values: Tuple[int, ...]
    display: str

    def __str__(self) -> str:
        return self.display

    def accepts(self, response: str) -> bool:
        got = parse_range(response)
        return got is not None and tuple(got) == tuple(self.values)


def call(a: int, b: int, s: int) -> RangeCall:
    if s == 1 and a == 0:
        text = f"range({b})"
    elif s == 1:
        text = f"range({a}, {b})"
    else:
        text = f"range({a}, {b}, {s})"
    return RangeCall(tuple(range(a, b, s)), text)


class RangeWrite(Generator):
    id = "python.range_write"
    summary = "Write the range(...) call that produces a given sequence of numbers."
    concepts = ("python-range", "off-by-one")
    misconceptions = MISCONCEPTIONS
    formats = (MCQ, FILL_BLANK, STEPS)
    params = {
        "length": Param("How many values the sequence has", 2, 10),
        "steps": Param("Kinds of step: one = 1, up = 2-5, down = negative", choices=("one", "up", "down")),
        "max_value": Param("Largest value in the sequence", 5, 50),
    }
    levels = {
        "easy": dict(length=4, steps=["one"], max_value=10),
        "medium": dict(length=5, steps=["one", "up"], max_value=25),
        "hard": dict(length=5, steps=["up", "down"], max_value=40),
    }

    def generate(self, rng: random.Random, level) -> Problem:
        kind = rng.choice(level["steps"])
        n = rng.randint(max(2, level["length"] - 2), level["length"])
        s = 1 if kind == "one" else rng.randint(2, 5)
        if kind == "down":
            s = -s
        span = abs(s) * (n - 1)
        if span > level["max_value"]:
            raise InvalidProblem("sequence too long for max_value")
        lo = rng.randint(0, level["max_value"] - span)
        a = lo if s > 0 else lo + span
        values = list(range(a, a + s * n, s))
        return Problem(
            prompt=(f"Write a range(...) call that produces exactly {', '.join(map(str, values))}. "
                    "Any correct call counts, e.g. range(2, 9, 3)."),
            data={"a": a, "s": s, "n": n},
            language="python",
        )

    def solve(self, problem: Problem) -> RangeCall:
        d = problem.data
        last = d["a"] + d["s"] * (d["n"] - 1)
        return call(d["a"], last + (1 if d["s"] > 0 else -1), d["s"])

    def answer_options(self, problem: Problem, answer: RangeCall, rng: random.Random) -> list:
        d = problem.data
        a, s, n = d["a"], d["s"], d["n"]
        last = a + s * (n - 1)
        options = [Option(call(a, last, s), "stop_inclusive")]
        if s not in (1,):
            options.append(Option(call(a, last + (1 if s > 0 else -1), 1 if s > 0 else -1), "ignored_step"))
        if s < 0:
            options.append(Option(RangeCall((), f"range({a}, {last - 1})"), "forgot_negative_step"))
        if a != 0 and s == 1:
            options.append(Option(call(0, last + 1, 1), "ignored_start"))
        rng.shuffle(options)
        filler = [call(a + (1 if s > 0 else -1), last + (1 if s > 0 else -1), s), call(a, last + 2 * s, s),
                  call(a - s, last, s)]
        return options + filler

    def explain(self, problem: Problem, answer: RangeCall) -> list:
        d = problem.data
        last = d["a"] + d["s"] * (d["n"] - 1)
        stop = last + (1 if d["s"] > 0 else -1)
        return [
            Step("start", d["a"], "the first value", ask=True),
            Step("step", d["s"], "the difference between neighbours" + (" (negative: counting down)" if d["s"] < 0 else ""),
                 ask=True),
            Step("stop", stop, f"one step past the last value {last}: range stops BEFORE stop", ask=True),
        ]
