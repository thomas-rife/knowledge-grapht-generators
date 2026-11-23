"""Inference by enumeration: "Compute P(Q=1 | evidence) from the network and its CPTs." """
from __future__ import annotations

import random
from itertools import combinations, product

from ..core import FILL_BLANK, MCQ, STEPS, Generator, InvalidProblem, Option, Param, Problem, Step
from ..graphs import draw, random_dag
from .network import BayesNet, assignment_text, needed_variables, random_net, term_text

MISCONCEPTIONS = {
    "forgot_normalization": "Stops at the joint P(Q=1, e) and forgets to normalise by P(e).",
    "reversed_conditional": "Computes P(e | Q=1) instead of P(Q=1 | e).",
    "ignored_evidence": "Ignores the evidence and gives the prior P(Q=1).",
    "wrong_value": "Computes the probability of Q=0 instead of Q=1.",
}
PARAMS = {
    "nodes": Param("Number of variables in the network", 2, 6),
    "evidence": Param("Number of evidence variables", 1, 4),
    "edge_prob": Param("Chance of each possible edge (higher = denser network)", 0.2, 0.9),
    "max_parents": Param("Most parents any node can have (CPT size grows as 2^parents)", 1, 3),
}
LEVELS = {
    "easy": dict(nodes=3, evidence=1, edge_prob=0.5, max_parents=2),
    "medium": dict(nodes=4, evidence=1, edge_prob=0.5, max_parents=2),
    "hard": dict(nodes=4, evidence=2, edge_prob=0.5, max_parents=2),
}


class Enumeration(Generator):
    id = "bayes.enumeration"
    summary = "Compute P(Q | evidence) from a Bayes net's CPTs by enumeration, using only the CPTs needed."
    concepts = ("inference-by-enumeration", "conditional-probability", "bayesian-networks")
    misconceptions = MISCONCEPTIONS
    formats = (MCQ, FILL_BLANK, STEPS)
    abs_tol = 0.002
    method = "enumeration"
    params = PARAMS
    levels = LEVELS

    def generate(self, rng: random.Random, level) -> Problem:
        if level["evidence"] >= level["nodes"]:
            raise ValueError("evidence must be smaller than nodes")
        dag = random_dag(rng, level["nodes"], level["edge_prob"], max_parents=level["max_parents"])
        net = random_net(rng, dag)
        queries = []
        for q in net.dag.nodes:
            others = [n for n in net.dag.nodes if n != q]
            for names in combinations(others, level["evidence"]):
                for values in product((0, 1), repeat=len(names)):
                    evidence = dict(zip(names, values))
                    lookup = bool(net.parents(q)) and set(net.parents(q)) == set(names)
                    matters = abs(net.prob({q: 1}, evidence) - net.prob({q: 1})) >= 0.02
                    if not lookup and matters:
                        queries.append((q, evidence))
        if not queries:
            raise InvalidProblem("no interesting query")
        q, evidence = rng.choice(queries)
        return Problem(
            prompt=(
                f"Using the network and CPTs below, compute P({q}=1 | {assignment_text(evidence)}) "
                f"by {self.method}. Give your answer to 3 decimal places."
            ),
            data={"net": net.to_dict(), "query": q, "evidence": evidence},
            diagram=draw(net.dag, observed=evidence, query=q),
            tables=net.cpt_tables(),
        )

    def solve(self, problem: Problem) -> float:
        net, q, e = self._unpack(problem)
        return net.prob({q: 1}, e)

    def answer_options(self, problem: Problem, answer: float, rng: random.Random) -> list:
        return inference_options(*self._unpack(problem), answer, rng)

    def explain(self, problem: Problem, answer: float) -> list:
        net, q, e = self._unpack(problem)
        hidden = [n for n in net.dag.nodes if n != q and n not in e]
        needed = needed_variables(net, [q, *e])
        summed = [n for n in hidden if n in needed]
        dropped = [n for n in hidden if n not in needed]
        steps = [
            Step("Label the variables", work=f"Q = {{{q}}}, e = {{{assignment_text(e)}}}, Y = {{{', '.join(hidden) or '∅'}}}"),
            Step("CPTs needed", needed,
                 "Q, e and their ancestors" + (f"; {', '.join(dropped)} {'sums' if len(dropped) == 1 else 'sum'} out to 1" if dropped else ""), ask=True),
        ]
        for value in (1, 0):
            total = 0.0
            for row in product((0, 1), repeat=len(summed)):
                a = {**e, q: value, **dict(zip(summed, row))}
                names, numbers, term = term_text(net, a, only=needed)
                steps.append(Step(f"P({assignment_text(a)})", term, f"{names} = {numbers}"))
                total += term
            work = f"sum over {', '.join(summed)}" if summed else "no hidden variables left to sum"
            steps.append(Step(f"P({q}={value}, {assignment_text(e)})", round(total, 4), work, ask=True))
        p1, p0 = net.marginal({**e, q: 1}), net.marginal({**e, q: 0})
        steps.append(Step(f"P({assignment_text(e)})", round(p1 + p0, 4), f"{p1:.4f} + {p0:.4f}", ask=True))
        steps.append(Step(f"P({q}=1 | {assignment_text(e)})", answer, f"{p1:.4f} / {p1 + p0:.4f}"))
        return steps

    @staticmethod
    def _unpack(problem: Problem):
        d = problem.data
        return BayesNet.from_dict(d["net"]), d["query"], {k: int(v) for k, v in d["evidence"].items()}


def inference_options(net: BayesNet, q: str, e: dict, answer: float, rng: random.Random) -> list:
    """Wrong answers for any P(Q=1 | e) question, shared by enumeration and elimination."""
    options = [
        Option(net.marginal({**e, q: 1}), "forgot_normalization"),
        Option(net.marginal({**e, q: 1}) / net.marginal({q: 1}), "reversed_conditional"),
        Option(net.prob({q: 1}), "ignored_evidence"),
        Option(1 - answer, "wrong_value"),
    ]
    rng.shuffle(options)
    near = [round(answer + d, 3) for d in (0.1, -0.1, 0.05, -0.05) if 0 < answer + d < 1]
    return options + near
