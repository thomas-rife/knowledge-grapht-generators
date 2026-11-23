# Generator settings

Generated from `describe()`. Pick a preset with `difficulty=`, then override any setting:

```python
make_question(Refutation(), seed, "hard", settings={"variables": 8, "min_steps": 6, "max_steps": 9})
```

## `python.conditionals`

Formats: mcq, fill_blank, steps

| Setting | What it controls | Range | Easy | Medium | Hard |
| --- | --- | --- | --- | --- | --- |
| `branches` | Conditions before the else (nested always uses 2) | 1–4 | 2 | 3 | 3 |
| `structures` | elif = one chain; separate = independent ifs (else belongs to the last); nested = ifs inside ifs | any of: elif; separate; nested | elif | elif; separate | elif; separate; nested |
| `operators` | Comparison operators to use | any of: >; >=; <; <= | >; >= | >; >= | >; >=; <; <= |
| `boundary_share` | Share of questions where the value equals a threshold | 0.0–1.0 | 0.2 | 0.4 | 0.5 |

## `python.division`

Formats: mcq, fill_blank, steps

| Setting | What it controls | Range | Easy | Medium | Hard |
| --- | --- | --- | --- | --- | --- |
| `expressions` | Expressions printed together | 1–3 | 1 | 2 | 3 |
| `operators` | Operators to use | any of: /; //; % | /; //; % | /; //; % | //; %; / |
| `negatives` | Share of expressions with a negative number | 0.0–1.0 | 0.0 | 0.2 | 0.5 |

## `python.list_aliasing`

Formats: mcq, fill_blank, steps

| Setting | What it controls | Range | Easy | Medium | Hard |
| --- | --- | --- | --- | --- | --- |
| `copies` | How b is made: alias = b = a; slice / list / copy make new lists | any of: alias; slice; list; copy | alias; slice | alias; slice; list; copy | alias; slice; list; copy |
| `changes` | What happens to b | any of: append; index; plus; plus_equals; rebind | append; index | append; index; plus; rebind | append; index; plus; plus_equals; rebind |
| `print_both` | 1 = print a and b; 0 = print only a | 0–1 | 0 | 0 | 1 |

## `python.list_length`

Formats: mcq, fill_blank, steps

| Setting | What it controls | Range | Easy | Medium | Hard |
| --- | --- | --- | --- | --- | --- |
| `operations` | List operations before len() is printed | 0–6 | 1 | 2 | 4 |
| `kinds` | Operations to use | any of: append; append_list; extend; pop; insert; remove; plus_new; plus_assign; plus_equals | append; pop; insert | append; append_list; extend; pop; remove; plus_new | append; append_list; extend; pop; insert; remove; plus_new; plus_assign; plus_equals |
| `nested_start` | Share of questions whose starting list contains a nested list | 0.0–1.0 | 0.0 | 0.3 | 0.4 |
| `start_length` | Most items in the starting list | 1–8 | 4 | 5 | 5 |

## `python.loop_count`

Formats: mcq, fill_blank, steps

| Setting | What it controls | Range | Easy | Medium | Hard |
| --- | --- | --- | --- | --- | --- |
| `forms` | Loop shapes | any of: nested_fixed; nested_dependent; while_doubling; while_step | nested_fixed; while_step | nested_fixed; nested_dependent; while_step | nested_fixed; nested_dependent; while_doubling; while_step |
| `max_n` | Largest loop bound | 3–64 | 5 | 8 | 40 |

## `python.range_loop`

Formats: mcq, fill_blank, steps

| Setting | What it controls | Range | Easy | Medium | Hard |
| --- | --- | --- | --- | --- | --- |
| `range_args` | Forms of range: 1 = range(stop), 2 = range(start, stop), 3 = range(start, stop, step) | any of: 1; 2; 3 | 1; 2 | 2; 3 | 3 |
| `negative_step` | 1 = allow counting down with a negative step | 0–1 | 0 | 0 | 1 |
| `max_value` | Largest start or stop value | 5–50 | 10 | 20 | 30 |
| `max_iterations` | Most loop iterations | 2–12 | 6 | 7 | 8 |
| `body` | print = print each value; sum = add the values up | any of: print; sum | print | print; sum | print; sum |

## `python.range_write`

Formats: mcq, fill_blank, steps

| Setting | What it controls | Range | Easy | Medium | Hard |
| --- | --- | --- | --- | --- | --- |
| `length` | How many values the sequence has | 2–10 | 4 | 5 | 5 |
| `steps` | Kinds of step: one = 1, up = 2-5, down = negative | any of: one; up; down | one | one; up | up; down |
| `max_value` | Largest value in the sequence | 5–50 | 10 | 25 | 40 |

## `python.string_slicing`

Formats: mcq, fill_blank, steps

| Setting | What it controls | Range | Easy | Medium | Hard |
| --- | --- | --- | --- | --- | --- |
| `forms` | Kinds of index or slice | any of: index; negative_index; slice; open_start; open_end; negative_slice; step; reverse | index; negative_index; open_start | slice; open_end; negative_index; negative_slice | slice; negative_slice; step; reverse |

## `python.variables`

Formats: mcq, fill_blank, steps

| Setting | What it controls | Range | Easy | Medium | Hard |
| --- | --- | --- | --- | --- | --- |
| `lines` | Statements after the initial assignments | 1–6 | 2 | 3 | 4 |
| `features` | Kinds of statement to include | any of: copy; arithmetic; augmented; swap; two_line_swap; division; strings | copy; arithmetic; augmented | copy; arithmetic; augmented; two_line_swap; division | copy; augmented; swap; two_line_swap; division; strings |

## `python.write_function`

Formats: code, mcq, steps

| Setting | What it controls | Range | Easy | Medium | Hard |
| --- | --- | --- | --- | --- | --- |
| `tasks` | Kinds of function to write | any of: multiples_list; grade; count_longer; average; last_n; sum_multiples | multiples_list; average; count_longer | multiples_list; grade; count_longer; average | multiples_list; grade; count_longer; average; last_n; sum_multiples |

## `logic.entailment`

Formats: mcq, fill_blank, steps

| Setting | What it controls | Range | Easy | Medium | Hard |
| --- | --- | --- | --- | --- | --- |
| `variables` | Propositions in the truth table (2 = 4 rows, 3 = 8, 4 = 16) | 2–4 | 2 | 3 | 3 |
| `alpha_forms` | Shapes α can take (kb = two clauses joined by ∧) | any of: literal; clause; and; implies; iff; kb | and; literal; implies | and; clause; implies | kb; iff; implies |
| `beta_forms` | Shapes β can take | any of: literal; clause; and; implies; iff; kb | clause; literal | clause; implies; literal | literal; clause; implies |
| `entailed_share` | Share of questions whose answer is True | 0.0–1.0 | 0.5 | 0.5 | 0.5 |

## `logic.resolution`

Formats: mcq, fill_blank, steps

| Setting | What it controls | Range | Easy | Medium | Hard |
| --- | --- | --- | --- | --- | --- |
| `variables` | Propositions the clauses can use | 2–5 | 3 | 3 | 4 |
| `clause_size` | Most literals in each clause | 1–4 | 2 | 3 | 3 |
| `cases` | Kinds of pair: single = one complementary pair, double = two (result is T), unit = X and ¬X (∅), shared = same literal in both (not resolvable), disjoint = nothing in common (not resolvable) | any of: single; double; unit; shared; disjoint | single; unit; shared; disjoint | single; double; unit; shared; disjoint | single; double; shared |

## `logic.cnf_conversion`

Formats: mcq, fill_blank, steps

| Setting | What it controls | Range | Easy | Medium | Hard |
| --- | --- | --- | --- | --- | --- |
| `forms` | Sentence shapes to convert (a, b, c are random propositions) | any of: a => b \| c; a & b => c; a <=> b; a => b & c; a <=> b \| c; a <=> b & c; a \| b => c; a => ~b & ~c; ~(a & (b \| c)); exactly one of a, b, c; a & b <=> c; (a => b) & (b => a \| c); ~(a <=> b) | a => b \| c; a & b => c; a <=> b; a => b & c | a <=> b \| c; a <=> b & c; a \| b => c; a => ~b & ~c; ~(a & (b \| c)) | exactly one of a, b, c; a & b <=> c; (a => b) & (b => a \| c); ~(a <=> b); a <=> b \| c |
| `negation_prob` | Chance each proposition appears negated | 0.0–0.6 | 0.0 | 0.2 | 0.25 |

## `logic.resolution_refutation`

Formats: steps, mcq, fill_blank

| Setting | What it controls | Range | Easy | Medium | Hard |
| --- | --- | --- | --- | --- | --- |
| `variables` | Propositions in the knowledge base | 3–10 | 4 | 5 | 6 |
| `min_steps` | Fewest resolution steps in the shortest proof found | 1–10 | 2 | 3 | 4 |
| `max_steps` | Most resolution steps in the shortest proof found | 1–12 | 3 | 4 | 7 |
| `distractor_rules` | Extra rules that aren't needed for the proof | 0–8 | 1 | 2 | 3 |
| `query_literals` | Literals in α (2 gives α = A ∧ ¬B, so ¬α needs De Morgan) | 1–2 | 1 | 1 | 2 |
| `provable_share` | Share of questions where KB ⊨ α is True | 0.0–1.0 | 0.7 | 0.7 | 0.7 |

## `bayes.d_separation`

Formats: mcq, fill_blank

| Setting | What it controls | Range | Easy | Medium | Hard |
| --- | --- | --- | --- | --- | --- |
| `nodes` | Number of variables in the network | 3–8 | 5 | 6 | 7 |
| `edge_prob` | Chance of each possible edge (higher = denser network) | 0.15–0.8 | 0.35 | 0.35 | 0.4 |
| `max_parents` | Most parents any node can have | 1–4 | 2 | 3 | 3 |
| `max_observed` | Most observed (shaded) nodes | 0–3 | 1 | 2 | 2 |
| `collider_trap` | 1 = only ask queries where a collider mistake changes the answer | 0–1 | 1 | 1 | 1 |

## `bayes.enumeration`

Formats: mcq, fill_blank, steps

| Setting | What it controls | Range | Easy | Medium | Hard |
| --- | --- | --- | --- | --- | --- |
| `nodes` | Number of variables in the network | 2–6 | 3 | 4 | 4 |
| `evidence` | Number of evidence variables | 1–4 | 1 | 1 | 2 |
| `edge_prob` | Chance of each possible edge (higher = denser network) | 0.2–0.9 | 0.5 | 0.5 | 0.5 |
| `max_parents` | Most parents any node can have (CPT size grows as 2^parents) | 1–3 | 2 | 2 | 2 |

## `bayes.variable_elimination`

Formats: mcq, fill_blank, steps

| Setting | What it controls | Range | Easy | Medium | Hard |
| --- | --- | --- | --- | --- | --- |
| `nodes` | Number of variables in the network | 2–6 | 3 | 4 | 5 |
| `evidence` | Number of evidence variables | 1–4 | 1 | 1 | 2 |
| `edge_prob` | Chance of each possible edge (higher = denser network) | 0.2–0.9 | 0.5 | 0.5 | 0.5 |
| `max_parents` | Most parents any node can have (CPT size grows as 2^parents) | 1–3 | 2 | 2 | 2 |

## `bayes.mle_cpt`

Formats: mcq, fill_blank, steps

| Setting | What it controls | Range | Easy | Medium | Hard |
| --- | --- | --- | --- | --- | --- |
| `nodes` | Number of variables (the data table has 2^nodes rows) | 2–4 | 2 | 3 | 3 |
| `parents` | Parents of the variable being estimated | 1–3 | 1 | 1 | 2 |
| `edge_prob` | Chance of each possible edge | 0.3–1.0 | 1.0 | 0.5 | 0.7 |
| `max_count` | Largest count in any row of the data table | 3–30 | 9 | 9 | 9 |
| `min_condition_count` | Fewest samples matching the condition (avoids tiny denominators) | 1–20 | 3 | 3 | 3 |

## `decision.meu`

Formats: mcq, fill_blank, steps

| Setting | What it controls | Range | Easy | Medium | Hard |
| --- | --- | --- | --- | --- | --- |
| `chance_nodes` | Chance variables in the network | 2–5 | 2 | 3 | 4 |
| `edge_prob` | Chance of each possible edge between chance nodes | 0.3–0.9 | 0.6 | 0.6 | 0.5 |
| `max_parents` | Most parents any chance node can have | 1–3 | 2 | 2 | 2 |
| `utility_parents` | Chance variables the utility depends on (besides D) | 1–2 | 1 | 1 | 2 |
| `decision_children` | Chance variables the decision affects (0 = D only affects U, as in Classwork 4) | 0–2 | 0 | 0 | 1 |
| `evidence` | Observed chance variables | 0–2 | 1 | 1 | 2 |
| `min_gap` | Smallest allowed difference between EU(D=0) and EU(D=1) | 0–30 | 5 | 5 | 3 |

## `decision.vpi`

Formats: mcq, fill_blank, steps

| Setting | What it controls | Range | Easy | Medium | Hard |
| --- | --- | --- | --- | --- | --- |
| `chance_nodes` | Chance variables in the network | 2–5 | 2 | 3 | 4 |
| `edge_prob` | Chance of each possible edge between chance nodes | 0.3–0.9 | 0.6 | 0.6 | 0.5 |
| `max_parents` | Most parents any chance node can have | 1–3 | 2 | 2 | 2 |
| `utility_parents` | Chance variables the utility depends on (besides D) | 1–2 | 1 | 1 | 2 |
| `decision_children` | Chance variables the decision affects (0 = D only affects U, as in Classwork 4) | 0–2 | 0 | 0 | 1 |
| `evidence` | Observed chance variables | 0–2 | 0 | 1 | 2 |
| `zero_share` | Share of questions where the information is worthless (VPI = 0) | 0.0–1.0 | 0.15 | 0.15 | 0.15 |

## `bayes.do_query`

Formats: mcq, fill_blank, steps

| Setting | What it controls | Range | Easy | Medium | Hard |
| --- | --- | --- | --- | --- | --- |
| `nodes` | Variables in the network | 3–6 | 3 | 4 | 5 |
| `edge_prob` | Chance of each possible edge | 0.3–0.9 | 0.7 | 0.6 | 0.5 |
| `max_parents` | Most parents any node can have (also the size of the adjustment set) | 1–3 | 2 | 2 | 3 |
| `min_confounding` | Smallest required gap between P(y \| do(x)) and P(y \| x); 0 allows no confounding | 0.0–0.3 | 0.03 | 0.03 | 0.03 |
