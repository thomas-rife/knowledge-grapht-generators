"""Convert a sentence to CNF clauses (Classwork 2, 2.2).

Any CNF equivalent to the right answer is accepted, so students can order or
group clauses however they like. Wrong options come from converting the same
sentence with a typical mistake.
"""
from __future__ import annotations

import random

from ..core import FILL_BLANK, MCQ, STEPS, Generator, Option, Param, Problem, Step
from .sentence import MISTAKES, VAR_POOL, CNFAnswer, conj, disj, iff, imp, lit, neg, text, to_cnf, var


FORMS = {
    "a => b | c": lambda a, b, c: imp(a, disj(b, c)),
    "a & b => c": lambda a, b, c: imp(conj(a, b), c),
    "a <=> b": lambda a, b, c: iff(a, b),
    "a => b & c": lambda a, b, c: imp(a, conj(b, c)),
    "a <=> b | c": lambda a, b, c: iff(a, disj(b, c)),
    "a <=> b & c": lambda a, b, c: iff(a, conj(b, c)),
    "a | b => c": lambda a, b, c: imp(disj(a, b), c),
    "a => ~b & ~c": lambda a, b, c: imp(a, conj(neg(b), neg(c))),
    "~(a & (b | c))": lambda a, b, c: neg(conj(a, disj(b, c))),
    "exactly one of a, b, c": lambda a, b, c: conj(
        imp(a, conj(neg(b), neg(c))), imp(b, conj(neg(a), neg(c))), imp(c, conj(neg(a), neg(b)))),
    "a & b <=> c": lambda a, b, c: iff(conj(a, b), c),
    "(a => b) & (b => a | c)": lambda a, b, c: conj(imp(a, b), imp(b, disj(a, c))),
    "~(a <=> b)": lambda a, b, c: neg(iff(a, b)),
}
PARAMS = {
    "forms": Param("Sentence shapes to convert (a, b, c are random propositions)", choices=tuple(FORMS)),
    "negation_prob": Param("Chance each proposition appears negated", 0.0, 0.6),
}
LEVELS = {
    "easy": dict(forms=["a => b | c", "a & b => c", "a <=> b", "a => b & c"], negation_prob=0.0),
    "medium": dict(forms=["a <=> b | c", "a <=> b & c", "a | b => c", "a => ~b & ~c", "~(a & (b | c))"], negation_prob=0.2),
    "hard": dict(forms=["exactly one of a, b, c", "a & b <=> c", "(a => b) & (b => a | c)", "~(a <=> b)", "a <=> b | c"],
                 negation_prob=0.25),
}


class CNFConversion(Generator):
    id = "logic.cnf_conversion"
    summary = "Convert a propositional sentence with ⇒, ⇔ and ¬ into CNF clauses."
    concepts = ("conjunctive-normal-form", "logical-equivalence", "propositional-logic")
    misconceptions = MISTAKES
    formats = (MCQ, FILL_BLANK, STEPS)
    params = PARAMS
    levels = LEVELS

    def generate(self, rng: random.Random, level) -> Problem:
        names = rng.sample(VAR_POOL, 3)
        a, b, c = [lit(n, rng.random() < level["negation_prob"]) for n in names]
        sentence = FORMS[rng.choice(level["forms"])](a, b, c)
        return Problem(
            prompt=(
                f"Convert {text(sentence)} into conjunctive normal form (CNF). "
                "Write the clauses joined by ∧, e.g. (¬A ∨ B) ∧ C."
            ),
            data={"sentence": sentence},
        )

    def solve(self, problem: Problem) -> CNFAnswer:
        return CNFAnswer(to_cnf(problem.data["sentence"])[0])

    def answer_options(self, problem: Problem, answer: CNFAnswer, rng: random.Random) -> list:
        s = problem.data["sentence"]
        # Specific mistakes first, so a shared wrong answer gets the more precise label.
        specific = [m for m in MISTAKES if m != "dropped_clause"]
        rng.shuffle(specific)
        options = [Option(CNFAnswer(to_cnf(s, m)[0]), m) for m in specific + ["dropped_clause"]]
        # Fillers: flip the sign of one literal in one clause.
        for i, clause in enumerate(answer.clauses):
            for j, l in enumerate(clause):
                flipped = l[1:] if l.startswith("¬") else "¬" + l
                new = list(answer.clauses)
                new[i] = tuple(sorted(clause[:j] + (flipped,) + clause[j + 1:]))
                options.append(CNFAnswer(tuple(new)))
        return options

    def explain(self, problem: Problem, answer: CNFAnswer) -> list:
        clauses, phases = to_cnf(problem.data["sentence"])
        steps = [Step(name, work=sentence) for name, sentence in phases]
        steps.append(Step("Number of clauses", len(clauses), ask=True))
        return steps
