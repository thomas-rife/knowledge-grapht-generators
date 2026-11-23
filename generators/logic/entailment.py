"""Models and entailment from a truth table (Classwork 2, 1.2-1.4).

"Does α ⊨ β?" with steps: M(α), M(β), is M(α) ⊆ M(β)? Worlds are numbered
w0, w1, ... with the first variable most significant, as in the classwork.
"""
from __future__ import annotations

import random

from ..core import FILL_BLANK, MCQ, STEPS, Generator, InvalidProblem, Option, Param, Problem, Step
from .sentence import conj, disj, evaluate, iff, imp, lit, models, text, worlds

VARIABLES = {2: ("X", "Y"), 3: ("X", "Y", "Z"), 4: ("W", "X", "Y", "Z")}
FORMS = ("literal", "clause", "and", "implies", "iff", "kb")
MISCONCEPTIONS = {
    "reversed_entailment": "Checks β ⊨ α (is M(β) ⊆ M(α)?) instead of α ⊨ β.",
    "overlap_means_entails": "Thinks sharing some models is enough, instead of every model of α being a model of β.",
}
PARAMS = {
    "variables": Param("Propositions in the truth table (2 = 4 rows, 3 = 8, 4 = 16)", 2, 4),
    "alpha_forms": Param("Shapes α can take (kb = two clauses joined by ∧)", choices=FORMS),
    "beta_forms": Param("Shapes β can take", choices=FORMS),
    "entailed_share": Param("Share of questions whose answer is True", 0.0, 1.0),
}
LEVELS = {
    "easy": dict(variables=2, alpha_forms=["and", "literal", "implies"], beta_forms=["clause", "literal"], entailed_share=0.5),
    "medium": dict(variables=3, alpha_forms=["and", "clause", "implies"], beta_forms=["clause", "implies", "literal"], entailed_share=0.5),
    "hard": dict(variables=3, alpha_forms=["kb", "iff", "implies"], beta_forms=["literal", "clause", "implies"], entailed_share=0.5),
}


def random_sentence(rng: random.Random, forms, names) -> list:
    def l(n=None):
        return lit(n or rng.choice(names), rng.random() < 0.35)

    def clause(k):
        return disj(*[l(n) for n in rng.sample(names, min(k, len(names)))])

    form = rng.choice(list(forms))
    if form == "literal":
        return l()
    if form == "clause":
        return clause(rng.randint(2, len(names)))
    if form == "kb":
        return conj(clause(2), clause(rng.randint(2, len(names))))
    a, b = rng.sample(names, 2)
    if form == "and":
        return conj(l(a), l(b))
    if form == "implies":
        return imp(l(a), l(b))
    return iff(lit(a), l(b))


class Entailment(Generator):
    id = "logic.entailment"
    summary = "Use a truth table to list the models of two sentences and decide whether one entails the other."
    concepts = ("entailment", "models", "truth-tables", "propositional-logic")
    misconceptions = MISCONCEPTIONS
    formats = (MCQ, FILL_BLANK, STEPS)
    option_count = 2  # True / False
    params = PARAMS
    levels = LEVELS

    def generate(self, rng: random.Random, level) -> Problem:
        names = VARIABLES[level["variables"]]
        alpha = random_sentence(rng, level["alpha_forms"], names)
        beta = random_sentence(rng, level["beta_forms"], names)
        ma, mb = set(models(alpha, names)), set(models(beta, names))
        if not ma or len(mb) == 2 ** len(names) or ma == mb:
            raise InvalidProblem("trivial pair")
        if (ma <= mb) != (rng.random() < level["entailed_share"]):
            raise InvalidProblem("rebalance")
        n = len(names)
        return Problem(
            prompt=(
                f"Let α = {text(alpha)} and β = {text(beta)}. Using a truth table over {', '.join(names)} "
                f"(worlds w0 = {'F' * n} to w{2 ** n - 1} = {'T' * n}), does α ⊨ β? Answer True or False."
            ),
            data={"alpha": alpha, "beta": beta, "names": list(names)},
        )

    def solve(self, problem: Problem) -> bool:
        a, b, names = self._unpack(problem)
        return set(models(a, names)) <= set(models(b, names))

    def answer_options(self, problem: Problem, answer: bool, rng: random.Random) -> list:
        a, b, names = self._unpack(problem)
        ma, mb = set(models(a, names)), set(models(b, names))
        if (mb <= ma) != answer:
            tag = "reversed_entailment"
        elif ma & mb and not answer:
            tag = "overlap_means_entails"
        else:
            tag = None
        return [Option(not answer, tag)]

    def explain(self, problem: Problem, answer: bool) -> list:
        a, b, names = self._unpack(problem)
        steps = []
        for i, w in enumerate(worlds(names)):
            tf = "".join("T" if w[n] else "F" for n in names)
            steps.append(Step(f"w{i} ({tf})", work=f"α = {'T' if evaluate(a, w) else 'F'}, β = {'T' if evaluate(b, w) else 'F'}"))
        ma, mb = models(a, names), models(b, names)
        missing = sorted(set(ma) - set(mb))
        steps += [
            Step("M(α)", ma, "worlds where α is true", ask=True),
            Step("M(β)", mb, "worlds where β is true", ask=True),
            Step("M(α) ⊆ M(β)?", answer,
                 "every model of α is a model of β" if answer else f"{', '.join(missing)} model α but not β",
                 ask=True),
        ]
        return steps

    @staticmethod
    def _unpack(problem: Problem):
        d = problem.data
        return d["alpha"], d["beta"], tuple(d["names"])
