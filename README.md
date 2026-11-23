# Knowledge Grapht generators

Practice-question generators. Write three methods; get multiple choice, fill
in the blank and step-by-step worked problems, plus marking and misconception
diagnosis, for free. Pure Python 3.9+, no dependencies.

```sh
python3 -m unittest discover tests     # tests
python3 -m generators.preview          # writes preview/samples.html
python3 -m generators.preview python   # writes preview/python.html
```

## Questions service

```sh
GENERATORS_SECRET=<32+ random chars> GENERATORS_API_KEY=<random key> python3 -m generators.api --port 8787
```

Studio and the admin app call it from their servers with `X-Generators-Key` (set `GENERATORS_API_URL`
and `GENERATORS_API_KEY` in both apps). `GET /generators` is the catalog, `POST /preview` returns a sample
with its answer (instructors), `POST /question` returns a question and a signed token without the answer
(students), and `POST /check` rebuilds the question from the token, marks it and names the misconception.
Nothing is stored; `registry.py` lists the published generators.

## Writing a generator

```python
class MyGenerator(Generator):
    id = "topic.name"
    concepts = ("concept-a",)

    params = {...}; levels = {"easy": {...}, ...}       # adjustable settings and presets
    def generate(self, rng, settings) -> Problem:        # random scenario + question text
    def solve(self, problem):                            # correct answer: text, number or list
    def answer_options(self, problem, answer, rng):      # wrong answers, Option(value, misconception)
    def explain(self, problem, answer) -> [Step]:        # optional worked solution
```

`Step(label, value, work, ask)` is one line of the worked solution. In the
`steps` format, every step with `ask=True` becomes a blank (followed by the
final answer); `question.check_step(i, response)` marks blank `i`, allowing 1%
on intermediate numbers.

`make_question(gen, seed, difficulty, fmt=None)` picks the format at random,
retries unsuitable scenarios (`raise InvalidProblem`), and returns a `Question`
with `check(response)`, `diagnose(response)` and `student_view()`. Marking
depends on the answer type: booleans accept T/F/true/false, lists are sets (any order or separator, "none" for
empty), numbers allow rounding, text ignores case and spacing. The same
arguments always give the same question.

## Size and difficulty

Every generator declares `params` (what can be adjusted, with ranges or
allowed values) and `levels` (easy / medium / hard presets). Pick a preset and
override anything:

```python
make_question(Refutation(), seed, "hard", settings={"variables": 8, "min_steps": 6, "max_steps": 9})
make_question(Entailment(), seed, "easy", settings={"variables": 2, "alpha_forms": ["and"]})
```

Invalid values and impossible combinations raise `ValueError` with a reason.
The resolved settings are stored on the question (`question.settings`), so a
question is rebuilt exactly from generator id, version, seed, settings and
format. `describe(generator)` returns everything a picker UI needs. See
[SETTINGS.md](SETTINGS.md) for every setting.

## Layout

- `generators/core.py`: the base class, harness and marking.
- `generators/graphs/`: shared random DAGs, top-down layout and SVG, for any graph question.
- `generators/bayes/network.py`: shared binary Bayes nets with CPTs and exact enumeration.
- `generators/bayes/dsep.py`: d-separation ("which nodes are d-separated from X given the shaded nodes?").
- `generators/bayes/enumeration.py`: P(Q=1 | evidence) from a network and its CPTs.
- `generators/bayes/mle.py`: maximum likelihood estimate of a CPT entry from a table of counts.
- `generators/bayes/elimination.py`: the same query by variable elimination, factor by factor.
- `generators/bayes/do_query.py`: causal effect P(Y=1 | do(X=x)) by adjusting for X's parents, versus conditioning.
- `generators/decision/network.py`: shared decision networks (chance nodes, decision D, utility U).
- `generators/decision/meu.py`: P(S | do(D), e), EU(d | e), MEU and d* (Classwork 4, Problem 2).
- `generators/decision/vpi.py`: VPI(X | e) = Σ_x P(x | e) MEU(x, e) − MEU(e) (Classwork 4, Problem 3).
- `generators/python/`: intro Python. Each question is a fresh random program; wrong answers come from
  running it under a misconception. `range_loop`, `range_write` (any equivalent range(...) call is accepted,
  parsed with ast and never executed), `conditionals`, `variables`, `list_length`, `list_aliasing`,
  `string_slicing`, `division`, `loop_count`. `common.run` executes only programs this package generated.
- `generators/python/functions.py` (`write_function`): write a function, marked LeetCode style by unit
  tests. Expected values come from a reference solution; buggy reference versions name the misconception
  when a student's results match theirs. `runner.HARNESS` is a standalone script (it can run in Pyodide in
  Studio); `LocalRunner` runs it in a separate process with a time limit for development. It is NOT a
  security sandbox: use Pyodide or an isolated sandbox for real students (`set_runner`).
- `generators/logic/sentence.py`: shared propositional logic: sentences, CNF conversion
  (with deliberate mistakes for wrong options), clause parsing, resolution.
- `generators/logic/entailment.py`: truth tables, M(α), M(β), does α ⊨ β (Classwork 2, 1.2-1.4).
- `generators/logic/resolution.py`: resolve two clauses: amenable, inferred clause, ≡ T, ∅ (1.5).
- `generators/logic/cnf.py`: convert a sentence to CNF; any equivalent CNF is accepted (2.2).
- `generators/logic/refutation.py`: proof by contradiction with resolution, numbered KB clauses (2.3).

Wrong answers come from misconceptions (each generator's `misconceptions`),
for example forgetting to normalise, reversing a conditional, or cancelling
two complementary pairs in one resolution. A problem can carry a diagram and
tables (CPTs, data, KB clauses). Numeric answers accept decimals, fractions
(3/7) and percentages.

Logic answers accept typed notation: `~`, `!` or `not` for ¬, `|` or `or` for ∨,
`&` or `and` for ∧, and `-`, `T`, `∅` (or `empty`) for resolution results.
