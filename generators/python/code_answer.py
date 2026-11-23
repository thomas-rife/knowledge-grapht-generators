"""CodeAnswer: a function is correct if it passes every unit test.

Expected values come from running the reference solution (code this package
wrote, run in-process). Student code always goes through the runner. A wrong
option's CodeAnswer holds what a buggy version returns, so if a student's
results match it, `diagnose` names that misconception.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from .common import SAFE_BUILTINS
from .runner import get_runner

_TRUSTED: Dict[Tuple[str, str, str], Dict[str, Any]] = {}  # our own sources -> results, no runner needed
_CACHE: Dict[Tuple[str, str, str], Dict[str, Any]] = {}  # student submissions already run


def normalize(value: Any) -> Any:
    return json.loads(json.dumps(value, default=repr))  # tuples -> lists, as the harness reports them


def run_trusted(source: str, function: str, inputs: List[list]) -> Dict[str, Any]:
    """Run a reference or buggy solution written by this package (never student code)."""
    namespace: Dict[str, Any] = {"__builtins__": SAFE_BUILTINS}
    exec(compile(source, "<reference>", "exec"), namespace)
    fn = namespace[function]
    results = []
    for args in inputs:
        try:
            results.append({"ok": True, "value": normalize(fn(*args))})
        except Exception as e:  # a buggy version may crash, e.g. dividing by zero
            results.append({"ok": False, "error": f"{type(e).__name__}: {e}"})
    return {"error": None, "results": results}


def same(a: Any, b: Any) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


@dataclass
class CodeAnswer:
    function: str
    inputs: List[list]
    source: str  # the solution this answer stands for (shown as the worked answer or an option)
    expected: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_source(cls, source: str, function: str, inputs: List[list]) -> "CodeAnswer":
        report = run_trusted(source, function, inputs)
        _TRUSTED[(source.strip(), function, json.dumps(inputs))] = report
        return cls(function, inputs, source, report["results"])

    def __str__(self) -> str:
        return self.source

    def results(self, code: str) -> Dict[str, Any]:
        key = (code.strip(), self.function, json.dumps(self.inputs))
        if key in _TRUSTED:
            return _TRUSTED[key]
        if key not in _CACHE:
            _CACHE[key] = get_runner().run(code, self.function, self.inputs)
        return _CACHE[key]

    def matches_report(self, report: Dict[str, Any]) -> bool:
        """Do these results (from any runner, e.g. Pyodide in the browser) equal the expected ones?"""
        got = report.get("results", [])
        if report.get("error") or len(got) != len(self.expected):
            return False
        for g, e in zip(got, self.expected):
            if g.get("ok") != e.get("ok"):
                return False
            if e.get("ok") and not same(g.get("value"), e.get("value")):
                return False
        return True

    def accepts(self, response: str) -> bool:
        return self.matches_report(self.results(response))

    def feedback(self, code: str) -> List[Dict[str, Any]]:
        """Per-test results for showing the student: input, expected, got, passed."""
        report = self.results(code)
        if report.get("error"):
            return [{"error": report["error"]}]
        rows = []
        for args, g, e in zip(self.inputs, report["results"], self.expected):
            got = g.get("value") if g.get("ok") else g.get("error")
            rows.append({"input": args, "expected": e.get("value"), "got": got,
                         "passed": g.get("ok") == e.get("ok") and (not e.get("ok") or same(g.get("value"), e.get("value")))})
        return rows
