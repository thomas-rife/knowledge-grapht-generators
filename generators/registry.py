"""Every published generator, by id. The questions service only serves these.

python.write_function runs student code. Its default runner is NOT a sandbox,
so it is published only when GENERATORS_ENABLE_CODE_RUNNER=1 (use that in a
test environment, or once a sandboxed runner is configured with set_runner).
"""
from __future__ import annotations

import os

from . import python as py
from .bayes import DoQuery, DSeparation, Enumeration, MaximumLikelihood, VariableElimination
from .decision import MaximumExpectedUtility, ValueOfInformation
from .logic import CNFConversion, Entailment, Refutation, Resolution

CODE_RUNNER_ENABLED = os.environ.get("GENERATORS_ENABLE_CODE_RUNNER") == "1"
_python = [getattr(py, name)() for name in py.__all__]
if not CODE_RUNNER_ENABLED:
    _python = [g for g in _python if g.id != "python.write_function"]

_BY_SUBJECT = {
    "Intro Python": _python,
    "Propositional logic": [Entailment(), Resolution(), CNFConversion(), Refutation()],
    "Bayesian networks": [DSeparation(), Enumeration(), VariableElimination(), MaximumLikelihood(), DoQuery()],
    "Decision making": [MaximumExpectedUtility(), ValueOfInformation()],
}
GENERATORS = {g.id: g for gens in _BY_SUBJECT.values() for g in gens}
SUBJECTS = {g.id: subject for subject, gens in _BY_SUBJECT.items() for g in gens}
