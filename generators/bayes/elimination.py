"""Variable elimination: the same P(Q=1 | e) question, solved factor by factor.

Steps follow the textbook: restrict CPTs to the evidence, then for each hidden
variable multiply the factors that mention it and sum it out, then multiply
what's left and normalise.
"""
from __future__ import annotations

import random
from functools import reduce

from ..core import FILL_BLANK, MCQ, STEPS, InvalidProblem, Problem, Step
from .enumeration import Enumeration
from .network import BayesNet, assignment_text, cpt_factor


class VariableElimination(Enumeration):
    id = "bayes.variable_elimination"
    summary = "Compute P(Q | evidence) by variable elimination, eliminating hidden variables factor by factor."
    concepts = ("variable-elimination", "conditional-probability", "bayesian-networks")
    formats = (MCQ, FILL_BLANK, STEPS)
    method = "variable elimination"
    levels = {
        "easy": dict(nodes=3, evidence=1, edge_prob=0.5, max_parents=2),
        "medium": dict(nodes=4, evidence=1, edge_prob=0.5, max_parents=2),
        "hard": dict(nodes=5, evidence=2, edge_prob=0.5, max_parents=2),
    }

    def generate(self, rng: random.Random, level) -> Problem:
        if level["nodes"] - level["evidence"] < 2:
            raise ValueError("variable elimination needs a hidden variable: nodes - evidence must be at least 2")
        problem = super().generate(rng, level)
        net, q, e = self._unpack(problem)
        hidden = self.order(net, q, e)
        if not hidden:
            raise InvalidProblem("nothing to eliminate")
        problem.data["order"] = hidden
        problem.prompt = problem.prompt.replace(
            "by variable elimination.",
            f"by variable elimination, eliminating {hidden[0]}."
            if len(hidden) == 1
            else f"by variable elimination, eliminating {', '.join(hidden)} in that order.",
        )
        return problem

    @staticmethod
    def order(net: BayesNet, q: str, e: dict) -> list:
        """Eliminate hidden variables leaves-first (reverse topological order)."""
        return [n for n in reversed(net.dag.topological_order()) if n != q and n not in e]

    def explain(self, problem: Problem, answer: float) -> list:
        net, q, e = self._unpack(problem)
        factors = {f"P({n}{' | ' + ', '.join(net.parents(n)) if net.parents(n) else ''})": cpt_factor(net, n, e)
                   for n in net.dag.topological_order()}
        steps = [Step("Restrict CPTs to the evidence", work=f"fix {assignment_text(e)} in every CPT")]
        for i, var in enumerate(problem.data["order"], start=1):
            used = {name: f for name, f in factors.items() if var in f.variables}
            product_f = reduce(lambda a, b: a.multiply(b), used.values())
            new = product_f.sum_out(var)
            name = f"f{i}({', '.join(new.variables)})"
            for old in used:
                del factors[old]
            factors[name] = new
            steps.append(Step(
                f"Eliminate {var}",
                work=f"{name} = Σ_{var} {' · '.join(used)} = [{new.entries_text()}]",
            ))
        final = reduce(lambda a, b: a.multiply(b), factors.values())
        p1, p0 = final({q: 1}), final({q: 0})
        steps.append(Step(f"Unnormalised value for {q}=1", round(p1, 4),
                          f"multiply the remaining factors {', '.join(factors)}", ask=True))
        steps.append(Step(f"Unnormalised value for {q}=0", round(p0, 4), ask=True))
        steps.append(Step(f"P({q}=1 | {assignment_text(e)})", answer,
                          f"normalise {p1:.4f} / ({p1:.4f} + {p0:.4f})"))
        return steps
