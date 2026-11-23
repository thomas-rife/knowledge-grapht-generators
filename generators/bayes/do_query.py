"""Causal do-queries: P(Y=1 | do(X=x)) versus the observational P(Y=1 | X=x).

Intervening on X cuts the arrows into X. Adjusting for X's parents Z gives
    P(y | do(x)) = Σ_z P(y | x, z) P(z)
which differs from conditioning, P(y | x) = Σ_z P(y | x, z) P(z | x), whenever
Z confounds X and Y. The worked solution follows that adjustment formula.
"""
from __future__ import annotations

import random
from itertools import product

from ..core import FILL_BLANK, MCQ, STEPS, Generator, InvalidProblem, Option, Param, Problem, Step
from ..graphs import DAG, draw, random_dag
from .network import BayesNet, assignment_text, random_net

MISCONCEPTIONS = {
    "used_observational": "Conditions on X=x (P(Y | X=x)) instead of intervening, so confounding through X's parents leaks in.",
    "posterior_weights": "Weights by P(z | x) instead of P(z): that is the observational answer again.",
    "ignored_intervention": "Ignores X entirely and gives P(Y=1).",
    "wrong_value": "Computes P(Y=0 | do(X=x)) instead of P(Y=1 | do(X=x)).",
}
PARAMS = {
    "nodes": Param("Variables in the network", 3, 6),
    "edge_prob": Param("Chance of each possible edge", 0.3, 0.9),
    "max_parents": Param("Most parents any node can have (also the size of the adjustment set)", 1, 3),
    "min_confounding": Param("Smallest required gap between P(y | do(x)) and P(y | x); 0 allows no confounding", 0.0, 0.3),
}
LEVELS = {
    "easy": dict(nodes=3, edge_prob=0.7, max_parents=2, min_confounding=0.03),
    "medium": dict(nodes=4, edge_prob=0.6, max_parents=2, min_confounding=0.03),
    "hard": dict(nodes=5, edge_prob=0.5, max_parents=3, min_confounding=0.03),
}


def do_prob(net: BayesNet, y: str, x: str, xv: int) -> float:
    """P(Y=1 | do(X=xv)) by adjusting for X's parents."""
    if y not in net.dag.descendants(x):
        return net.prob({y: 1})  # intervening on X can't change its non-descendants
    z = net.parents(x)
    total = 0.0
    for row in product((0, 1), repeat=len(z)):
        zz = dict(zip(z, row))
        total += net.prob({y: 1}, {x: xv, **zz}) * (net.marginal(zz) if zz else 1.0)
    return total


class DoQuery(Generator):
    id = "bayes.do_query"
    summary = "Compute a causal effect P(Y | do(X)) by adjusting for X's parents, versus conditioning on X."
    concepts = ("interventions", "do-calculus", "confounding", "causal-inference")
    misconceptions = MISCONCEPTIONS
    formats = (MCQ, FILL_BLANK, STEPS)
    abs_tol = 0.002
    params = PARAMS
    levels = LEVELS

    def generate(self, rng: random.Random, level) -> Problem:
        if level["max_parents"] < 2 and level["min_confounding"] > 0:
            raise ValueError("confounding needs max_parents ≥ 2 (Z → X → Y with Z → Y); or set min_confounding to 0")
        dag = random_dag(rng, level["nodes"], level["edge_prob"], max_parents=level["max_parents"])
        net = random_net(rng, dag)
        queries = []
        for x in dag.nodes:
            if not dag.parents(x):
                continue
            for y in sorted(dag.descendants(x)):
                for xv in (0, 1):
                    gap = abs(do_prob(net, y, x, xv) - net.prob({y: 1}, {x: xv}))
                    if gap >= level["min_confounding"]:
                        queries.append((x, y, xv))
        if not queries:
            raise InvalidProblem("no confounded query")
        x, y, xv = rng.choice(queries)
        return Problem(
            prompt=(
                f"Using the network and CPTs below, compute the causal effect P({y}=1 | do({x}={xv})). "
                f"Intervening sets {x}={xv} and cuts the arrows into {x}. Give your answer to 3 decimal places."
            ),
            data={"net": net.to_dict(), "x": x, "y": y, "xv": xv},
            diagram=draw(dag, observed=[x], query=y),
            tables=net.cpt_tables(),
        )

    def solve(self, problem: Problem) -> float:
        net, x, y, xv = self._unpack(problem)
        return do_prob(net, y, x, xv)

    def answer_options(self, problem: Problem, answer: float, rng: random.Random) -> list:
        net, x, y, xv = self._unpack(problem)
        options = [
            Option(net.prob({y: 1}, {x: xv}), "used_observational"),
            Option(net.prob({y: 1}), "ignored_intervention"),
            Option(1 - answer, "wrong_value"),
        ]
        rng.shuffle(options)
        return options + [round(answer + d, 3) for d in (0.1, -0.1, 0.05, -0.05) if 0 < answer + d < 1]

    def explain(self, problem: Problem, answer: float) -> list:
        net, x, y, xv = self._unpack(problem)
        z = net.parents(x)
        cut = ", ".join(f"{p} → {x}" for p in z)
        steps = [
            Step("Cut arrows into X", work=f"remove {cut}; {x} is now fixed at {xv}"),
            Step("Adjustment set", z, f"the parents of {x} block every back-door path", ask=True),
        ]
        terms = []
        for row in product((0, 1), repeat=len(z)):
            zz = dict(zip(z, row))
            pz = net.marginal(zz)
            py = net.prob({y: 1}, {x: xv, **zz})
            steps.append(Step(f"P({assignment_text(zz)})", round(pz, 4), ask=True))
            steps.append(Step(f"P({y}=1 | {x}={xv}, {assignment_text(zz)})", round(py, 4), ask=True))
            terms.append(f"{py:.4g}×{pz:.4g}")
        steps.append(Step(f"P({y}=1 | do({x}={xv}))", answer, " + ".join(terms)))
        steps.append(Step("Compare: observational", round(net.prob({y: 1}, {x: xv}), 4),
                          f"P({y}=1 | {x}={xv}) weights by P(z | x) instead, so it differs"))
        return steps

    @staticmethod
    def _unpack(problem: Problem):
        d = problem.data
        return BayesNet.from_dict(d["net"]), d["x"], d["y"], int(d["xv"])
