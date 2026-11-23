"""Maximum expected utility in a decision network (Classwork 4, Problem 2).

Steps: label Q / e / D / Y, find P(S | do(D=d), e), then EU(d | e) for each
decision, then MEU(e) = max_d EU(d | e) and d*.
"""
from __future__ import annotations

import random
from typing import Dict, List

from ..core import FILL_BLANK, MCQ, STEPS, Generator, InvalidProblem, Option, Param, Problem, Step
from .network import DECISION, DecisionNet, evidence_text, outcome_text, random_decision_net

MISCONCEPTIONS = {
    "picked_lower_eu": "Takes the smaller expected utility instead of the larger.",
    "ignored_evidence": "Computes expected utilities without conditioning on the evidence.",
    "used_joint": "Weights utilities by the joint P(s, e | do(d)) instead of the conditional P(s | e, do(d)).",
    "averaged_decisions": "Averages the expected utilities of the decisions instead of taking the best one.",
}
PARAMS = {
    "chance_nodes": Param("Chance variables in the network", 2, 5),
    "edge_prob": Param("Chance of each possible edge between chance nodes", 0.3, 0.9),
    "max_parents": Param("Most parents any chance node can have", 1, 3),
    "utility_parents": Param("Chance variables the utility depends on (besides D)", 1, 2),
    "decision_children": Param("Chance variables the decision affects (0 = D only affects U, as in Classwork 4)", 0, 2),
    "evidence": Param("Observed chance variables", 0, 2),
    "min_gap": Param("Smallest allowed difference between EU(D=0) and EU(D=1)", 0, 30),
}
LEVELS = {
    "easy": dict(chance_nodes=2, edge_prob=0.6, max_parents=2, utility_parents=1, decision_children=0, evidence=1, min_gap=5),
    "medium": dict(chance_nodes=3, edge_prob=0.6, max_parents=2, utility_parents=1, decision_children=0, evidence=1, min_gap=5),
    "hard": dict(chance_nodes=4, edge_prob=0.5, max_parents=2, utility_parents=2, decision_children=1, evidence=2, min_gap=3),
}


def pick_evidence(rng: random.Random, dn: DecisionNet, count: int, avoid=()) -> Dict[str, int]:
    """Observed variables must be known before deciding, so never descendants of D."""
    after = dn.net.dag.descendants(DECISION)
    pool = [n for n in dn.chance if n not in after and n not in avoid]
    if len(pool) < count:
        raise InvalidProblem("not enough observable variables")
    return {n: rng.randint(0, 1) for n in rng.sample(pool, count)}


def eu_steps(dn: DecisionNet, evidence: Dict[str, int], ask: bool, label_suffix: str = "") -> List[Step]:
    """P(S | do(d), e) and EU(d | e) for both decisions, as in Classwork 4, 2.1-2.2."""
    e_txt = evidence_text(evidence)
    given = f" | {e_txt}" if e_txt else ""
    steps = []
    independent = not dn.decision_children()
    for d in ((0,) if independent else (0, 1)):
        for s, p, _ in dn.eu(d, evidence)[1]:
            if not s:
                continue
            do = "" if independent else f"do(D={d}), "
            cond = f" | {do}{e_txt}" if (do or e_txt) else ""
            steps.append(Step(f"P({outcome_text(s)}{cond.rstrip(', ')})", round(p, 4),
                              "same for both decisions: D has no chance children" if independent else "", ask=ask))
    for d in (0, 1):
        eu, terms = dn.eu(d, evidence)
        work = " + ".join(f"{p:.4g}×{u:g}" for _, p, u in terms)
        steps.append(Step(f"EU(D={d}{given}){label_suffix}", round(eu, 4), work, ask=ask))
    return steps


class MaximumExpectedUtility(Generator):
    id = "decision.meu"
    summary = "Find the maximum expected utility and best decision in a decision network given evidence."
    concepts = ("decision-networks", "expected-utility", "maximum-expected-utility")
    misconceptions = MISCONCEPTIONS
    formats = (MCQ, FILL_BLANK, STEPS)
    abs_tol = 0.05
    params = PARAMS
    levels = LEVELS

    def generate(self, rng: random.Random, level) -> Problem:
        if level["evidence"] >= level["chance_nodes"]:
            raise ValueError("evidence must be smaller than chance_nodes")
        dn = random_decision_net(rng, level)
        evidence = pick_evidence(rng, dn, level["evidence"])
        if not any(dn.outcomes(evidence)[0]):
            raise InvalidProblem("every utility parent is observed")
        _, _, eus = dn.meu(evidence)
        if abs(eus[0] - eus[1]) < level["min_gap"]:
            raise InvalidProblem("decisions too close")
        e_txt = evidence_text(evidence)
        target = f"MEU({e_txt})" if e_txt else "MEU(∅), with no evidence"
        return Problem(
            prompt=(
                f"In the decision network below (chance nodes in circles, decision D, utility U), find {target}: "
                "the maximum expected utility. Use the CPTs and utility table."
            ),
            data={"dn": dn.to_dict(), "evidence": evidence},
            diagram=dn.diagram(observed=evidence),
            tables=dn.tables(),
        )

    def solve(self, problem: Problem) -> float:
        dn, e = self._unpack(problem)
        return round(dn.meu(e)[0], 4)

    def answer_options(self, problem: Problem, answer: float, rng: random.Random) -> list:
        dn, e = self._unpack(problem)
        _, _, eus = dn.meu(e)
        options = [
            Option(round(min(eus.values()), 4), "picked_lower_eu"),
            Option(round((eus[0] + eus[1]) / 2, 4), "averaged_decisions"),
        ]
        if e:
            options.append(Option(round(dn.meu({})[0], 4), "ignored_evidence"))
            joint = []
            for d in (0, 1):
                p_e = dn.net.marginal({**e, DECISION: d}) / dn.net.marginal({DECISION: d})
                joint.append(sum(p * p_e * u for _, p, u in dn.eu(d, e)[1]))
            options.append(Option(round(max(joint), 4), "used_joint"))
        rng.shuffle(options)
        return options + [round(answer + k, 4) for k in (5, -5, 10, -10)]

    def explain(self, problem: Problem, answer: float) -> list:
        dn, e = self._unpack(problem)
        S = [p for p in dn.utility_parents if p not in e]
        hidden = [n for n in dn.chance if n not in S and n not in e]
        best, d_star, eus = dn.meu(e)
        steps = [Step("Label the variables",
                      work=f"Q = {{{', '.join(S)}}}, e = {{{evidence_text(e) or '∅'}}}, D = {{D}}, Y = {{{', '.join(hidden) or '∅'}}}")]
        steps += eu_steps(dn, e, ask=True)
        steps.append(Step("d*", d_star, f"argmax_d EU: EU(D=0) = {eus[0]:.4g}, EU(D=1) = {eus[1]:.4g}", ask=True))
        return steps

    @staticmethod
    def _unpack(problem: Problem):
        d = problem.data
        return DecisionNet.from_dict(d["dn"]), {k: int(v) for k, v in d["evidence"].items()}
