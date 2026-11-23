"""Decision networks: chance nodes, one binary decision D and a utility node U.

The decision is a root of the chance network, so P(S | do(D=d), e) equals
P(S | D=d, e): intervening on a node with no parents is the same as
conditioning on it. D may have chance children (then the decision changes
the probabilities) or none (as in Classwork 4, where only U depends on D).
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from itertools import product
from typing import Dict, List, Mapping, Optional, Tuple

from ..core import Diagram, Table
from ..graphs import DAG, draw, random_dag
from ..bayes.network import BayesNet, CPT_VALUES

DECISION, UTILITY = "D", "U"
CHANCE_NAMES = "ABCEGHJK"  # skips D (decision) and U (utility)


@dataclass
class DecisionNet:
    net: BayesNet  # chance nodes plus the decision as a root (its prior is never used)
    utility_parents: Tuple[str, ...]  # chance parents of U, sorted; D is always a parent too
    utility: Dict[Tuple[int, ...], float]  # (chance parent values..., d) -> utility

    @property
    def chance(self) -> List[str]:
        return [n for n in self.net.dag.nodes if n != DECISION]

    def u(self, assignment: Mapping[str, int], d: int) -> float:
        return self.utility[tuple(assignment[p] for p in self.utility_parents) + (d,)]

    def p_do(self, query: Mapping[str, int], d: int, evidence: Mapping[str, int]) -> float:
        """P(query | do(D=d), e)."""
        return self.net.prob(query, {**evidence, DECISION: d})

    def outcomes(self, evidence: Mapping[str, int]) -> List[Dict[str, int]]:
        """Assignments of the utility's unobserved chance parents, S in the classwork."""
        free = [p for p in self.utility_parents if p not in evidence]
        return [dict(zip(free, row)) for row in product((0, 1), repeat=len(free))]

    def eu(self, d: int, evidence: Mapping[str, int]) -> Tuple[float, List[Tuple[Dict[str, int], float, float]]]:
        """EU(d | e) and its terms (s, P(s | do(d), e), U(s, d))."""
        terms = []
        for s in self.outcomes(evidence):
            p = self.p_do(s, d, evidence) if s else 1.0
            terms.append((s, p, self.u({**evidence, **s}, d)))
        return sum(p * u for _, p, u in terms), terms

    def meu(self, evidence: Mapping[str, int]) -> Tuple[float, int, Dict[int, float]]:
        """(MEU(e), best decision d*, {d: EU(d | e)})."""
        eus = {d: self.eu(d, evidence)[0] for d in (0, 1)}
        best = max(eus, key=lambda d: (eus[d], -d))
        return eus[best], best, eus

    def decision_children(self) -> List[str]:
        return sorted(self.net.dag.children(DECISION))

    # ---- display ----------------------------------------------------------------
    def diagram(self, observed=(), query: Optional[str] = None) -> Diagram:
        nodes = tuple(self.net.dag.nodes) + (UTILITY,)
        edges = tuple(self.net.dag.edges) + tuple((p, UTILITY) for p in self.utility_parents) + ((DECISION, UTILITY),)
        return draw(DAG(nodes, tuple(sorted(edges))), observed=observed, query=query,
                    shapes={DECISION: "decision", UTILITY: "utility"})

    def tables(self) -> List[Table]:
        tables = self.net.cpt_tables(skip=(DECISION,))
        cols = list(self.utility_parents) + [DECISION, f"U({', '.join(self.utility_parents + (DECISION,))})"]
        rows = [[str(v) for v in key] + [f"{val:g}"] for key, val in sorted(self.utility.items())]
        tables.append(Table("Utility", cols, rows))
        return tables

    # ---- storage ----------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "net": self.net.to_dict(),
            "utility_parents": list(self.utility_parents),
            "utility": {",".join(map(str, k)): v for k, v in self.utility.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DecisionNet":
        return cls(
            BayesNet.from_dict(data["net"]),
            tuple(data["utility_parents"]),
            {tuple(int(x) for x in k.split(",")): v for k, v in data["utility"].items()},
        )


def random_decision_net(rng: random.Random, settings) -> DecisionNet:
    n = settings["chance_nodes"]
    dag = random_dag(rng, n, settings["edge_prob"], max_parents=settings["max_parents"], names=CHANCE_NAMES)
    edges = list(dag.edges)
    if settings["decision_children"]:
        # Attach D downstream (fewest descendants first) so earlier variables stay observable.
        nodes = sorted(dag.nodes, key=lambda v: (len(dag.descendants(v)), rng.random()))
        for child in nodes[: settings["decision_children"]]:
            if len(dag.parents(child)) < settings["max_parents"]:
                edges.append((DECISION, child))
    full = DAG(tuple(dag.nodes) + (DECISION,), tuple(sorted(edges)))
    cpt = {}
    for node in full.nodes:
        k = len(full.parents(node))
        cpt[node] = {v: rng.choice(CPT_VALUES) for v in product((0, 1), repeat=k)}
    cpt[DECISION] = {(): 0.5}
    parents = tuple(sorted(rng.sample(list(dag.nodes), min(settings["utility_parents"], n))))
    keys = list(product((0, 1), repeat=len(parents) + 1))
    values = rng.sample(range(10, 101, 10), len(keys)) if len(keys) <= 10 else [rng.randrange(0, 101, 5) for _ in keys]
    utility = {key: float(v) for key, v in zip(keys, values)}
    return DecisionNet(BayesNet(full, cpt), parents, utility)


def evidence_text(evidence: Mapping[str, int]) -> str:
    return ", ".join(f"{k}={v}" for k, v in sorted(evidence.items()))


def outcome_text(s: Mapping[str, int]) -> str:
    return ", ".join(f"{k}={v}" for k, v in sorted(s.items()))
