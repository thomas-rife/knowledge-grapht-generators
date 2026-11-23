"""Maximum likelihood CPT estimation: "Estimate P(X=1 | parents) from these counts." """
from __future__ import annotations

import random
from itertools import product
from typing import Dict, List, Tuple

from ..core import FILL_BLANK, MCQ, STEPS, Generator, InvalidProblem, Option, Param, Problem, Step, Table
from ..graphs import draw, random_dag
from .network import assignment_text

MISCONCEPTIONS = {
    "used_joint": "Divides by the total number of samples, giving P(X=1, parents) instead of P(X=1 | parents).",
    "reversed_conditional": "Divides by the count of X=1, giving P(parents | X=1).",
    "ignored_parents": "Ignores the parents and estimates P(X=1) over all samples.",
    "wrong_value": "Estimates P(X=0 | parents) instead of P(X=1 | parents).",
}
PARAMS = {
    "nodes": Param("Number of variables (the data table has 2^nodes rows)", 2, 4),
    "parents": Param("Parents of the variable being estimated", 1, 3),
    "edge_prob": Param("Chance of each possible edge", 0.3, 1.0),
    "max_count": Param("Largest count in any row of the data table", 3, 30),
    "min_condition_count": Param("Fewest samples matching the condition (avoids tiny denominators)", 1, 20),
}
LEVELS = {
    "easy": dict(nodes=2, parents=1, edge_prob=1.0, max_count=9, min_condition_count=3),
    "medium": dict(nodes=3, parents=1, edge_prob=0.5, max_count=9, min_condition_count=3),
    "hard": dict(nodes=3, parents=2, edge_prob=0.7, max_count=9, min_condition_count=3),
}


class MaximumLikelihood(Generator):
    id = "bayes.mle_cpt"
    summary = "Estimate a CPT entry P(X | parents) by maximum likelihood from a table of counts."
    concepts = ("maximum-likelihood", "parameter-learning", "bayesian-networks")
    misconceptions = MISCONCEPTIONS
    formats = (MCQ, FILL_BLANK, STEPS)
    abs_tol = 0.002
    params = PARAMS
    levels = LEVELS

    def generate(self, rng: random.Random, level) -> Problem:
        if level["parents"] >= level["nodes"]:
            raise ValueError("parents must be smaller than nodes")
        dag = random_dag(rng, level["nodes"], level["edge_prob"], max_parents=level["parents"])
        targets = [n for n in dag.nodes if len(dag.parents(n)) == level["parents"]]
        if not targets:
            raise InvalidProblem("no node with the right number of parents")
        x = rng.choice(targets)
        parents = sorted(dag.parents(x))
        given = {p: rng.randint(0, 1) for p in parents}
        names = list(dag.nodes)
        counts = [[*values, rng.randint(0, level["max_count"])] for values in product((0, 1), repeat=len(names))]
        c = Counts(names, counts)
        n_given, n_hit = c.count(given), c.count({**given, x: 1})
        if n_given < level["min_condition_count"] or n_hit in (0, n_given):
            raise InvalidProblem("estimate would be undefined or trivial")
        return Problem(
            prompt=(
                f"The network structure and a dataset of {c.total} samples are shown below. "
                f"What is the maximum likelihood estimate of P({x}=1 | {assignment_text(given)})? "
                "Give a decimal to 3 places or a fraction."
            ),
            data={"names": names, "counts": counts, "target": x, "given": given},
            diagram=draw(dag),
            tables=[Table("Data (counts)", names + ["count"], [[str(v) for v in row] for row in counts])],
        )

    def solve(self, problem: Problem) -> float:
        c, x, given = self._unpack(problem)
        return c.count({**given, x: 1}) / c.count(given)

    def answer_options(self, problem: Problem, answer: float, rng: random.Random) -> list:
        c, x, given = self._unpack(problem)
        hit = c.count({**given, x: 1})
        options = [
            Option(hit / c.total, "used_joint"),
            Option(hit / c.count({x: 1}), "reversed_conditional"),
            Option(c.count({x: 1}) / c.total, "ignored_parents"),
            Option(c.count({**given, x: 0}) / c.count(given), "wrong_value"),
        ]
        rng.shuffle(options)
        near = [round(answer + d, 3) for d in (0.1, -0.1, 0.05, -0.05) if 0 < answer + d < 1]
        return options + near

    def explain(self, problem: Problem, answer: float) -> list:
        c, x, given = self._unpack(problem)
        n_given, n_hit = c.count(given), c.count({**given, x: 1})
        return [
            Step(f"Samples with {assignment_text(given)}", n_given, "add their counts", ask=True),
            Step(f"Of those, samples with {x}=1", n_hit, ask=True),
            Step(f"P({x}=1 | {assignment_text(given)})", answer, f"{n_hit}/{n_given}"),
        ]

    @staticmethod
    def _unpack(problem: Problem):
        d = problem.data
        return Counts(d["names"], d["counts"]), d["target"], {k: int(v) for k, v in d["given"].items()}


class Counts:
    """A table of counts over every assignment of binary variables."""

    def __init__(self, names: List[str], rows: List[List[int]]):
        self.names, self.rows = names, rows
        self.total = sum(r[-1] for r in rows)

    def count(self, fixed: Dict[str, int]) -> int:
        idx = {n: i for i, n in enumerate(self.names)}
        return sum(r[-1] for r in self.rows if all(r[idx[k]] == v for k, v in fixed.items()))
