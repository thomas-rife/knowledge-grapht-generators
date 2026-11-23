"""Small DAGs shared by graph-based generators (Bayes nets, search, scheduling)."""
from __future__ import annotations

import random
import string
from dataclasses import dataclass
from typing import Iterable, List, Tuple

@dataclass(frozen=True)
class DAG:
    nodes: Tuple[str, ...]
    edges: Tuple[Tuple[str, str], ...]

    def parents(self, n: str) -> set:
        return {a for a, b in self.edges if b == n}

    def children(self, n: str) -> set:
        return {b for a, b in self.edges if a == n}

    def neighbors(self, n: str) -> set:
        return self.parents(n) | self.children(n)

    def has_edge(self, a: str, b: str) -> bool:
        return (a, b) in self.edges

    def adjacent(self, a: str, b: str) -> bool:
        return self.has_edge(a, b) or self.has_edge(b, a)

    def descendants(self, n: str) -> set:
        seen, stack = set(), [n]
        while stack:
            for child in self.children(stack.pop()):
                if child not in seen:
                    seen.add(child)
                    stack.append(child)
        return seen

    def ancestors(self, n: str) -> set:
        seen, stack = set(), [n]
        while stack:
            for parent in self.parents(stack.pop()):
                if parent not in seen:
                    seen.add(parent)
                    stack.append(parent)
        return seen

    def colliders(self) -> List[str]:
        return [n for n in self.nodes if len(self.parents(n)) >= 2]

    def topological_order(self) -> List[str]:
        indegree = {n: len(self.parents(n)) for n in self.nodes}
        ready = sorted(n for n, d in indegree.items() if d == 0)
        order = []
        while ready:
            n = ready.pop(0)
            order.append(n)
            for c in sorted(self.children(n)):
                indegree[c] -= 1
                if indegree[c] == 0:
                    ready.append(c)
            ready.sort()
        return order

    def to_dict(self) -> dict:
        return {"nodes": list(self.nodes), "edges": [list(e) for e in self.edges]}

    @classmethod
    def from_dict(cls, data: dict) -> "DAG":
        return cls(tuple(data["nodes"]), tuple(tuple(e) for e in data["edges"]))

    @classmethod
    def from_edges(cls, edges: Iterable[str]) -> "DAG":
        """Convenience for tests: DAG.from_edges(["A>B", "B>C"])."""
        pairs = [tuple(e.split(">")) for e in edges]
        nodes = sorted({n for p in pairs for n in p})
        return cls(tuple(nodes), tuple(sorted(pairs)))


def random_dag(
    rng: random.Random, n: int, edge_prob: float, max_parents: int = 3, names: Iterable[str] = None
) -> DAG:
    """Random connected DAG. Letters are shuffled so 'A' isn't always a root."""
    names = list(names)[:n] if names is not None else list(string.ascii_uppercase[:n])
    order = rng.sample(names, n)
    edges = set()
    for j in range(1, n):
        for i in range(j):
            child = order[j]
            if rng.random() < edge_prob and sum(1 for e in edges if e[1] == child) < max_parents:
                edges.add((order[i], child))
    # Connect any separate components, keeping the topological order.
    rank = {name: i for i, name in enumerate(order)}
    comps = _components(names, edges)
    main = comps[0]
    for comp in comps[1:]:
        u, v = rng.choice(sorted(main)), rng.choice(sorted(comp))
        edges.add((u, v) if rank[u] < rank[v] else (v, u))
        main |= comp
    return DAG(tuple(names), tuple(sorted(edges)))


def _components(nodes, edges) -> List[set]:
    adj = {n: set() for n in nodes}
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    comps, seen = [], set()
    for n in nodes:
        if n in seen:
            continue
        comp, stack = set(), [n]
        while stack:
            m = stack.pop()
            if m in comp:
                continue
            comp.add(m)
            stack.extend(adj[m] - comp)
        seen |= comp
        comps.append(comp)
    return comps


def undirected_paths(dag: DAG, x: str, y: str) -> List[List[str]]:
    paths: List[List[str]] = []

    def walk(path: List[str]) -> None:
        if path[-1] == y:
            paths.append(list(path))
            return
        for n in sorted(dag.neighbors(path[-1])):
            if n not in path:
                path.append(n)
                walk(path)
                path.pop()

    walk([x])
    return paths


def describe_path(dag: DAG, path: List[str]) -> str:
    out = path[0]
    for a, b in zip(path, path[1:]):
        out += f" → {b}" if dag.has_edge(a, b) else f" ← {b}"
    return out
