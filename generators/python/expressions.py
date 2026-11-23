"""String slicing, division operators and loop counting."""
from __future__ import annotations

import math
import random
from typing import List

from ..core import FILL_BLANK, MCQ, STEPS, InvalidProblem, Param, Problem, Step
from .common import Output, PythonGenerator, code_problem, run

# ---- slicing ------------------------------------------------------------------------------
WORDS = ["generator", "algorithm", "notebook", "variable", "function", "python", "keyboard",
         "practice", "compiler", "iteration", "boolean", "recursion", "network", "dataset"]
SLICE_MISCONCEPTIONS = {
    "stop_inclusive": "Includes the character at the stop index; slices stop BEFORE it.",
    "one_based": "Counts positions from 1 instead of 0.",
    "negative_off_by_one": "Counts negative indexes from -0: s[-1] is the LAST character.",
    "ignored_step": "Ignores the step in s[a:b:step].",
}
FORMS = ("index", "negative_index", "slice", "open_start", "open_end", "negative_slice", "step", "reverse")


def slice_text(form, n, rng):
    """(expression inside brackets, python slice/int, label for steps)"""
    if form == "index":
        i = rng.randint(1, n - 1)
        return f"{i}", i
    if form == "negative_index":
        k = rng.randint(1, min(4, n))
        return f"-{k}", -k
    if form == "slice":
        a = rng.randint(1, n - 3)
        b = rng.randint(a + 1, n - 1)
        return f"{a}:{b}", slice(a, b)
    if form == "open_start":
        b = rng.randint(2, n - 1)
        return f":{b}", slice(None, b)
    if form == "open_end":
        a = rng.randint(1, n - 2)
        return f"{a}:", slice(a, None)
    if form == "negative_slice":
        k = rng.randint(2, min(5, n - 1))
        return f"-{k}:", slice(-k, None)
    if form == "step":
        a = rng.randint(0, 2)
        b = rng.randint(a + 4, n)
        s = rng.choice([2, 3])
        return f"{a}:{b}:{s}", slice(a, b, s)
    return "::-1", slice(None, None, -1)


class StringSlicing(PythonGenerator):
    id = "python.string_slicing"
    summary = "Predict the result of indexing and slicing a string, including negative indexes and steps."
    concepts = ("python-strings", "indexing", "slicing")
    misconceptions = SLICE_MISCONCEPTIONS
    params = {"forms": Param("Kinds of index or slice", choices=FORMS)}
    levels = {
        "easy": dict(forms=["index", "negative_index", "open_start"]),
        "medium": dict(forms=["slice", "open_end", "negative_index", "negative_slice"]),
        "hard": dict(forms=["slice", "negative_slice", "step", "reverse"]),
    }

    def generate(self, rng: random.Random, level) -> Problem:
        word = rng.choice(WORDS)
        form = rng.choice(level["forms"])
        text, _ = slice_text(form, len(word), rng)
        code = f'word = "{word}"\nprint(word[{text}])'
        return code_problem("What does this code print?", code, {"word": word, "form": form, "text": text})

    def variants(self, problem: Problem, rng: random.Random):
        d = problem.data
        w, form, text = d["word"], d["form"], d["text"]
        parts = [int(p) if p.lstrip("-").isdigit() else None for p in text.split(":")]
        out = []
        if form in ("index",):
            out.append(("one_based", w[parts[0] - 1]))
        if form == "negative_index":
            k = -parts[0]
            if k < len(w):
                out.append(("negative_off_by_one", w[-(k + 1)]))
        if form in ("slice", "open_start", "step"):
            a, b = parts[0], parts[1]
            s = parts[2] if len(parts) > 2 else None
            out.append(("stop_inclusive", w[slice(a, b + 1, s)]))
            out.append(("one_based", w[slice((a or 1) - 1, b - 1, s)]))
        if form == "step":
            out.append(("ignored_step", w[parts[0]:parts[1]]))
        if form in ("open_end", "negative_slice"):
            a = parts[0]
            out.append(("one_based" if a > 0 else "negative_off_by_one", w[a - 1:]))
        out += [(None, w[1:4]), (None, w[:3]), (None, w[-3:]), (None, w[::2]), (None, w[0]), (None, w[-1])]
        return out

    def explain(self, problem: Problem, answer) -> List[Step]:
        d = problem.data
        w, text = d["word"], d["text"]
        idx = list(range(len(w)))
        parts = [int(p) if p.lstrip("-").isdigit() else None for p in text.split(":")]
        chosen = [idx[parts[0]]] if len(parts) == 1 else idx[slice(*parts)]
        table = " ".join(f"{i}:{c}" for i, c in enumerate(w))
        return [
            Step("Index of each character", work=table),
            Step("Indexes used", Output(" ".join(map(str, chosen))),
                 "negative indexes count from the end (-1 is the last)" if text.startswith("-") or ":-" in text
                 else "a slice stops BEFORE its stop index", ask=True),
        ]


# ---- division operators ---------------------------------------------------------------------
DIV_MISCONCEPTIONS = {
    "slash_is_integer": "Thinks / between integers gives an integer; / always gives a float (6 / 3 is 2.0).",
    "truncates_toward_zero": "Thinks // and % round toward zero; Python floors, so -7 // 2 is -4 and -7 % 2 is 1.",
    "swapped_floor_and_mod": "Mixes up // (how many times it fits) and % (the remainder).",
}


def trunc_div(a, b):
    return int(a / b)


def evaluate(a, op, b, flag=None):
    if op == "/":
        return a // b if flag == "slash_is_integer" else a / b
    if flag == "swapped_floor_and_mod":
        op = "%" if op == "//" else "//"
    if flag == "truncates_toward_zero":
        q = trunc_div(a, b)
        return q if op == "//" else a - b * q
    return a // b if op == "//" else a % b


class DivisionOperators(PythonGenerator):
    id = "python.division"
    summary = "Evaluate /, // and % on integers, including negative numbers."
    concepts = ("python-arithmetic", "integer-division", "modulo")
    misconceptions = DIV_MISCONCEPTIONS
    params = {
        "expressions": Param("Expressions printed together", 1, 3),
        "operators": Param("Operators to use", choices=("/", "//", "%")),
        "negatives": Param("Share of expressions with a negative number", 0.0, 1.0),
    }
    levels = {
        "easy": dict(expressions=1, operators=["/", "//", "%"], negatives=0.0),
        "medium": dict(expressions=2, operators=["/", "//", "%"], negatives=0.2),
        "hard": dict(expressions=3, operators=["//", "%", "/"], negatives=0.5),
    }

    def generate(self, rng: random.Random, level) -> Problem:
        exprs = []
        for _ in range(level["expressions"]):
            op = rng.choice(level["operators"])
            b = rng.randint(2, 6)
            a = rng.randint(b + 1, 30)
            if op == "/" and rng.random() < 0.4:
                a = b * rng.randint(2, 6)  # exact division: shows 2.0, not 2
            if rng.random() < level["negatives"]:
                a = -a
                if op in ("//", "%") and a % b == 0:
                    a -= 1  # an exact multiple would hide how Python floors
            if op == "/" and not float(a / b * 4).is_integer():
                a = b * rng.randint(2, 6) + (b // 2 if b % 2 == 0 else 0)
            exprs.append((a, op, b))
        code = "print(" + ", ".join(f"{a} {op} {b}" for a, op, b in exprs) + ")"
        return code_problem("What does this code print?", code, {"exprs": [list(e) for e in exprs]})

    def variants(self, problem: Problem, rng: random.Random):
        exprs = [tuple(e) for e in problem.data["exprs"]]
        out = []
        for flag in DIV_MISCONCEPTIONS:
            out.append((flag, " ".join(str(evaluate(a, op, b, flag)) for a, op, b in exprs)))
        correct = [evaluate(a, op, b) for a, op, b in exprs]
        out += [(None, " ".join(str(v + 1 if isinstance(v, int) else v + 0.5) for v in correct)),
                (None, " ".join(str(-v) for v in correct)),
                (None, " ".join(str(round(v)) if isinstance(v, float) else str(float(v)) for v in correct))]
        return out

    def explain(self, problem: Problem, answer) -> List[Step]:
        steps = []
        for a, op, b in (tuple(e) for e in problem.data["exprs"]):
            v = evaluate(a, op, b)
            why = {"/": "true division always gives a float",
                   "//": f"floor of {a / b:g}: rounds DOWN, toward −∞",
                   "%": f"remainder with the sign of the divisor: {a} - {b}×({a // b})"}[op]
            steps.append(Step(f"{a} {op} {b}", Output(str(v)), why, ask=True))
        return steps


# ---- loop counting ---------------------------------------------------------------------------
COUNT_MISCONCEPTIONS = {
    "multiplied_dependent_loops": "Multiplies the loop sizes even though the inner loop depends on i.",
    "added_nested_loops": "Adds the loop sizes instead of multiplying them.",
    "off_by_one": "Counts one extra (or one fewer) iteration at the boundary.",
    "linear_for_doubling": "Thinks a doubling loop runs about n times instead of about log₂ n.",
}
LOOP_FORMS = ("nested_fixed", "nested_dependent", "while_doubling", "while_step")


class LoopCount(PythonGenerator):
    id = "python.loop_count"
    summary = "Count how many times nested for loops or while loops run."
    concepts = ("loops", "nested-loops", "while-loops")
    misconceptions = COUNT_MISCONCEPTIONS
    params = {
        "forms": Param("Loop shapes", choices=LOOP_FORMS),
        "max_n": Param("Largest loop bound", 3, 64),
    }
    levels = {
        "easy": dict(forms=["nested_fixed", "while_step"], max_n=5),
        "medium": dict(forms=["nested_fixed", "nested_dependent", "while_step"], max_n=8),
        "hard": dict(forms=list(LOOP_FORMS), max_n=40),
    }

    def generate(self, rng: random.Random, level) -> Problem:
        form = rng.choice(level["forms"])
        top = level["max_n"]
        if form == "nested_fixed":
            n, m = rng.randint(2, min(top, 6)), rng.randint(2, min(top, 6))
            code = f'for i in range({n}):\n    for j in range({m}):\n        print("*", end="")'
            data = {"n": n, "m": m}
        elif form == "nested_dependent":
            n = rng.randint(3, min(top, 8))
            inner = rng.choice(["i", "i + 1"])
            code = f'for i in range({n}):\n    for j in range({inner}):\n        print("*", end="")'
            data = {"n": n, "inner": inner}
        elif form == "while_doubling":
            n = rng.randint(5, max(6, top))
            code = f'i = 1\nwhile i < {n}:\n    print("*", end="")\n    i *= 2'
            data = {"n": n}
        else:
            a, s = rng.randint(0, 5), rng.randint(1, 4)
            b = a + s * rng.randint(2, max(2, min(top, 8)))
            op = rng.choice(["<", "<="])
            code = f'i = {a}\nwhile i {op} {b}:\n    print("*", end="")\n    i += {s}'
            data = {"a": a, "b": b, "s": s, "op": op}
        data["form"] = form
        return code_problem("How many * does this code print?", code, data)

    def solve(self, problem: Problem) -> int:
        return run(problem.code).count("*")

    def variants(self, problem: Problem, rng: random.Random):
        d, ans = problem.data, run(problem.code).count("*")
        out = []
        if d["form"] == "nested_fixed":
            out.append(("added_nested_loops", d["n"] + d["m"]))
            out.append(("off_by_one", (d["n"] + 1) * (d["m"] + 1)))
        elif d["form"] == "nested_dependent":
            out.append(("multiplied_dependent_loops", d["n"] * d["n"]))
            other = d["n"] * (d["n"] + 1) // 2 if d["inner"] == "i" else d["n"] * (d["n"] - 1) // 2
            out.append(("off_by_one", other))
        elif d["form"] == "while_doubling":
            out.append(("linear_for_doubling", d["n"]))
            out.append(("off_by_one", ans + 1))
        else:
            out.append(("off_by_one", ans + 1 if d["op"] == "<" else ans - 1))
        out += [(None, ans + k) for k in (2, -1, -2, 3) if ans + k >= 0]
        return out

    def explain(self, problem: Problem, answer: int) -> List[Step]:
        d = problem.data
        if d["form"] == "nested_fixed":
            return [Step("Inner loop runs per i", d["m"], ask=True), Step("Outer loop runs", d["n"], ask=True),
                    Step("Total", answer, f"{d['n']} × {d['m']}")]
        if d["form"] == "nested_dependent":
            counts = [i if d["inner"] == "i" else i + 1 for i in range(d["n"])]
            return [Step("Inner runs for i = 0, 1, ...", Output(" ".join(map(str, counts))), ask=True),
                    Step("Total", answer, " + ".join(map(str, counts)))]
        if d["form"] == "while_doubling":
            values, i = [], 1
            while i < d["n"]:
                values.append(i)
                i *= 2
            return [Step("Values of i that pass the test", Output(" ".join(map(str, values))),
                         f"i doubles: 1, 2, 4, ... while i < {d['n']}", ask=True)]
        values, i = [], d["a"]
        while (i < d["b"]) if d["op"] == "<" else (i <= d["b"]):
            values.append(i)
            i += d["s"]
        return [Step("Values of i that pass the test", Output(" ".join(map(str, values))),
                     f"the test is i {d['op']} {d['b']}", ask=True)]
