"""Running student code against unit tests.

HARNESS is a standalone Python script: give it the student's code, the
function name and the test inputs (as JSON on stdin) and it prints each
call's return value or error as JSON. The same script can run in Pyodide
inside Studio, so the browser executes student code and the server only
compares results with the expected values.

LocalRunner runs HARNESS in a separate Python process with a time limit and
an empty environment. It is for development and tests, NOT a security
sandbox: it can still read files the server can. Production should run
student code in the browser (Pyodide) or an isolated sandbox service.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional

HARNESS = r'''
import contextlib, io, json, sys

spec = json.loads(sys.stdin.read())
report = {"error": None, "results": []}
namespace = {"__name__": "student"}
try:
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(spec["code"], "<student>", "exec"), namespace)
except BaseException as e:  # syntax errors, crashes at import time
    report["error"] = f"{type(e).__name__}: {e}"
else:
    fn = namespace.get(spec["function"])
    if not callable(fn):
        report["error"] = f"no function named {spec['function']}"
    else:
        for args in spec["inputs"]:
            printed = io.StringIO()
            try:
                with contextlib.redirect_stdout(printed):
                    value = fn(*args)
                report["results"].append({"ok": True, "value": value, "printed": printed.getvalue()})
            except BaseException as e:
                report["results"].append({"ok": False, "error": f"{type(e).__name__}: {e}"})
print(json.dumps(report, default=repr))
'''


class Runner:
    def run(self, code: str, function: str, inputs: List[list]) -> Dict[str, Any]:
        raise NotImplementedError


def _limits():  # pragma: no cover - runs in the child process
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
        resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))  # best effort only: buffered writes can slip through
    except (ImportError, ValueError, OSError):
        pass


class LocalRunner(Runner):
    """Development runner: a separate process in a throwaway folder, 3 second limit, no environment variables.

    Not a security sandbox: student code could still read files or use the network.
    """

    def __init__(self, timeout: float = 3.0):
        self.timeout = timeout

    def run(self, code: str, function: str, inputs: List[list]) -> Dict[str, Any]:
        spec = json.dumps({"code": code, "function": function, "inputs": inputs})
        with tempfile.TemporaryDirectory() as tmp:
            try:
                proc = subprocess.run(
                    [sys.executable, "-I", "-S", "-c", HARNESS], input=spec, capture_output=True, text=True,
                    timeout=self.timeout, cwd=tmp, env={}, preexec_fn=_limits if os.name == "posix" else None,
                )
            except subprocess.TimeoutExpired:
                return {"error": "Timed out: is there an infinite loop?", "results": []}
        try:
            return json.loads(proc.stdout.strip().splitlines()[-1])
        except (IndexError, json.JSONDecodeError):
            return {"error": (proc.stderr.strip().splitlines() or ["the program crashed"])[-1], "results": []}


_runner: Runner = LocalRunner()


def set_runner(runner: Runner) -> None:
    """Swap in a real sandbox (or a stub) for running student code."""
    global _runner
    _runner = runner


def get_runner() -> Runner:
    return _runner
