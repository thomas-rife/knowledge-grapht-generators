"""Resolve two clauses (Classwork 2, 1.5).

Amenable? Inferred clause? ≡ T? ∅? Only ONE complementary pair may be
cancelled per resolution, which is the classic mistake this targets.
"""
from __future__ import annotations

import random

from ..core import FILL_BLANK, MCQ, STEPS, Generator, InvalidProblem, Option, Param, Problem, Step
from .sentence import ResolveResult, clause_text, complement, is_valid_clause, resolve

MISCONCEPTIONS = {
    "cancel_all_pairs": "Cancels several complementary pairs in one resolution.",
    "drop_shared_literal": "Treats a literal that appears in both clauses (same sign) as cancelling.",
    "empty_vs_valid": "Mixes up the empty clause (∅, contradiction) with a valid clause (T).",
    "missed_resolution": "Says the clauses can't be resolved even though they share a complementary pair.",
}
VARIABLES = {2: "XY", 3: "XYZ", 4: "WXYZ", 5: "UWXYZ"}
CASES = ("single", "double", "unit", "shared", "disjoint")
PARAMS = {
    "variables": Param("Propositions the clauses can use", 2, 5),
    "clause_size": Param("Most literals in each clause", 1, 4),
    "cases": Param(
        "Kinds of pair: single = one complementary pair, double = two (result is T), unit = X and ¬X (∅), "
        "shared = same literal in both (not resolvable), disjoint = nothing in common (not resolvable)",
        choices=CASES,
    ),
}
LEVELS = {
    "easy": dict(variables=3, clause_size=2, cases=["single", "unit", "shared", "disjoint"]),
    "medium": dict(variables=3, clause_size=3, cases=["single", "double", "unit", "shared", "disjoint"]),
    "hard": dict(variables=4, clause_size=3, cases=["single", "double", "shared"]),
}


class Resolution(Generator):
    id = "logic.resolution"
    summary = "Resolve two clauses: are they resolvable, and is the result a clause, T (valid) or ∅?"
    concepts = ("resolution", "clauses", "propositional-logic")
    misconceptions = MISCONCEPTIONS
    formats = (MCQ, FILL_BLANK, STEPS)
    params = PARAMS
    levels = LEVELS

    def generate(self, rng: random.Random, level) -> Problem:
        names, size = list(VARIABLES[level["variables"]]), level["clause_size"]
        case = rng.choice(level["cases"])
        if case == "double" and (size < 2 or len(names) < 2):
            raise InvalidProblem("double needs clauses of 2+ literals")

        def literal(n):
            return ("¬" if rng.random() < 0.4 else "") + n

        def extra(k, avoid):
            pool = [n for n in names if n not in avoid]
            return [literal(n) for n in rng.sample(pool, min(k, len(pool)))]

        if case == "unit":
            l = literal(rng.choice(names))
            c1, c2 = [l], [complement(l)]
        elif case in ("single", "double"):
            pairs = rng.sample(names, 2 if case == "double" else 1)
            first = [literal(n) for n in pairs]
            used = set(pairs)
            c1 = first + extra(rng.randint(0, size - len(first)), used)
            c2 = [complement(l) for l in first] + extra(rng.randint(0 if case == "double" else 1, size - len(first)), used)
        elif case == "shared":
            shared = literal(rng.choice(names))
            c1 = [shared] + extra(rng.randint(0, size - 1), {shared.lstrip("¬")})
            c2 = [shared] + extra(rng.randint(0, size - 1), {shared.lstrip("¬")} | {l.lstrip("¬") for l in c1})
        else:
            half = rng.sample(names, min(len(names), 2 * size))
            k = max(1, len(half) // 2)
            c1, c2 = [literal(n) for n in half[:k]], [literal(n) for n in half[k:]] or [literal(half[0])]
        c1, c2 = frozenset(c1), frozenset(c2)
        if is_valid_clause(c1) or is_valid_clause(c2) or not c2:
            raise InvalidProblem("input clause is already valid")
        if rng.random() < 0.5:
            c1, c2 = c2, c1
        return Problem(
            prompt=(
                f"resolve({clause_text(c1)}, {clause_text(c2)}): what is the inferred clause? "
                "Write - if the clauses can't be resolved, T if the result is valid, ∅ if it is the empty clause."
            ),
            data={"c1": sorted(c1), "c2": sorted(c2)},
        )

    def solve(self, problem: Problem) -> ResolveResult:
        return resolve(*self._clauses(problem))

    def answer_options(self, problem: Problem, answer: ResolveResult, rng: random.Random) -> list:
        c1, c2 = self._clauses(problem)
        options = []
        pairs = [l for l in c1 if complement(l) in c2]
        if len(pairs) > 1:
            rest = (c1 - set(pairs)) | (c2 - {complement(l) for l in pairs})
            options.append(Option(ResolveResult("clause", tuple(sorted(rest))) if rest else ResolveResult("empty"), "cancel_all_pairs"))
        shared = c1 & c2
        if shared:
            rest = (c1 | c2) - shared
            options.append(Option(ResolveResult("clause", tuple(sorted(rest))) if rest else ResolveResult("empty"), "drop_shared_literal"))
        if answer.kind == "empty":
            options.append(Option(ResolveResult("valid"), "empty_vs_valid"))
        if answer.kind == "valid":
            options.append(Option(ResolveResult("empty"), "empty_vs_valid"))
        if answer.kind != "none":
            options.append(Option(ResolveResult("none"), "missed_resolution"))
        # Generic fillers: keep everything, or the plausible-looking special answers.
        union = c1 | c2
        filler = [ResolveResult("clause", tuple(sorted(union))) if not is_valid_clause(union) else ResolveResult("valid"),
                  ResolveResult("none"), ResolveResult("empty"), ResolveResult("valid")]
        if answer.kind == "clause" and len(answer.literals) > 1:
            filler.append(ResolveResult("clause", answer.literals[:-1]))
        rng.shuffle(filler)
        return options + filler

    def explain(self, problem: Problem, answer: ResolveResult) -> list:
        c1, c2 = self._clauses(problem)
        pairs = sorted(l for l in c1 if complement(l) in c2)
        if not pairs:
            return [Step("Amenable?", False, "no proposition appears negated in one clause and plain in the other", ask=True)]
        l = pairs[0]
        rest = sorted((c1 - {l}) | (c2 - {complement(l)}))
        steps = [
            Step("Amenable?", True, f"{l} and {complement(l)} are complementary", ask=True),
            Step("Cancel one pair", work=f"remove {l} / {complement(l)}, keep {clause_text(rest)}"
                 + (" (still contains a complementary pair, so it is valid)" if answer.kind == "valid" else "")),
            Step("≡ T?", answer.kind == "valid", ask=True),
            Step("∅?", answer.kind == "empty", ask=True),
        ]
        if len(pairs) > 1:
            steps.insert(2, Step("Note", work="only ONE complementary pair can be cancelled per resolution"))
        return steps

    @staticmethod
    def _clauses(problem: Problem):
        return frozenset(problem.data["c1"]), frozenset(problem.data["c2"])
