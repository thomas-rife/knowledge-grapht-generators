"""Lists: len() after a series of operations, and aliasing (b = a vs copies)."""
from __future__ import annotations

import copy
import random
from typing import List

from ..core import InvalidProblem, Param, Problem, Step
from .common import Output, PythonGenerator, code_problem, run

LENGTH_MISCONCEPTIONS = {
    "append_list_adds_each": "Thinks append([x, y]) adds two items (that's extend); append adds ONE item, the list.",
    "extend_adds_one": "Thinks extend([x, y]) adds one item; extend adds each item.",
    "plus_changes_list": "Thinks other = lst + [x] changes lst; + builds a new list.",
    "nested_counts_inner": "Counts the items inside a nested list; len counts only the outer items.",
    "len_is_last_index": "Confuses len(lst) with the last index, len(lst) - 1.",
}
OPS = ("append", "append_list", "extend", "pop", "insert", "remove", "plus_new", "plus_assign", "plus_equals")


def op_text(op) -> str:
    kind, v = op[0], op[1] if len(op) > 1 else None
    return {
        "append": f"lst.append({v!r})",
        "append_list": f"lst.append({v!r})",
        "extend": f"lst.extend({v!r})",
        "pop": "lst.pop()",
        "insert": f"lst.insert(0, {v!r})",
        "remove": f"lst.remove({v!r})",
        "plus_new": f"other = lst + {v!r}",
        "plus_assign": f"lst = lst + {v!r}",
        "plus_equals": f"lst += {v!r}",
    }[kind]


def contents(start, ops) -> list:
    """The real list after the ops (to pick valid values for remove and pop)."""
    namespace = {"lst": copy.deepcopy(start)}
    for op in ops:
        exec(op_text(op), {"__builtins__": {}}, namespace)  # our own generated statements
    return namespace["lst"]


def lengths(start, ops, flags=()) -> List[int]:
    """len(lst) after each op, optionally under a misconception."""
    lst = copy.deepcopy(start)
    out = []

    def size():
        if "nested_counts_inner" in flags:
            return sum(len(x) if isinstance(x, list) else 1 for x in lst)
        return len(lst)

    for op in ops:
        kind = op[0]
        if kind == "append":
            lst.append(op[1])
        elif kind == "append_list":
            (lst.extend if "append_list_adds_each" in flags else lst.append)(copy.deepcopy(op[1]))
        elif kind == "extend":
            if "extend_adds_one" in flags:
                lst.append(copy.deepcopy(op[1]))
            else:
                lst.extend(op[1])
        elif kind == "pop":
            if lst:  # can be empty only in a misconception replay
                lst.pop()
        elif kind == "insert":
            lst.insert(0, op[1])
        elif kind == "remove":
            if op[1] in lst:
                lst.remove(op[1])
            elif lst:
                lst.pop()  # misconception replay: only the length matters, and remove shrinks it by one
        elif kind == "plus_new":
            if "plus_changes_list" in flags:
                lst = lst + op[1]
        elif kind in ("plus_assign", "plus_equals"):
            lst = lst + op[1]
        out.append(size())
    return out


class ListLength(PythonGenerator):
    id = "python.list_length"
    summary = "Find len(lst) after append, extend, pop, insert, remove and + on a list."
    concepts = ("python-lists", "len", "list-methods")
    misconceptions = LENGTH_MISCONCEPTIONS
    params = {
        "operations": Param("List operations before len() is printed", 0, 6),
        "kinds": Param("Operations to use", choices=OPS),
        "nested_start": Param("Share of questions whose starting list contains a nested list", 0.0, 1.0),
        "start_length": Param("Most items in the starting list", 1, 8),
    }
    levels = {
        "easy": dict(operations=1, kinds=["append", "pop", "insert"], nested_start=0.0, start_length=4),
        "medium": dict(operations=2, kinds=["append", "append_list", "extend", "pop", "remove", "plus_new"],
                       nested_start=0.3, start_length=5),
        "hard": dict(operations=4, kinds=list(OPS), nested_start=0.4, start_length=5),
    }

    def generate(self, rng: random.Random, level) -> Problem:
        start = rng.sample(range(1, 20), rng.randint(1, level["start_length"]))
        if rng.random() < level["nested_start"]:
            start.insert(rng.randint(0, len(start)), rng.sample(range(20, 40), rng.randint(2, 3)))
        ops = []
        for _ in range(level["operations"]):
            current = contents(start, ops)
            kind = rng.choice(level["kinds"])
            fresh = lambda k: rng.sample(range(40, 60), k)
            if kind == "pop" and not current:
                continue
            if kind == "remove":
                flat = [x for x in current if not isinstance(x, list)]
                if not flat:
                    continue
                op = ("remove", rng.choice(flat))
            elif kind in ("append", "insert"):
                op = (kind, fresh(1)[0])
            elif kind == "pop":
                op = ("pop",)
            else:
                op = (kind, fresh(rng.randint(2, 3)))
            ops.append(op)
        code = "\n".join([f"lst = {start!r}"] + [op_text(o) for o in ops] + ["print(len(lst))"])
        return code_problem("What does this code print?", code, {"start": start, "ops": [list(o) for o in ops]})

    @staticmethod
    def _unpack(problem: Problem):
        return problem.data["start"], [tuple(o) for o in problem.data["ops"]]

    def variants(self, problem: Problem, rng: random.Random):
        start, ops = self._unpack(problem)
        final = lengths(start, ops)[-1] if ops else len(start)
        out = []
        for flag in ("append_list_adds_each", "extend_adds_one", "plus_changes_list", "nested_counts_inner"):
            if ops:
                out.append((flag, str(lengths(start, ops, (flag,))[-1])))
            elif flag == "nested_counts_inner":
                out.append((flag, str(sum(len(x) if isinstance(x, list) else 1 for x in start))))
        out.append(("len_is_last_index", str(final - 1)))
        out += [(None, str(final + d)) for d in (1, 2, -2) if final + d >= 0]
        return out

    def explain(self, problem: Problem, answer) -> List[Step]:
        start, ops = self._unpack(problem)
        steps = [Step(f"len after line 1 (lst = {start!r})", len(start),
                      "a nested list counts as ONE item" if any(isinstance(x, list) for x in start) else "")]
        for i, (op, n) in enumerate(zip(ops, lengths(start, ops)), start=2):
            steps.append(Step(f"len after line {i} ({op_text(op)})", n, ask=True))
        return steps


# ---- aliasing ------------------------------------------------------------------------------
ALIAS_MISCONCEPTIONS = {
    "assignment_copies": "Thinks b = a makes a copy; both names refer to the SAME list.",
    "copy_is_alias": "Thinks a[:], list(a) or a.copy() share the list; they make a new one.",
    "plus_mutates": "Thinks b = b + [x] changes the shared list; + builds a new list and rebinds b.",
    "plus_equals_rebinds": "Thinks b += [x] leaves a alone; += extends the shared list in place.",
}
COPIES = {"alias": "a", "slice": "a[:]", "list": "list(a)", "copy": "a.copy()"}
CHANGES = ("append", "index", "plus", "plus_equals", "rebind")


def change_text(kind, v) -> str:
    return {"append": f"b.append({v})", "index": f"b[0] = {v}", "plus": f"b = b + [{v}]",
            "plus_equals": f"b += [{v}]", "rebind": f"b = [{v}]"}[kind]


class ListAliasing(PythonGenerator):
    id = "python.list_aliasing"
    summary = "Predict whether changing b also changes a, for b = a versus copies made with [:], list() or copy()."
    concepts = ("python-lists", "aliasing", "mutability")
    misconceptions = ALIAS_MISCONCEPTIONS
    params = {
        "copies": Param("How b is made: alias = b = a; slice / list / copy make new lists", choices=tuple(COPIES)),
        "changes": Param("What happens to b", choices=CHANGES),
        "print_both": Param("1 = print a and b; 0 = print only a", 0, 1),
    }
    levels = {
        "easy": dict(copies=["alias", "slice"], changes=["append", "index"], print_both=0),
        "medium": dict(copies=list(COPIES), changes=["append", "index", "plus", "rebind"], print_both=0),
        "hard": dict(copies=list(COPIES), changes=list(CHANGES), print_both=1),
    }

    def generate(self, rng: random.Random, level) -> Problem:
        a = rng.sample(range(1, 10), rng.randint(2, 4))
        copy_kind, change = rng.choice(level["copies"]), rng.choice(level["changes"])
        v = rng.randint(10, 99)
        printed = "print(a, b)" if level["print_both"] else "print(a)"
        code = "\n".join([f"a = {a!r}", f"b = {COPIES[copy_kind]}", change_text(change, v), printed])
        return code_problem("What does this code print?", code,
                            {"a": a, "copy": copy_kind, "change": change, "v": v, "printed": printed})

    def _code(self, d, copy_kind=None, change=None) -> str:
        return "\n".join([f"a = {d['a']!r}", f"b = {COPIES[copy_kind or d['copy']]}",
                          change_text(change or d["change"], d["v"]), d["printed"]])

    def variants(self, problem: Problem, rng: random.Random):
        d = problem.data
        out = []
        if d["copy"] == "alias":
            out.append(("assignment_copies", run(self._code(d, copy_kind="slice"))))
        else:
            out.append(("copy_is_alias", run(self._code(d, copy_kind="alias"))))
        if d["change"] == "plus" and d["copy"] == "alias":
            out.append(("plus_mutates", run(self._code(d, change="plus_equals"))))
        if d["change"] == "plus_equals" and d["copy"] == "alias":
            out.append(("plus_equals_rebinds", run(self._code(d, change="plus"))))
        for c in COPIES:
            for ch in CHANGES:
                out.append((None, run(self._code(d, c, ch))))
        return out

    def explain(self, problem: Problem, answer) -> List[Step]:
        d = problem.data
        shared = d["copy"] == "alias"
        in_place = d["change"] in ("append", "index", "plus_equals")
        return [
            Step("After line 2, do a and b name the same list?", shared,
                 "b = a copies the reference" if shared else f"{COPIES[d['copy']]} builds a new list", ask=True),
            Step("Does line 3 change a list in place?", in_place,
                 "append, item assignment and += change the list itself" if in_place
                 else "this builds a new list and points b at it", ask=True),
            Step("Is a affected?", shared and in_place, ask=True),
        ]
