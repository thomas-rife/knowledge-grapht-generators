"""Write a function, marked by unit tests (LeetCode style).

Each task family produces a random specification, a reference solution,
buggy versions that each encode one misconception, and test inputs that
include the boundaries where those bugs show. Formats:
- code: write the function; it passes if every test matches the reference.
- mcq: pick the correct implementation from buggy look-alikes.
- steps: predict the function's result on boundary inputs, then write it.
"""
from __future__ import annotations

import random
import textwrap
from typing import Dict, List

from ..core import CODE, MCQ, STEPS, Generator, InvalidProblem, Option, Param, Problem, Step
from .code_answer import CodeAnswer, run_trusted

MISCONCEPTIONS = {
    "stop_exclusive": "Forgets that range stops before its stop value, so the last value is missing.",
    "ignored_step": "Ignores the step, including values in between.",
    "started_at_zero": "Starts from 0 instead of the given start.",
    "boundary_flip": "Uses > where the task needs >= (or the reverse), so the boundary value is wrong.",
    "separate_ifs": "Uses separate ifs instead of elif, so a later branch overwrites the earlier result.",
    "wrong_order": "Checks the conditions in the wrong order, so a broad condition hides the narrow ones.",
    "counted_characters": "Adds up word lengths instead of counting words.",
    "integer_division": "Uses // instead of /, so the average loses its fraction.",
    "no_empty_check": "Doesn't handle the empty list, so it crashes dividing by zero.",
    "negative_zero_slice": "Uses items[-n:], which returns the WHOLE list when n is 0.",
    "slice_off_by_one": "Slices one position too early or too late.",
    "inclusive_upper_bound": "Includes n itself when the task says 'less than n'.",
    "counted_instead_of_summed": "Counts the matching numbers instead of adding them up.",
    "ignored_condition": "Counts every item instead of only the ones that meet the condition.",
    "forgot_divide": "Returns the total instead of dividing by how many numbers there are.",
    "sliced_from_start": "Takes items from the start of the list instead of the end.",
    "no_default_return": "Forgets the final return, so values that match no condition give None.",
}
TASKS = ("multiples_list", "grade", "count_longer", "average", "last_n", "sum_multiples")
WORDS = ["cat", "tree", "python", "loop", "list", "a", "range", "code", "graph", "node", "if", "while", "variable"]


def src(text: str) -> str:
    return textwrap.dedent(text).strip() + "\n"


def multiples_list(rng):
    k, start = rng.randint(2, 5), rng.randint(1, 6)
    ref = f"def multiples(n):\n    return list(range({start}, n + 1, {k}))\n"
    bugs = {
        "stop_exclusive": f"def multiples(n):\n    return list(range({start}, n, {k}))\n",
        "ignored_step": f"def multiples(n):\n    return list(range({start}, n + 1))\n",
        "started_at_zero": f"def multiples(n):\n    return list(range(0, n + 1, {k}))\n",
    }
    hit = start + k * rng.randint(2, 4)  # n exactly on a value: the off-by-one boundary
    inputs = [[hit], [hit + 1], [start], [start - 1], [hit + k - 1]]
    desc = (f"Write multiples(n) that returns a list of the numbers {start}, {start + k}, {start + 2 * k}, ... "
            f"(start at {start}, go up by {k}) that are at most n. Return [] if there are none.")
    return "multiples", desc, ref, bugs, inputs, [[hit], [start - 1]]


def grade(rng):
    cuts = sorted(rng.sample(range(55, 96, 5), 3), reverse=True)
    strict = rng.random() < 0.4
    op, flip = (">", ">=") if strict else (">=", ">")
    words = "more than" if strict else "at least"
    labels = ["A", "B", "C", "D"]

    def chain(o, kw="elif", order=cuts):
        lines = ["def grade(score):"]
        for i, c in enumerate(order):
            lines += [f"    {'if' if i == 0 else kw} score {o} {c}:", f'        return "{labels[cuts.index(c)]}"']
        lines.append(f'    return "{labels[3]}"')
        return "\n".join(lines) + "\n"

    separate = ["def grade(score):", f'    result = "{labels[3]}"']
    for c, label in zip(cuts, labels[:3]):  # highest first, so lower grades overwrite higher ones
        separate += [f"    if score {op} {c}:", f'        result = "{label}"']
    separate.append("    return result")
    bugs = {
        "boundary_flip": chain(flip),
        "wrong_order": chain(op, order=list(reversed(cuts))),
        "separate_ifs": "\n".join(separate) + "\n",
        "no_default_return": chain(op).replace(f'    return "{labels[3]}"\n', ""),
    }
    inputs = [[c] for c in cuts] + [[c + 1] for c in cuts] + [[c - 1] for c in cuts] + [[0], [100]]
    desc = (f"Write grade(score) that returns \"A\" if score is {words} {cuts[0]}, \"B\" if {words} {cuts[1]}, "
            f"\"C\" if {words} {cuts[2]}, and \"D\" otherwise.")
    return "grade", desc, chain(op), bugs, inputs, [[cuts[0]], [cuts[1] - 1]]


def count_longer(rng):
    k = rng.randint(2, 5)
    strict = rng.random() < 0.5
    op, flip, words = (">", ">=", "more than") if strict else (">=", ">", "at least")
    ref = src(f"""
        def count_long(words, k):
            count = 0
            for w in words:
                if len(w) {op} k:
                    count += 1
            return count
    """)
    bugs = {
        "boundary_flip": ref.replace(f"len(w) {op} k", f"len(w) {flip} k"),
        "counted_characters": src(f"""
            def count_long(words, k):
                total = 0
                for w in words:
                    if len(w) {op} k:
                        total += len(w)
                return total
        """),
        "ignored_condition": src("""
            def count_long(words, k):
                return len(words)
        """),
    }
    inputs = [[rng.sample(WORDS, rng.randint(3, 6)), k] for _ in range(3)] + [[[], k], [["x" * k, "y" * (k + 1)], k]]
    desc = f"Write count_long(words, k) that returns how many strings in the list words have {words} k characters."
    return "count_long", desc, ref, bugs, inputs, [[["x" * k, "y" * (k + 1), "z"], k], [[], k]]


def average(rng):
    ref = src("""
        def average(nums):
            if len(nums) == 0:
                return 0
            return sum(nums) / len(nums)
    """)
    bugs = {
        "integer_division": ref.replace("sum(nums) / len(nums)", "sum(nums) // len(nums)"),
        "no_empty_check": src("""
            def average(nums):
                return sum(nums) / len(nums)
        """),
        "forgot_divide": src("""
            def average(nums):
                return sum(nums)
        """),
    }
    inputs = [[rng.sample(range(1, 20), n)] for n in (2, 3, 4)] + [[[]], [[7]], [[1, 2]]]
    desc = "Write average(nums) that returns the mean of a list of numbers as a float, or 0 for an empty list."
    return "average", desc, ref, bugs, inputs, [[[1, 2]], [[]]]


def last_n(rng):
    ref = src("""
        def last_n(items, n):
            if n == 0:
                return []
            return items[-n:]
    """)
    bugs = {
        "negative_zero_slice": src("""
            def last_n(items, n):
                return items[-n:]
        """),
        "slice_off_by_one": src("""
            def last_n(items, n):
                if n == 0:
                    return []
                return items[-n - 1:]
        """),
        "sliced_from_start": src("""
            def last_n(items, n):
                return items[:n]
        """),
    }
    base = rng.sample(range(1, 30), rng.randint(4, 7))
    inputs = [[base, 2], [base, 1], [base, 0], [base, len(base) + 2], [[], 3]]
    desc = ("Write last_n(items, n) that returns a list of the last n items (the whole list if n is larger than "
            "its length, and [] if n is 0).")
    return "last_n", desc, ref, bugs, inputs, [[base, 0], [base, 2]]


def sum_multiples(rng):
    k = rng.randint(2, 7)
    ref = src(f"""
        def sum_multiples(n):
            total = 0
            for i in range({k}, n, {k}):
                total += i
            return total
    """)
    bugs = {
        "inclusive_upper_bound": ref.replace(f"range({k}, n, {k})", f"range({k}, n + 1, {k})"),
        "counted_instead_of_summed": ref.replace("total += i", "total += 1"),
        "ignored_step": src(f"""
            def sum_multiples(n):
                total = 0
                for i in range({k}, n):
                    total += i
                return total
        """),
    }
    hit = k * rng.randint(3, 6)
    inputs = [[hit], [hit + 1], [k], [1], [hit + k - 1]]
    desc = f"Write sum_multiples(n) that returns the sum of the positive multiples of {k} that are less than n."
    return "sum_multiples", desc, ref, bugs, inputs, [[hit], [k]]


BUILDERS = {"multiples_list": multiples_list, "grade": grade, "count_longer": count_longer, "average": average,
            "last_n": last_n, "sum_multiples": sum_multiples}


class WriteFunction(Generator):
    id = "python.write_function"
    summary = "Write a short Python function that must pass hidden unit tests, including edge cases."
    concepts = ("python-functions", "unit-testing", "python-range", "python-conditionals", "python-lists")
    misconceptions = MISCONCEPTIONS
    formats = (CODE, MCQ, STEPS)
    params = {"tasks": Param("Kinds of function to write", choices=TASKS)}
    levels = {
        "easy": dict(tasks=["multiples_list", "average", "count_longer"]),
        "medium": dict(tasks=["multiples_list", "grade", "count_longer", "average"]),
        "hard": dict(tasks=list(TASKS)),
    }

    def generate(self, rng: random.Random, level) -> Problem:
        task = rng.choice(level["tasks"])
        name, desc, ref, bugs, inputs, step_inputs = BUILDERS[task](rng)
        expected = run_trusted(ref, name, inputs)["results"]
        live, seen = {}, [expected]
        for tag, bug in bugs.items():
            got = run_trusted(bug, name, inputs)["results"]
            if got not in seen:  # keep bugs the tests catch, and only one per distinct behaviour
                live[tag] = bug
                seen.append(got)
        if not live:
            raise InvalidProblem("tests don't separate the bugs")
        return Problem(
            prompt=desc + f" Your function is run against {len(inputs)} tests, including edge cases.",
            data={"task": task, "function": name, "reference": ref, "bugs": live, "inputs": inputs,
                  "step_inputs": step_inputs},
            language="python",
        )

    def solve(self, problem: Problem) -> CodeAnswer:
        d = problem.data
        return CodeAnswer.from_source(d["reference"], d["function"], d["inputs"])

    def answer_options(self, problem: Problem, answer: CodeAnswer, rng: random.Random) -> list:
        d = problem.data
        options = [Option(CodeAnswer.from_source(bug, d["function"], d["inputs"]), tag) for tag, bug in d["bugs"].items()]
        rng.shuffle(options)
        return options

    def explain(self, problem: Problem, answer: CodeAnswer) -> List[Step]:
        d = problem.data
        results = run_trusted(d["reference"], d["function"], d["step_inputs"])["results"]
        steps = []
        for args, r in zip(d["step_inputs"], results):
            call = f"{d['function']}({', '.join(repr(a) for a in args)})"
            steps.append(Step(f"What should {call} return?", r["value"], "an edge case the tests check", ask=True))
        steps.append(Step("Reference solution", work=d["reference"].strip().replace("\n", " ⏎ ")))
        return steps
