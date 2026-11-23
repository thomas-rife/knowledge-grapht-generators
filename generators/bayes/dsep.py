"""D-separation: "Given the shaded nodes, which nodes are d-separated from X?"

Wrong answers come from running the same solver with a misconception, so a
wrong pick (or a wrong typed answer) tells you which mistake the student made.
"""
from __future__ import annotations

import random
from itertools import combinations
from typing import FrozenSet, Iterable, List, Optional

from ..core import Generator, InvalidProblem, Option, Param, Problem, Step
from ..graphs import DAG, describe_path, draw, random_dag, undirected_paths

CORRECT = "correct"
MISCONCEPTIONS = {
    "observed_collider_blocks": "Treats a collider like a chain: thinks observing it blocks the path.",
    "ignores_collider_descendants": "Forgets that observing a descendant of a collider opens the path.",
    "connected_means_dependent": "Thinks any connecting path means dependence, whatever is observed.",
}
PARAMS = {
    "nodes": Param("Number of variables in the network", 3, 8),
    "edge_prob": Param("Chance of each possible edge (higher = denser network)", 0.15, 0.8),
    "max_parents": Param("Most parents any node can have", 1, 4),
    "max_observed": Param("Most observed (shaded) nodes", 0, 3),
    "collider_trap": Param("1 = only ask queries where a collider mistake changes the answer", 0, 1),
}
LEVELS = {
    "easy": dict(nodes=5, edge_prob=0.35, max_parents=2, max_observed=1, collider_trap=1),
    "medium": dict(nodes=6, edge_prob=0.35, max_parents=3, max_observed=2, collider_trap=1),
    "hard": dict(nodes=7, edge_prob=0.4, max_parents=3, max_observed=2, collider_trap=1),
}


# ---- solver ------------------------------------------------------------------
def blocker(dag: DAG, path: List[str], observed: FrozenSet[str], rule: str = CORRECT) -> Optional[str]:
    """The node that blocks this path, or None if the path is active."""
    for a, b, c in zip(path, path[1:], path[2:]):
        collider = dag.has_edge(a, b) and dag.has_edge(c, b)
        if rule == "connected_means_dependent":
            active = True
        elif not collider:
            active = b not in observed
        elif rule == "observed_collider_blocks":
            active = b not in observed
        elif rule == "ignores_collider_descendants":
            active = b in observed
        else:
            active = b in observed or bool(dag.descendants(b) & observed)
        if not active:
            return b
    return None


def separated_from(dag: DAG, x: str, observed: Iterable[str], rule: str = CORRECT) -> List[str]:
    """Every unobserved node d-separated from x."""
    obs = frozenset(observed)
    return sorted(
        y for y in dag.nodes
        if y != x and y not in obs
        and all(blocker(dag, p, obs, rule) for p in undirected_paths(dag, x, y))
    )


# ---- generator ----------------------------------------------------------------
class DSeparation(Generator):
    id = "bayes.d_separation"
    summary = "Decide which nodes are d-separated from a query node given the observed (shaded) nodes."
    concepts = ("d-separation", "conditional-independence", "bayesian-networks")
    misconceptions = MISCONCEPTIONS
    params = PARAMS
    levels = LEVELS

    def generate(self, rng: random.Random, level) -> Problem:
        dag = random_dag(rng, level["nodes"], level["edge_prob"], max_parents=level["max_parents"])
        if level["collider_trap"] and not dag.colliders():
            raise InvalidProblem("needs a collider")

        def trap(x, given):
            """A collider mistake gives a different answer."""
            return any(
                separated_from(dag, x, given, r) != separated_from(dag, x, given)
                for r in ("observed_collider_blocks", "ignores_collider_descendants")
            )

        queries = [
            (x, given)
            for x in dag.nodes
            for k in range(level["max_observed"] + 1)
            for given in combinations([n for n in dag.nodes if n != x], k)
            if separated_from(dag, x, given) and (not level["collider_trap"] or trap(x, given))
        ]
        if not queries:
            raise InvalidProblem("no interesting query")
        x, given = rng.choice(queries)
        shaded = f"{' and '.join(given)} {'is' if len(given) == 1 else 'are'} observed (shaded)" if given else "nothing is observed"
        return Problem(
            prompt=f"In the Bayesian network below, {shaded}. Which nodes are d-separated from {x}?",
            data={"dag": dag.to_dict(), "query": x, "observed": list(given)},
            diagram=draw(dag, observed=given, query=x),
        )

    def solve(self, problem: Problem) -> List[str]:
        d = problem.data
        return separated_from(DAG.from_dict(d["dag"]), d["query"], d["observed"])

    def answer_options(self, problem: Problem, answer: List[str], rng: random.Random) -> list:
        d = problem.data
        dag = DAG.from_dict(d["dag"])
        options = [Option(separated_from(dag, d["query"], d["observed"], r), r) for r in MISCONCEPTIONS]
        # Near misses (one node added or dropped) top up the list.
        candidates = [n for n in dag.nodes if n != d["query"] and n not in d["observed"]]
        near = [sorted(set(answer) ^ {n}) for n in candidates]
        rng.shuffle(near)
        return options + near

    def explain(self, problem: Problem, answer: List[str]) -> list:
        d = problem.data
        dag, x, obs = DAG.from_dict(d["dag"]), d["query"], frozenset(d["observed"])
        steps = []
        for y in dag.nodes:
            if y == x or y in obs:
                continue
            paths = undirected_paths(dag, x, y)
            active = next((p for p in paths if not blocker(dag, p, obs)), None)
            if active:
                steps.append(Step(y, "dependent", f"active path {describe_path(dag, active)}"))
            else:
                example = paths[0]
                steps.append(Step(y, "d-separated",
                                  f"all {len(paths)} path(s) blocked, e.g. {describe_path(dag, example)} at {blocker(dag, example, obs)}"))
        return steps
