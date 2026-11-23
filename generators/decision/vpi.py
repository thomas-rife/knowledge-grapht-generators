"""Value of perfect information (Classwork 4, Problem 3).

VPI(X | e) = Σ_x P(x | e) MEU(x, e) − MEU(e): how much knowing X before
deciding is worth, i.e. a fair price for the information.
"""
from __future__ import annotations

import random

from ..core import FILL_BLANK, MCQ, STEPS, Generator, InvalidProblem, Option, Param, Problem, Step
from .meu import LEVELS as MEU_LEVELS
from .meu import PARAMS as MEU_PARAMS
from .meu import eu_steps, pick_evidence
from .network import DECISION, DecisionNet, evidence_text, random_decision_net

MISCONCEPTIONS = {
    "forgot_subtract": "Stops at MEU(X, e) and forgets to subtract MEU(e).",
    "prior_weights": "Weights MEU(x, e) by the prior P(x) instead of P(x | e).",
    "unweighted_average": "Averages MEU(X=0, e) and MEU(X=1, e) without weighting by P(x | e).",
    "best_case": "Uses the best outcome max_x MEU(x, e) instead of the expectation.",
    "reversed_difference": "Subtracts the wrong way round, giving a negative value (VPI is never negative).",
}
PARAMS = dict(MEU_PARAMS)
PARAMS.pop("min_gap")
PARAMS["zero_share"] = Param("Share of questions where the information is worthless (VPI = 0)", 0.0, 1.0)
LEVELS = {k: {**{p: v for p, v in lv.items() if p != "min_gap"}, "zero_share": 0.15} for k, lv in MEU_LEVELS.items()}
LEVELS["easy"]["evidence"] = 0
LEVELS["easy"]["chance_nodes"] = 2


def vpi_parts(dn: DecisionNet, x: str, e):
    meu_e = dn.meu(e)[0]
    px = {v: dn.net.prob({x: v}, e) for v in (0, 1)}
    meu_x = {v: dn.meu({**e, x: v})[0] for v in (0, 1)}
    meu_X = sum(px[v] * meu_x[v] for v in (0, 1))
    return meu_e, px, meu_x, meu_X


class ValueOfInformation(Generator):
    id = "decision.vpi"
    summary = "Compute the value of perfect information: how much knowing a variable before deciding is worth."
    concepts = ("value-of-perfect-information", "decision-networks", "maximum-expected-utility")
    misconceptions = MISCONCEPTIONS
    formats = (MCQ, FILL_BLANK, STEPS)
    abs_tol = 0.05
    params = PARAMS
    levels = LEVELS

    def generate(self, rng: random.Random, level) -> Problem:
        if level["evidence"] + level["decision_children"] + 1 > level["chance_nodes"]:
            raise ValueError("need chance_nodes ≥ evidence + decision_children + 1 (something observable to learn)")
        dn = random_decision_net(rng, level)
        evidence = pick_evidence(rng, dn, level["evidence"])
        after = dn.net.dag.descendants(DECISION)
        candidates = [n for n in dn.chance if n not in evidence and n not in after]
        if not candidates:
            raise InvalidProblem("nothing to learn")
        x = rng.choice(candidates)
        meu_e, _, _, meu_X = vpi_parts(dn, x, evidence)
        vpi = meu_X - meu_e
        want_zero = rng.random() < level["zero_share"]
        if (want_zero and vpi > 0.01) or (not want_zero and vpi < 1):
            raise InvalidProblem("rebalance")
        e_txt = evidence_text(evidence)
        return Problem(
            prompt=(
                f"In the decision network below, compute VPI({x}{' | ' + e_txt if e_txt else ''}): the value of "
                f"learning {x} before choosing D{', given ' + e_txt if e_txt else ''}. If utilities are dollars, "
                "this is a fair price for the information."
            ),
            data={"dn": dn.to_dict(), "evidence": evidence, "x": x},
            diagram=dn.diagram(observed=evidence, query=x),
            tables=dn.tables(),
        )

    def solve(self, problem: Problem) -> float:
        dn, e, x = self._unpack(problem)
        meu_e, _, _, meu_X = vpi_parts(dn, x, e)
        return round(meu_X - meu_e, 4)

    def answer_options(self, problem: Problem, answer: float, rng: random.Random) -> list:
        dn, e, x = self._unpack(problem)
        meu_e, px, meu_x, meu_X = vpi_parts(dn, x, e)
        prior = {v: dn.net.prob({x: v}) for v in (0, 1)}
        options = [
            Option(round(meu_X, 4), "forgot_subtract"),
            Option(round(sum(prior[v] * meu_x[v] for v in (0, 1)) - meu_e, 4), "prior_weights"),
            Option(round((meu_x[0] + meu_x[1]) / 2 - meu_e, 4), "unweighted_average"),
            Option(round(max(meu_x.values()) - meu_e, 4), "best_case"),
        ]
        if answer > 0:
            options.append(Option(round(-answer, 4), "reversed_difference"))
        rng.shuffle(options)
        return options + [round(answer + k, 4) for k in (5, 10, 2.5) if answer + k >= 0]

    def explain(self, problem: Problem, answer: float) -> list:
        dn, e, x = self._unpack(problem)
        meu_e, px, meu_x, meu_X = vpi_parts(dn, x, e)
        e_txt = evidence_text(e)
        steps = [Step(f"MEU({e_txt or '∅'})", round(meu_e, 4),
                      f"max of EU(D=0) = {dn.meu(e)[2][0]:.4g}, EU(D=1) = {dn.meu(e)[2][1]:.4g}", ask=True)]
        for v in (0, 1):
            given = f"{x}={v}" + (f", {e_txt}" if e_txt else "")
            steps.append(Step(f"P({x}={v}{' | ' + e_txt if e_txt else ''})", round(px[v], 4), ask=True))
            eus = dn.meu({**e, x: v})[2]
            steps.append(Step(f"MEU({given})", round(meu_x[v], 4),
                              f"max of EU(D=0) = {eus[0]:.4g}, EU(D=1) = {eus[1]:.4g}", ask=True))
        steps.append(Step(f"MEU({x}{', ' + e_txt if e_txt else ''})", round(meu_X, 4),
                          f"{px[0]:.4g}×{meu_x[0]:.4g} + {px[1]:.4g}×{meu_x[1]:.4g}", ask=True))
        steps.append(Step("VPI", answer, f"{meu_X:.4g} − {meu_e:.4g}"))
        return steps

    @staticmethod
    def _unpack(problem: Problem):
        d = problem.data
        return DecisionNet.from_dict(d["dn"]), {k: int(v) for k, v in d["evidence"].items()}, d["x"]
