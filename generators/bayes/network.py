"""Binary Bayesian networks with CPTs, exact inference by enumeration, and data counts.

Shared by the Bayes-net generators (enumeration, MLE, and later variable
elimination or sampling).
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from itertools import product
from typing import Dict, List, Mapping, Optional, Tuple

from ..core import Table
from ..graphs import DAG

CPT_VALUES = (0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9)  # 0.5 left out: it hides mistakes


@dataclass
class BayesNet:
    dag: DAG
    cpt: Dict[str, Dict[Tuple[int, ...], float]]  # node -> parent values -> P(node=1 | parents)

    def parents(self, node: str) -> List[str]:
        return sorted(self.dag.parents(node))

    def p(self, node: str, value: int, assignment: Mapping[str, int]) -> float:
        row = tuple(assignment[p] for p in self.parents(node))
        p1 = self.cpt[node][row]
        return p1 if value else 1 - p1

    def joint(self, assignment: Mapping[str, int]) -> float:
        out = 1.0
        for n in self.dag.nodes:
            out *= self.p(n, assignment[n], assignment)
        return out

    def marginal(self, fixed: Mapping[str, int]) -> float:
        """P(fixed) by summing the joint over every other variable."""
        free = [n for n in self.dag.nodes if n not in fixed]
        return sum(
            self.joint({**fixed, **dict(zip(free, values))})
            for values in product((0, 1), repeat=len(free))
        )

    def prob(self, query: Mapping[str, int], evidence: Optional[Mapping[str, int]] = None) -> float:
        evidence = dict(evidence or {})
        return self.marginal({**evidence, **query}) / self.marginal(evidence)

    def cpt_tables(self, skip=()) -> List[Table]:
        tables = []
        for n in self.dag.topological_order():
            if n in skip:
                continue
            parents = self.parents(n)
            rows = [
                [str(v) for v in values] + [f"{self.cpt[n][values]:.1f}"]
                for values in sorted(self.cpt[n], reverse=True)
            ]
            label = f"P({n}=1 | {', '.join(parents)})" if parents else f"P({n}=1)"
            tables.append(Table(f"CPT for {n}", parents + [label], rows))
        return tables

    def to_dict(self) -> dict:
        return {
            "dag": self.dag.to_dict(),
            "cpt": {n: {",".join(map(str, k)): v for k, v in rows.items()} for n, rows in self.cpt.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BayesNet":
        cpt = {
            n: {tuple(int(x) for x in k.split(",") if x != ""): v for k, v in rows.items()}
            for n, rows in data["cpt"].items()
        }
        return cls(DAG.from_dict(data["dag"]), cpt)


def random_net(rng: random.Random, dag: DAG) -> BayesNet:
    cpt = {}
    for n in dag.nodes:
        k = len(dag.parents(n))
        cpt[n] = {values: rng.choice(CPT_VALUES) for values in product((0, 1), repeat=k)}
    return BayesNet(dag, cpt)


def assignment_text(assignment: Mapping[str, int]) -> str:
    return ", ".join(f"{k}={v}" for k, v in sorted(assignment.items()))


def term_text(net: BayesNet, assignment: Mapping[str, int], only=None) -> Tuple[str, str, float]:
    """('P(C=1)·P(B=0|C=1)', '0.6 × 0.3', 0.18) for one assignment, in topological order.

    `only` limits the product to some variables (e.g. the query, evidence and their ancestors).
    """
    names, numbers, value = [], [], 1.0
    for n in net.dag.topological_order():
        if only is not None and n not in only:
            continue
        parents = net.parents(n)
        given = f" | {', '.join(f'{p}={assignment[p]}' for p in parents)}" if parents else ""
        names.append(f"P({n}={assignment[n]}{given})")
        numbers.append(f"{net.p(n, assignment[n], assignment):.1f}")
        value *= net.p(n, assignment[n], assignment)
    return "·".join(names), " × ".join(numbers), value


def needed_variables(net: BayesNet, variables) -> List[str]:
    """The variables whose CPTs a query needs: the variables themselves and all their ancestors."""
    out = set(variables)
    for v in variables:
        out |= net.dag.ancestors(v)
    return sorted(out)


@dataclass
class Factor:
    """A table over binary variables, for variable elimination."""

    variables: Tuple[str, ...]
    values: Dict[Tuple[int, ...], float]

    def __call__(self, assignment: Mapping[str, int]) -> float:
        return self.values[tuple(assignment[v] for v in self.variables)]

    def multiply(self, other: "Factor") -> "Factor":
        variables = tuple(sorted(set(self.variables) | set(other.variables)))
        values = {}
        for row in product((0, 1), repeat=len(variables)):
            a = dict(zip(variables, row))
            values[row] = self(a) * other(a)
        return Factor(variables, values)

    def sum_out(self, var: str) -> "Factor":
        variables = tuple(v for v in self.variables if v != var)
        values = {}
        for row in product((0, 1), repeat=len(variables)):
            a = dict(zip(variables, row))
            values[row] = self({**a, var: 0}) + self({**a, var: 1})
        return Factor(variables, values)

    def entries_text(self) -> str:
        if not self.variables:
            return f"{self.values[()]:.4f}"
        return ", ".join(
            f"{','.join(f'{v}={x}' for v, x in zip(self.variables, row))}: {val:.4f}"
            for row, val in sorted(self.values.items(), reverse=True)
        )


def cpt_factor(net: BayesNet, node: str, evidence: Mapping[str, int]) -> Factor:
    """The CPT of `node` as a factor, with evidence variables fixed."""
    scope = [node] + net.parents(node)
    free = tuple(sorted(v for v in scope if v not in evidence))
    values = {}
    for row in product((0, 1), repeat=len(free)):
        a = {**evidence, **dict(zip(free, row))}
        values[row] = net.p(node, a[node], a)
    return Factor(free, values)
