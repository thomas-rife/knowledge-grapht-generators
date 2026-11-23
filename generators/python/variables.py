"""Variables and assignment: trace a short program line by line.

Programs mix assignment, copying one variable into another, augmented
assignment, swaps (correct tuple swaps and the broken two-line kind),
division and string operations. A small interpreter replays the program under
each misconception to produce the wrong answers.
"""
from __future__ import annotations

import random
from typing import Dict, List, Tuple

from ..core import InvalidProblem, Param, Problem, Step
from .common import Output, PythonGenerator, code_problem

MISCONCEPTIONS = {
    "copy_links": "Thinks b = a links the variables, so later changes to a also change b.",
    "sequential_swap_works": "Thinks a = b followed by b = a swaps the values.",
    "string_math": "Treats digit strings as numbers: '3' + '4' as 7 and '3' * 2 as 6.",
    "slash_is_integer": "Thinks / between integers gives an integer (7 / 2 as 3).",
    "unchanged_by_augmented": "Thinks x += k shows the change only later, not on the next line.",
}
NAMES = [("a", "b"), ("x", "y"), ("p", "q"), ("first", "second")]


def line_text(op) -> List[str]:
    kind = op[0]
    if kind == "set":
        return [f"{op[1]} = {op[2]!r}"]
    if kind == "copy":
        return [f"{op[1]} = {op[2]}"]
    if kind == "binop":
        return [f"{op[1]} = {op[2]} {op[3]} {op[4]!r}"]
    if kind == "aug":
        return [f"{op[1]} {op[2]}= {op[3]!r}"]
    if kind == "swap":
        return [f"{op[1]}, {op[2]} = {op[2]}, {op[1]}"]
    raise ValueError(kind)


def simulate(ops, flags=()) -> List[Dict[str, object]]:
    """Variable values after each op, optionally under misconceptions."""
    env: Dict[str, object] = {}
    links: Dict[str, str] = {}  # follower -> leader, for copy_links
    history = []

    def apply(o, a, k):
        if "string_math" in flags and isinstance(a, str) and a.lstrip("-").isdigit():
            a = int(a)
            k = int(k) if isinstance(k, str) else k
        if o == "+":
            return a + k
        if o == "-":
            return a - k
        if o == "*":
            return a * k
        if o == "/":
            return a // k if "slash_is_integer" in flags and isinstance(a, int) and isinstance(k, int) else a / k
        raise ValueError(o)

    def assign(name, value):
        env[name] = value
        links.pop(name, None)
        if "copy_links" in flags:
            for follower, leader in list(links.items()):
                if leader == name:
                    env[follower] = value

    for i, op in enumerate(ops):
        kind = op[0]
        if kind == "set":
            assign(op[1], op[2])
        elif kind == "copy":
            dst, src = op[1], op[2]
            is_second_half = ("sequential_swap_works" in flags and i > 0 and ops[i - 1][0] == "copy"
                              and ops[i - 1][1] == src and ops[i - 1][2] == dst)
            if is_second_half:
                assign(dst, history[-2][src] if len(history) >= 2 else env[src])
            else:
                assign(dst, env[src])
                links[dst] = src
        elif kind == "binop":
            assign(op[1], apply(op[3], env[op[2]], op[4]))
        elif kind == "aug":
            assign(op[1], apply(op[2], env[op[1]], op[3]))
        elif kind == "swap":
            a, b = op[1], op[2]
            va, vb = env[b], env[a]
            assign(a, va)
            assign(b, vb)
        history.append(dict(env))
    return history


class Variables(PythonGenerator):
    id = "python.variables"
    summary = "Trace assignments, copies, swaps, += and division line by line to find the final values."
    concepts = ("python-variables", "assignment", "tracing")
    misconceptions = MISCONCEPTIONS
    params = {
        "lines": Param("Statements after the initial assignments", 1, 6),
        "features": Param("Kinds of statement to include",
                          choices=("copy", "arithmetic", "augmented", "swap", "two_line_swap", "division", "strings")),
    }
    levels = {
        "easy": dict(lines=2, features=["copy", "arithmetic", "augmented"]),
        "medium": dict(lines=3, features=["copy", "arithmetic", "augmented", "two_line_swap", "division"]),
        "hard": dict(lines=4, features=["copy", "augmented", "swap", "two_line_swap", "division", "strings"]),
    }

    def generate(self, rng: random.Random, level) -> Problem:
        a, b = rng.choice(NAMES)
        features = list(level["features"])
        strings = "strings" in features and rng.random() < 0.5
        if strings:
            ops = [("set", a, str(rng.randint(1, 9))), ("set", b, str(rng.randint(1, 9)))]
        else:
            ops = [("set", a, rng.randint(1, 12)), ("set", b, rng.randint(1, 12))]
        features = [f for f in features if f != "strings"] or ["arithmetic", "augmented"]
        for _ in range(level["lines"]):
            f = rng.choice(features)
            u, v = rng.sample([a, b], 2)
            if f == "copy":
                ops.append(("copy", u, v))
            elif f == "arithmetic":
                ops.append(("binop", u, v, "+", str(rng.randint(1, 9)) if strings else rng.randint(1, 9)))
            elif f == "augmented":
                ops.append(("aug", u, "*" if strings else rng.choice("+-*"), rng.randint(2, 3)))
            elif f == "swap":
                ops.append(("swap", a, b))
            elif f == "two_line_swap":
                ops += [("copy", a, b), ("copy", b, a)]
            elif f == "division" and not strings:
                ops.append(("binop", u, u, "/", rng.choice([2, 4])))
        final = simulate(ops)[-1]
        if any(isinstance(val, float) and not float(val * 4).is_integer() for val in final.values()):
            raise InvalidProblem("awkward float")
        if any(isinstance(val, str) and len(val) > 12 for val in final.values()):
            raise InvalidProblem("string too long")
        code = "\n".join(t for op in ops for t in line_text(op)) + f"\nprint({a}, {b})"
        return code_problem("What does this code print?", code, {"ops": [list(o) for o in ops], "names": [a, b]})

    @staticmethod
    def _unpack(problem: Problem) -> Tuple[list, List[str]]:
        return [tuple(o) for o in problem.data["ops"]], problem.data["names"]

    def variants(self, problem: Problem, rng: random.Random):
        ops, (a, b) = self._unpack(problem)
        out = []
        for flag in ("copy_links", "sequential_swap_works", "string_math", "slash_is_integer"):
            final = simulate(ops, (flag,))[-1]
            out.append((flag, f"{final[a]} {final[b]}"))
        initial = simulate(ops)[1]
        final = simulate(ops)[-1]
        out += [(None, f"{initial[a]} {initial[b]}"), (None, f"{final[b]} {final[a]}"),
                (None, f"{final[a]} {final[a]}"), (None, f"{final[b]} {final[b]}")]
        return out

    def explain(self, problem: Problem, answer) -> List[Step]:
        ops, (a, b) = self._unpack(problem)
        history = simulate(ops)
        steps = []
        for i, (op, env) in enumerate(zip(ops, history), start=1):
            values = " ".join(str(env.get(n, "-")) for n in (a, b))
            steps.append(Step(f"After line {i} ({line_text(op)[0]}): {a}, {b}", Output(values), ask=i > 2))
        return steps
