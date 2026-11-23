"""Write an HTML page of sample questions: python3 -m generators.preview [out.html]"""
from __future__ import annotations

import sys
from html import escape
from pathlib import Path

from . import CODE, FILL_BLANK, MCQ, STEPS, make_question
from .bayes import DoQuery, DSeparation, Enumeration, MaximumLikelihood, VariableElimination
from .decision import MaximumExpectedUtility, ValueOfInformation
from .core import as_text
from .graphs import diagram_to_svg
from .logic import CNFConversion, Entailment, Refutation, Resolution
from . import python as py

SAMPLES = [
    (MaximumExpectedUtility, 3, "medium", STEPS),
    (ValueOfInformation, 3, "medium", STEPS),
    (DoQuery, 2, "medium", MCQ),
    (Enumeration, 4, "medium", STEPS),
    (Entailment, 4, "medium", STEPS),
    (Resolution, 3, "medium", MCQ),
    (CNFConversion, 2, "hard", STEPS),
    (Refutation, 5, "hard", STEPS),
    (VariableElimination, 3, "hard", STEPS),
    (MaximumLikelihood, 2, "hard", FILL_BLANK),
    (DSeparation, 3, "hard", MCQ),
]
PYTHON_SAMPLES = [
    (py.WriteFunction, 1, "hard", CODE),
    (py.WriteFunction, 3, "medium", MCQ),
    (py.RangeLoop, 3, "medium", MCQ),
    (py.RangeWrite, 2, "hard", MCQ),
    (py.Conditionals, 5, "medium", STEPS),
    (py.Variables, 3, "hard", STEPS),
    (py.ListLength, 4, "medium", MCQ),
    (py.ListAliasing, 6, "hard", MCQ),
    (py.StringSlicing, 2, "hard", STEPS),
    (py.DivisionOperators, 7, "hard", MCQ),
    (py.LoopCount, 4, "hard", MCQ),
]
FORMAT_NAMES = {MCQ: "multiple choice", FILL_BLANK: "fill in the blank", STEPS: "step by step", CODE: "write code"}

CSS = """
:root{--bg:#f4f5f7;--card:#fff;--ink:#1d2733;--muted:#5d6b7a;--line:#dde2e8;--good:#16794c;--tag:#eef3fb}
@media (prefers-color-scheme:dark){:root{--bg:#14181d;--card:#1d232a;--ink:#e6ebf0;--muted:#9aa7b4;--line:#2f3943;--good:#4cc38a;--tag:#24303d}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 -apple-system,Segoe UI,Helvetica,Arial,sans-serif}
main{max-width:720px;margin:0 auto;padding:20px 16px 48px}h1{font-size:22px;margin:0 0 4px}.sub{color:var(--muted);margin:0 0 20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;margin:0 0 18px}
.meta{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}.tag{background:var(--tag);border-radius:99px;padding:2px 10px;font-size:13px;color:var(--muted)}
.fig{background:#fff;border-radius:10px;padding:6px;text-align:center;margin-bottom:6px}.fig svg{max-width:100%;height:auto}
ol.opts{padding-left:0;list-style:none;margin:12px 0}ol.opts li{border:1px solid var(--line);border-radius:10px;padding:8px 12px;margin:6px 0}
ol.opts li.correct{border-color:var(--good);color:var(--good);font-weight:600}.why{display:block;font-size:12px;color:var(--muted);font-weight:400}
.editor{border:1px dashed var(--muted);border-radius:10px;min-height:90px;padding:10px;color:var(--muted);font:13px ui-monospace,Menlo,monospace;margin:8px 0}
.optcode{white-space:pre;font:13px/1.45 ui-monospace,Menlo,monospace;overflow-x:auto;display:block}
.pass{color:var(--good)}.fail{color:#d9534f}
.blank{border-bottom:2px solid var(--muted);min-width:120px;width:45%;height:24px;display:inline-block;vertical-align:bottom;margin-left:6px}
ol.steps{padding-left:22px;margin:10px 0}ol.steps li{margin:8px 0}.ans{color:var(--good);font-size:13px;display:block}
table{border-collapse:collapse;margin:6px 10px 6px 0;font-size:14px;display:inline-table;vertical-align:top}
caption{text-align:left;font-size:12px;color:var(--muted);padding-bottom:2px}th,td{border:1px solid var(--line);padding:3px 9px;text-align:center}
th{background:var(--tag);font-weight:600}details{margin-top:10px}summary{cursor:pointer;color:var(--muted)}
.code{background:#0f1720;color:#e6edf3;border-radius:10px;padding:12px 14px;font:14px/1.5 ui-monospace,Menlo,monospace;white-space:pre;overflow-x:auto;margin:6px 0}
pre{white-space:pre-wrap;font:13px/1.55 ui-monospace,Menlo,monospace;margin:8px 0 0}
"""


def table_html(t) -> str:
    head = "".join(f"<th>{escape(c)}</th>" for c in t.columns if c)
    rows = "".join("<tr>" + "".join(f"<td>{escape(v)}</td>" for v in r) + "</tr>" for r in t.rows)
    return f"<table><caption>{escape(t.title)}</caption>{f'<tr>{head}</tr>' if head else ''}{rows}</table>"


def card(gen, q) -> str:
    body = []
    if q.diagram:
        body.append(f"<div class='fig'>{diagram_to_svg(q.diagram)}</div>")
    if q.tables:
        body.append(f"<div>{''.join(table_html(t) for t in q.tables)}</div>")
    body.append(f"<p>{escape(q.prompt)}</p>")
    if q.code:
        body.append(f"<div class='code'>{escape(q.code)}</div>")
    if q.format == MCQ:
        items = []
        for letter, text in zip("ABCD", q.options):
            trap = q.diagnose(text)
            why = f"<span class='why'>trap: {escape(gen.misconceptions[trap])}</span>" if trap else ""
            shown = f"<span class='optcode'>{escape(text)}</span>" if "\n" in text else escape(text)
            items.append(f"<li class='{'correct' if q.check(text) else ''}'>{letter}. {shown}{why}</li>")
        body.append(f"<ol class='opts'>{''.join(items)}</ol>")
    elif q.format == STEPS:
        items = []
        for b in q.blanks:
            shown = f"{b.value:.4g}" if isinstance(b.value, float) else as_text(b.value)
            items.append(f"<li>{escape(b.label)} <span class='blank'></span><span class='ans'>{escape(shown)}</span></li>")
        body.append(f"<ol class='steps'>{''.join(items)}</ol>")
    elif q.format == CODE:
        body.append("<div class='editor'># write your function here</div>")
        demo = q.wrong[0]
        rows = q.answer_value.feedback(demo.answer.source)
        cells = "".join(
            f"<tr><td>{escape(str(r['input']))}</td><td>{escape(repr(r['expected']))}</td>"
            f"<td>{escape(repr(r['got']))}</td><td class='{'pass' if r['passed'] else 'fail'}'>{'✓' if r['passed'] else '✗'}</td></tr>"
            for r in rows if "input" in r)
        trap = gen.misconceptions.get(q.diagnose(demo.answer.source) or "", "")
        body.append(
            f"<details open><summary>Example: what a student sees for a buggy submission</summary>"
            f"<div class='code'>{escape(demo.answer.source)}</div>"
            f"<table><tr><th>input</th><th>expected</th><th>got</th><th></th></tr>{cells}</table>"
            f"<p class='why'>Diagnosis: {escape(trap)}</p></details>")
    else:
        body.append("<p>Answer: <span class='blank'></span></p>")
    body.append(
        f"<details><summary>Worked solution</summary><pre>Answer: {escape(q.answer)}\n{escape(q.explanation)}</pre></details>"
    )
    return (
        f"<section class='card'><div class='meta'><span class='tag'>{q.generator_id}</span>"
        f"<span class='tag'>{q.difficulty}</span><span class='tag'>{FORMAT_NAMES[q.format]}</span></div>"
        f"{''.join(body)}</section>"
    )


def build(path: Path, samples=SAMPLES, title="Generator samples",
          subtitle="Decision networks and do-queries (Classwork 4), logic (Classwork 2) and Bayes net generators.") -> list:
    questions = [(G(), make_question(G(), seed, d, f)) for G, seed, d, f in samples]
    html = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>Generator samples</title><style>{CSS}</style></head><body><main>"
        f"<h1>{title}</h1><p class='sub'>{subtitle} "
        "Step-by-step questions show each blank with its expected answer in green; multiple choice shows the "
        "misconception behind each wrong option.</p>"
        f"{''.join(card(g, q) for g, q in questions)}</main></body></html>"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return questions


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "python":
        out = Path("preview/python.html")
        build(out, PYTHON_SAMPLES, "Intro Python generators",
              "Every question is a fresh random program; wrong answers come from running it with a misconception. Write-code questions are marked by unit tests.")
    else:
        out = Path(sys.argv[1] if len(sys.argv) > 1 else "preview/samples.html")
        build(out)
    print(f"wrote {out}")
