"""Propositional sentences, CNF conversion, clauses and resolution.

Shared by the logic generators. Notation follows CMSI 3300: ¬ ∧ ∨ ⇒ ⇔,
clauses like ¬M ∨ D ∨ P, "T" for a valid clause, ∅ for the empty clause and
"-" when two clauses can't be resolved.

Sentences are nested lists so they stay JSON-safe:
    ["var", "X"], ["not", s], ["and", a, b, ...], ["or", a, b, ...], ["imp", a, b], ["iff", a, b]
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from itertools import product
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Tuple

Clause = FrozenSet[str]  # literals like "X" or "¬X"

# Letters that don't clash with T (valid), F (false) or v (or).
VAR_POOL = "ABCDEGHJKMNPQRSWXYZ"

PRECEDENCE = {"var": 6, "not": 5, "and": 4, "or": 3, "imp": 2, "iff": 1}
SYMBOL = {"and": " ∧ ", "or": " ∨ ", "imp": " ⇒ ", "iff": " ⇔ "}


# ---- building and reading sentences --------------------------------------------
def var(name: str) -> list:
    return ["var", name]


def neg(s: list) -> list:
    return ["not", s]


def conj(*parts: list) -> list:
    return ["and", *parts]


def disj(*parts: list) -> list:
    return ["or", *parts]


def imp(a: list, b: list) -> list:
    return ["imp", a, b]


def iff(a: list, b: list) -> list:
    return ["iff", a, b]


def lit(name: str, negated: bool = False) -> list:
    return neg(var(name)) if negated else var(name)


def atoms(s: list) -> List[str]:
    if s[0] == "var":
        return [s[1]]
    return sorted({a for part in s[1:] for a in atoms(part)})


def evaluate(s: list, world: Dict[str, bool]) -> bool:
    op = s[0]
    if op == "var":
        return world[s[1]]
    if op == "not":
        return not evaluate(s[1], world)
    if op == "and":
        return all(evaluate(p, world) for p in s[1:])
    if op == "or":
        return any(evaluate(p, world) for p in s[1:])
    if op == "imp":
        return (not evaluate(s[1], world)) or evaluate(s[2], world)
    return evaluate(s[1], world) == evaluate(s[2], world)


def text(s: list) -> str:
    op = s[0]
    if op == "var":
        return s[1]
    if op == "not":
        inner = text(s[1])
        return "¬" + (inner if s[1][0] in ("var", "not") else f"({inner})")
    parts = []
    for p in s[1:]:
        # Bracket every compound part except a repeat of the same ∧ / ∨, as the classwork does.
        simple = p[0] in ("var", "not") or (p[0] == op and op in ("and", "or"))
        inner = text(p)
        parts.append(inner if simple else f"({inner})")
    return SYMBOL[op].join(parts)


def worlds(names: Sequence[str]) -> List[Dict[str, bool]]:
    """All worlds, first variable most significant: w0 = all false, as in the classwork."""
    return [dict(zip(names, (bool(b) for b in bits))) for bits in product((0, 1), repeat=len(names))]


def models(s: list, names: Sequence[str]) -> List[str]:
    return [f"w{i}" for i, w in enumerate(worlds(names)) if evaluate(s, w)]


# ---- clauses -----------------------------------------------------------------
def complement(literal: str) -> str:
    return literal[1:] if literal.startswith("¬") else "¬" + literal


def atom_of(literal: str) -> str:
    return literal.lstrip("¬")


def is_valid_clause(c: Iterable[str]) -> bool:
    c = set(c)
    return any(complement(l) in c for l in c)


def clause_text(c: Iterable[str]) -> str:
    c = sorted(set(c), key=lambda l: (atom_of(l), l.startswith("¬")))
    return " ∨ ".join(c) if c else "∅"


def cnf_text(clauses: Sequence[Iterable[str]]) -> str:
    parts = [clause_text(c) for c in clauses]
    if len(parts) == 1:
        return parts[0]
    return " ∧ ".join(p if " ∨ " not in p else f"({p})" for p in parts)


def clause_sentence(c: Iterable[str]) -> list:
    return disj(*[lit(atom_of(l), l.startswith("¬")) for l in sorted(c)])


def holds(clauses: Iterable[Iterable[str]], world: Dict[str, bool]) -> bool:
    return all(any(world[atom_of(l)] != l.startswith("¬") for l in c) for c in clauses)


# ---- parsing what students type ----------------------------------------------------
VALID_WORDS = {"t", "true", "⊤", "valid", "vacuous", "tautology"}
EMPTY_WORDS = {"∅", "{}", "empty", "contradiction", "⊥", "false", "□"}
NONE_WORDS = {"-", "–", "—", "n/a", "na", "none", "not amenable", "not resolvable", "no"}


def _clean(response: str) -> str:
    t = unicodedata.normalize("NFKC", str(response)).strip()
    t = re.sub(r"\bnot\s+", "¬", t, flags=re.I)
    return t.replace("~", "¬").replace("!", "¬").replace("¬ ", "¬")


def parse_clause(response: str) -> Optional[Clause]:
    """'¬M ∨ D ∨ P', '~m | d | p', 'not M or D' -> frozenset; None if unreadable."""
    t = _clean(response).strip("() ")
    if not t:
        return None
    parts = re.split(r"\s*(?:∨|\||\bor\b|,)\s*", t, flags=re.I)
    out = set()
    for p in parts:
        p = p.strip("() ").upper()
        if not re.fullmatch(r"¬?[A-Z]", p):
            return None
        out.add(p)
    return frozenset(out)


def parse_cnf(response: str) -> Optional[List[Clause]]:
    t = _clean(response)
    pieces = re.split(r"\s*(?:∧|&|\^|\band\b|;|\n|\)\s*\()\s*", t, flags=re.I)
    clauses = [parse_clause(p) for p in pieces if p.strip("() ")]
    return None if not clauses or any(c is None for c in clauses) else clauses


@dataclass
class ResolveResult:
    """Answer type for resolve(c1, c2): a clause, valid (T), empty (∅) or not resolvable (-)."""

    kind: str  # "clause" | "valid" | "empty" | "none"
    literals: Tuple[str, ...] = ()

    def __str__(self) -> str:
        return {"valid": "T", "empty": "∅", "none": "-"}.get(self.kind) or clause_text(self.literals)

    def accepts(self, response: str) -> bool:
        word = _clean(response).lower()
        if word in NONE_WORDS:
            return self.kind == "none"
        if word in VALID_WORDS:
            return self.kind == "valid"
        if word in EMPTY_WORDS:
            return self.kind == "empty"
        c = parse_clause(response)
        if c is None:
            return False
        if self.kind == "valid":
            return is_valid_clause(c)  # writing out the tautology also counts
        return self.kind == "clause" and c == frozenset(self.literals)


@dataclass
class CNFAnswer:
    """Answer type for a CNF conversion: any CNF logically equivalent to the answer is accepted."""

    clauses: Tuple[Tuple[str, ...], ...]

    def __str__(self) -> str:
        return cnf_text(self.clauses)

    def accepts(self, response: str) -> bool:
        got = parse_cnf(response)
        if got is None:
            return False
        names = sorted({atom_of(l) for c in list(self.clauses) + got for l in c})
        return all(holds(self.clauses, w) == holds(got, w) for w in worlds(names))


def as_clauses(clauses: Iterable[Iterable[str]]) -> Tuple[Tuple[str, ...], ...]:
    return tuple(tuple(sorted(c, key=lambda l: (atom_of(l), l.startswith("¬")))) for c in clauses)


# ---- resolution ----------------------------------------------------------------------
def resolvents(c1: Clause, c2: Clause) -> List[Tuple[str, Clause]]:
    """Every single-pair resolvent: (literal resolved on, resulting clause)."""
    return [
        (l, frozenset((c1 - {l}) | (c2 - {complement(l)})))
        for l in sorted(c1)
        if complement(l) in c2
    ]


def resolve(c1: Clause, c2: Clause) -> ResolveResult:
    """resolve(clause1, clause2) as in the classwork: cancel ONE complementary pair."""
    options = resolvents(c1, c2)
    if not options:
        return ResolveResult("none")
    _, out = options[0]
    if not out:
        return ResolveResult("empty")
    if is_valid_clause(out):
        return ResolveResult("valid")
    return ResolveResult("clause", tuple(sorted(out)))


# ---- CNF conversion, with optional deliberate mistakes ------------------------------
MISTAKES = {
    "biconditional_one_way": "Converts A ⇔ B as only A ⇒ B, dropping the other direction.",
    "implication_reversed": "Rewrites A ⇒ B as A ∨ ¬B instead of ¬A ∨ B.",
    "de_morgan_error": "Pushes ¬ inside without flipping ∧/∨: ¬(A ∨ B) becomes ¬A ∨ ¬B.",
    "distribution_error": "Distributes ∨ into only the first part of a conjunction.",
    "dropped_clause": "Loses one of the clauses produced by the conversion.",
}


def _elim_iff(s: list, mistake: Optional[str]) -> list:
    if s[0] == "var":
        return s
    parts = [_elim_iff(p, mistake) for p in s[1:]]
    if s[0] == "iff":
        a, b = parts
        return imp(a, b) if mistake == "biconditional_one_way" else conj(imp(a, b), imp(b, a))
    return [s[0], *parts]


def _elim_imp(s: list, mistake: Optional[str]) -> list:
    if s[0] == "var":
        return s
    parts = [_elim_imp(p, mistake) for p in s[1:]]
    if s[0] == "imp":
        a, b = parts
        return disj(a, neg(b)) if mistake == "implication_reversed" else disj(neg(a), b)
    return [s[0], *parts]


def _push_not(s: list, mistake: Optional[str]) -> list:
    op = s[0]
    if op == "var":
        return s
    if op != "not":
        return [op, *[_push_not(p, mistake) for p in s[1:]]]
    inner = s[1]
    if inner[0] == "var":
        return s
    if inner[0] == "not":
        return _push_not(inner[1], mistake)
    flipped = inner[0] if mistake == "de_morgan_error" else ("or" if inner[0] == "and" else "and")
    return [flipped, *[_push_not(neg(p), mistake) for p in inner[1:]]]


def _clauses(s: list, mistake: Optional[str]) -> List[frozenset]:
    op = s[0]
    if op == "var":
        return [frozenset([s[1]])]
    if op == "not":
        return [frozenset(["¬" + s[1][1]])]
    child = [_clauses(p, mistake) for p in s[1:]]
    if op == "and":
        return [c for cs in child for c in cs]
    # op == "or": distribute
    if mistake == "distribution_error" and any(len(cs) > 1 for cs in child):
        multi = next(cs for cs in child if len(cs) > 1)
        rest = frozenset().union(*[cs[0] for cs in child if cs is not multi])
        return [multi[0] | rest] + multi[1:]
    out = [frozenset()]
    for cs in child:
        out = [a | b for a in out for b in cs]
    return out


def to_cnf(s: list, mistake: Optional[str] = None) -> Tuple[Tuple[Tuple[str, ...], ...], List[Tuple[str, str]]]:
    """(clauses, phases): phases are (step name, sentence text) for the worked solution."""
    phases = []
    s1 = _elim_iff(s, mistake)
    if s1 != s:
        phases.append(("Eliminate ⇔", text(s1)))
    s2 = _elim_imp(s1, mistake)
    if s2 != s1:
        phases.append(("Eliminate ⇒", text(s2)))
    s3 = _push_not(s2, mistake)
    if s3 != s2:
        phases.append(("Move ¬ inwards (De Morgan)", text(s3)))
    raw = _clauses(s3, mistake)
    unique = []
    for c in raw:
        if not is_valid_clause(c) and c not in unique:
            unique.append(c)
    if mistake == "dropped_clause" and len(unique) > 1:
        unique = unique[:-1]
    clauses = as_clauses(unique)
    phases.append(("Distribute ∨ over ∧, drop duplicate clauses", cnf_text(clauses)))
    return clauses, phases
