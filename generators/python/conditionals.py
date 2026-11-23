"""if / elif / else: which branches run?

Programs vary the structure (an elif chain, separate ifs where the final else
belongs only to the last if, or nested ifs), the comparison operators and the
value tested, often landing exactly on a threshold.
"""
from __future__ import annotations

import random
from typing import List

from ..core import InvalidProblem, Param, Problem, Step
from .common import Output, PythonGenerator, code_problem, run

MISCONCEPTIONS = {
    "elif_runs_all": "Treats an elif chain like separate ifs, running every branch whose condition is true.",
    "separate_ifs_stop": "Thinks separate if statements stop at the first true one, like elif.",
    "boundary_flip": "Mixes up > and >= (or < and <=) when the value equals the threshold.",
    "else_always_runs": "Thinks the else branch always runs as well.",
}
SUBJECTS = [
    ("score", ["A", "B", "C", "D", "F"]),
    ("temp", ["hot", "warm", "mild", "cool", "cold"]),
    ("age", ["senior", "adult", "teen", "child", "baby"]),
    ("speed", ["fast", "quick", "steady", "slow", "stopped"]),
]
FLIP = {">": ">=", ">=": ">", "<": "<=", "<=": "<"}


def render(spec, structure=None, flip=False, else_always=False) -> str:
    var, x, conds, labels = spec["var"], spec["x"], spec["conds"], spec["labels"]
    structure = structure or spec["structure"]
    op = lambda o: FLIP[o] if flip else o
    lines = [f"{var} = {x}"]
    if structure == "nested":
        (o1, t1), (o2, t2) = conds[0], conds[1]
        lines += [f"if {var} {op(o1)} {t1}:", f"    if {var} {op(o2)} {t2}:", f'        print("{labels[0]}")',
                  "    else:", f'        print("{labels[1]}")', "else:", f'    print("{labels[2]}")']
        return "\n".join(lines)
    for i, (o, t) in enumerate(conds):
        kw = "if" if i == 0 or structure == "separate" else "elif"
        lines += [f"{kw} {var} {op(o)} {t}:", f'    print("{labels[i]}")']
    if else_always:
        lines.append(f'print("{labels[len(conds)]}")')
    else:
        lines += ["else:", f'    print("{labels[len(conds)]}")']
    return "\n".join(lines)


def holds(x, o, t) -> bool:
    return {">": x > t, ">=": x >= t, "<": x < t, "<=": x <= t}[o]


class Conditionals(PythonGenerator):
    id = "python.conditionals"
    summary = "Predict which branch of an if / elif / else (or separate or nested ifs) runs for a value."
    concepts = ("python-conditionals", "if-elif-else", "boolean-comparisons")
    misconceptions = MISCONCEPTIONS
    params = {
        "branches": Param("Conditions before the else (nested always uses 2)", 1, 4),
        "structures": Param("elif = one chain; separate = independent ifs (else belongs to the last); nested = ifs inside ifs",
                            choices=("elif", "separate", "nested")),
        "operators": Param("Comparison operators to use", choices=(">", ">=", "<", "<=")),
        "boundary_share": Param("Share of questions where the value equals a threshold", 0.0, 1.0),
    }
    levels = {
        "easy": dict(branches=2, structures=["elif"], operators=[">", ">="], boundary_share=0.2),
        "medium": dict(branches=3, structures=["elif", "separate"], operators=[">", ">="], boundary_share=0.4),
        "hard": dict(branches=3, structures=["elif", "separate", "nested"], operators=[">", ">=", "<", "<="],
                     boundary_share=0.5),
    }

    def generate(self, rng: random.Random, level) -> Problem:
        var, labels = rng.choice(SUBJECTS)
        structure = rng.choice(level["structures"])
        k = 2 if structure == "nested" else level["branches"]
        ops = level["operators"]
        downward = [o for o in ops if o in (">", ">=")]
        upward = [o for o in ops if o in ("<", "<=")]
        direction = rng.choice([d for d, avail in (("down", downward), ("up", upward)) if avail])
        if direction == "up":
            labels = list(reversed(labels))  # smallest values first: "cold" before "hot"
        thresholds = sorted(rng.sample(range(10, 100, 5), k), reverse=(direction == "down"))
        if structure == "nested":
            thresholds = sorted(thresholds, reverse=(direction == "up"))  # inner test is stricter
        conds = [(rng.choice(downward if direction == "down" else upward), t) for t in thresholds]
        if rng.random() < level["boundary_share"]:
            x = rng.choice(thresholds)
        else:
            x = rng.randint(min(thresholds) - 10, max(thresholds) + 10)
        spec = {"var": var, "x": x, "conds": conds, "labels": labels[: k + 1], "structure": structure}
        return code_problem("What does this code print?", render(spec), spec)

    def variants(self, problem: Problem, rng: random.Random):
        spec = problem.data
        out = []
        if spec["structure"] == "elif":
            out.append(("elif_runs_all", run(render(spec, structure="separate"))))
        if spec["structure"] == "separate":
            out.append(("separate_ifs_stop", run(render(spec, structure="elif"))))
        out.append(("boundary_flip", run(render(spec, flip=True))))
        if spec["structure"] != "nested":
            out.append(("else_always_runs", run(render(spec, else_always=True))))
        labels = spec["labels"]
        out += [(None, label + "\n") for label in labels]
        out += [(None, f"{labels[i]}\n{labels[i + 1]}\n") for i in range(len(labels) - 1)]
        return out

    def explain(self, problem: Problem, answer) -> List[Step]:
        spec = problem.data
        var, x, conds, structure = spec["var"], spec["x"], spec["conds"], spec["structure"]
        steps = []
        if structure == "nested":
            outer = holds(x, *conds[0])
            steps.append(Step(f"{var} {conds[0][0]} {conds[0][1]}", outer, f"{var} = {x}", ask=True))
            if outer:
                steps.append(Step(f"{var} {conds[1][0]} {conds[1][1]}", holds(x, *conds[1]), "inner if", ask=True))
            else:
                steps.append(Step("Inner if", work="skipped: the outer condition is False, so its else runs"))
            return steps
        for i, (o, t) in enumerate(conds):
            result = holds(x, o, t)
            steps.append(Step(f"{var} {o} {t}", result, f"{var} = {x}", ask=True))
            if result and structure == "elif":
                if i < len(conds) - 1:
                    steps.append(Step("Remaining elif/else", work="skipped: an elif chain stops at the first True condition"))
                return steps
        if structure == "separate":
            steps.append(Step("else", work=f"belongs only to the last if, which was {holds(x, *conds[-1])}"))
        return steps
