"""Proof by contradiction with resolution (Classwork 2, 2.3).

Given CNF clauses KB1..KBn and a query α, add ¬α and search for the empty
clause. The worked solution numbers inferred clauses KBn+2, ... with the pair
of clauses each came from, as in the classwork's table.
"""
from __future__ import annotations

import random
import heapq
from typing import Dict, List, Optional, Tuple

from ..core import FILL_BLANK, MCQ, STEPS, Generator, InvalidProblem, Option, Param, Problem, Step, Table
from .sentence import (
    VAR_POOL, ResolveResult, atom_of, clause_text, complement, conj, disj, holds, iff, imp, is_valid_clause,
    lit, resolvents, to_cnf, worlds,
)

MISCONCEPTIONS = {
    "forgot_negation": "Adds α itself to the KB instead of ¬α.",
    "wrong_de_morgan": "Negates ¬(A ∧ B) as ¬A ∧ ¬B instead of ¬A ∨ ¬B.",
    "assumed_entailed": "Assumes the query follows without finding the empty clause.",
}
PARAMS = {
    "variables": Param("Propositions in the knowledge base", 3, 10),
    "min_steps": Param("Fewest resolution steps in the shortest proof found", 1, 10),
    "max_steps": Param("Most resolution steps in the shortest proof found", 1, 12),
    "distractor_rules": Param("Extra rules that aren't needed for the proof", 0, 8),
    "query_literals": Param("Literals in α (2 gives α = A ∧ ¬B, so ¬α needs De Morgan)", 1, 2),
    "provable_share": Param("Share of questions where KB ⊨ α is True", 0.0, 1.0),
}
LEVELS = {
    "easy": dict(variables=4, min_steps=2, max_steps=3, distractor_rules=1, query_literals=1, provable_share=0.7),
    "medium": dict(variables=5, min_steps=3, max_steps=4, distractor_rules=2, query_literals=1, provable_share=0.7),
    "hard": dict(variables=6, min_steps=4, max_steps=7, distractor_rules=3, query_literals=2, provable_share=0.7),
}
MAX_CLAUSES = 3000


def random_rule(rng: random.Random, names: List[str]) -> list:
    a, b, c = rng.sample(names, 3)
    return rng.choice([
        lambda: imp(lit(a), lit(b)),
        lambda: imp(conj(lit(a), lit(b)), lit(c)),
        lambda: imp(lit(a), disj(lit(b), lit(c))),
        lambda: iff(lit(a), lit(b)),
        lambda: imp(lit(a), lit(b, True)),
        lambda: disj(lit(a), lit(b)),
    ])()


def refute(kb: List[frozenset], negated: frozenset) -> Optional[List[Tuple[int, int, frozenset]]]:
    """Resolution from ¬α (set of support), shortest clauses first. Returns proof steps or None."""
    items = list(kb) + [negated]
    index: Dict[frozenset, int] = {c: i for i, c in enumerate(items)}
    parents: Dict[int, Tuple[int, int]] = {}
    queue = [(len(negated), len(items) - 1)]
    while queue and len(items) < MAX_CLAUSES:
        _, i = heapq.heappop(queue)
        for j in range(len(items)):
            for _, r in resolvents(items[i], items[j]):
                if is_valid_clause(r) or r in index:
                    continue
                index[r] = len(items)
                parents[len(items)] = (i, j)
                items.append(r)
                if not r:
                    return _extract(items, parents, len(items) - 1, len(kb) + 1)
                heapq.heappush(queue, (len(r), len(items) - 1))
    return None


def _extract(items, parents, goal, first_inferred) -> List[Tuple[int, int, frozenset]]:
    needed, stack = set(), [goal]
    while stack:
        k = stack.pop()
        if k >= first_inferred and k not in needed:
            needed.add(k)
            stack.extend(parents[k])
    order = sorted(needed)
    label = {k: first_inferred + n for n, k in enumerate(order)}
    rename = lambda k: label.get(k, k)
    return [(rename(parents[k][0]) + 1, rename(parents[k][1]) + 1, items[k]) for k in order]


class Refutation(Generator):
    id = "logic.resolution_refutation"
    summary = "Prove or disprove KB ⊨ α by adding ¬α and resolving clauses towards ∅."
    concepts = ("resolution", "proof-by-contradiction", "entailment", "propositional-logic")
    misconceptions = MISCONCEPTIONS
    formats = (STEPS, MCQ, FILL_BLANK)
    option_count = 2  # True / False
    params = PARAMS
    levels = LEVELS

    def generate(self, rng: random.Random, level) -> Problem:
        if level["min_steps"] > level["max_steps"]:
            raise ValueError("min_steps must not exceed max_steps")
        if level["variables"] < level["min_steps"] + level["query_literals"]:
            raise ValueError("need at least min_steps + query_literals variables")
        names = rng.sample(VAR_POOL, level["variables"])
        want = rng.random() < level["provable_share"]
        sentences, query = (self._provable if want else self._random)(rng, names, level)
        rng.shuffle(sentences)
        clauses: List[frozenset] = []
        for s in sentences:
            for c in to_cnf(s)[0]:
                if frozenset(c) not in clauses:
                    clauses.append(frozenset(c))
        negated = frozenset(complement(l) for l in query)
        units = {next(iter(c)) for c in clauses if len(c) == 1}
        if any(l in units or complement(l) in units for l in query):
            raise InvalidProblem("a fact already settles the query")
        all_names = sorted({atom_of(l) for c in clauses for l in c} | {atom_of(l) for l in query})
        kb_worlds = [w for w in worlds(all_names) if holds(clauses, w)]
        if not kb_worlds:
            raise InvalidProblem("KB is contradictory")
        entailed = all(not holds([negated], w) for w in kb_worlds)
        if entailed != want:
            raise InvalidProblem("rebalance")
        if entailed:
            proof = refute(clauses, negated)
            if proof is None or not level["min_steps"] <= len(proof) <= level["max_steps"]:
                raise InvalidProblem("proof length outside the requested range")
        alpha = " ∧ ".join(query)
        rows = [[f"KB{i}", clause_text(c)] for i, c in enumerate(clauses, start=1)]
        return Problem(
            prompt=(
                f"Using resolution (proof by contradiction), decide whether KB ⊨ α where α = {alpha}. "
                f"Add ¬α as KB{len(clauses) + 1} and search for the empty clause. Answer True or False."
            ),
            data={"kb": [sorted(c) for c in clauses], "query": query},
            tables=[Table("Knowledge base (CNF clauses)", ["Clause", ""], rows)],
        )

    @staticmethod
    def _random(rng, names, level):
        rules = [random_rule(rng, names) for _ in range(level["distractor_rules"] + level["min_steps"])]
        facts = [lit(n, rng.random() < 0.3) for n in rng.sample(names, level["query_literals"])]
        query = [n if rng.random() < 0.6 else "¬" + n for n in rng.sample(names, level["query_literals"])]
        return rules + facts, query

    @staticmethod
    def _provable(rng, names, level):
        """A chain of rules from a fact to each query literal, plus unrelated distractor rules."""
        room = len(names) - level["query_literals"] + 1
        chain = names[: max(2, min(room, rng.randint(level["min_steps"], level["max_steps"])))]
        sentences = [lit(chain[0])]
        for a, b in zip(chain, chain[1:]):
            sentences.append(rng.choice([imp(lit(a), lit(b)), iff(lit(a), lit(b)), disj(lit(a, True), lit(b))]))
        query = [chain[-1]]
        if level["query_literals"] > 1:
            # Second literal: a rule from somewhere on the chain to a negated conclusion.
            side = names[len(chain)]
            sentences.append(imp(lit(rng.choice(chain[:-1])), lit(side, True)))
            query.append("¬" + side)
        spare = [n for n in names if n not in chain]
        for _ in range(level["distractor_rules"]):
            if len(spare) >= 2:
                a, b = rng.sample(spare, 2)
                sentences.append(rng.choice([imp(lit(a), lit(b)), disj(lit(a), lit(rng.choice(chain)))]))
        return sentences, query

    def solve(self, problem: Problem) -> bool:
        kb, negated = self._unpack(problem)
        names = sorted({atom_of(l) for c in kb + [negated] for l in c})
        return all(not holds([negated], w) for w in worlds(names) if holds(kb, w))

    def answer_options(self, problem: Problem, answer: bool, rng: random.Random) -> list:
        return [Option(not answer, None if answer else "assumed_entailed")]

    def explain(self, problem: Problem, answer: bool) -> list:
        kb, negated = self._unpack(problem)
        n = len(kb) + 1
        query = problem.data["query"]
        how = "negate the single literal" if len(query) == 1 else "De Morgan: ¬(A ∧ B) ≡ ¬A ∨ ¬B"
        steps = [Step(f"KB{n} = ¬α", ResolveResult("clause", tuple(sorted(negated))), how, ask=True)]
        if answer:
            for i, j, c in refute(kb, negated):
                n += 1
                steps.append(Step(f"KB{n}", clause_text(c), f"resolve KB{i}, KB{j}"))
            steps.append(Step("Contradiction", work="the empty clause ∅ was derived, so KB ∧ ¬α is unsatisfiable"))
        else:
            names = sorted({atom_of(l) for c in kb + [negated] for l in c})
            world = next(w for w in worlds(names) if holds(kb + [negated], w))
            shown = ", ".join(f"{k}={'T' if v else 'F'}" for k, v in world.items())
            steps.append(Step("No contradiction", work=f"the world {shown} satisfies every clause and ¬α"))
        return steps

    @staticmethod
    def _unpack(problem: Problem):
        kb = [frozenset(c) for c in problem.data["kb"]]
        negated = frozenset(complement(l) for l in problem.data["query"])
        return kb, negated
