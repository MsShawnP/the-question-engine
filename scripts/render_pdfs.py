"""
Phase 4 render pipeline — renders every non-stub question to a one-page PDF.

Usage:
    python -m scripts.render_pdfs              # all non-stub questions
    python -m scripts.render_pdfs q01 q10      # subset

Output: static/pdfs/{question_id}.pdf (pre-rendered artifacts served by
GET /api/pdf/{question_id}).

Requires: DATABASE_URL reachable (local dev: `fly proxy 5432 -a cinderhaven-db`)
and quarto on PATH with a working knitr toolchain.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
TEMPLATE = ROOT / "quarto" / "_template.qmd"
OUT_DIR = ROOT / "static" / "pdfs"

os.environ.setdefault("PYTHONPATH", str(ROOT))
sys.path.insert(0, str(ROOT))

from engine.registry import registry  # noqa: E402


def tex_esc(s: str) -> str:
    """Escape LaTeX special characters. Backslash first via sentinel so the
    replacement's own braces are not double-escaped."""
    s = s.replace("\\", "\x00")
    for ch, rep in (
        ("{", r"\{"), ("}", r"\}"), ("&", r"\&"), ("%", r"\%"),
        ("$", r"\$"), ("#", r"\#"), ("_", r"\_"),
        ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}"),
    ):
        s = s.replace(ch, rep)
    return s.replace("\x00", r"\textbackslash{}")


def key_numbers_tex(key_numbers) -> str:
    """Build pre-escaped LaTeX tabular rows: bold navy value | label (+ context)."""
    rows = []
    for kn in key_numbers:
        label = tex_esc(kn.label)
        if kn.context:
            label += (r" \newline \textcolor{textsec}{\footnotesize "
                      + tex_esc(kn.context) + "}")
        value = r"\textcolor{navy}{\textbf{" + tex_esc(kn.value) + "}}"
        rows.append(f"{value} & {label} \\\\[0.06in]")
    return "\n".join(rows)


def render_one(question) -> tuple[str, bool, str]:
    """Run a question and render its PDF. Returns (id, ok, note)."""
    qid = question.meta().id
    try:
        r = question.run()
    except Exception as exc:  # surface DB/rule failures per-question
        return qid, False, f"run() failed: {exc}"

    params = {
        "question": r.question,
        "verdict": r.verdict,
        "verdict_detail": r.verdict_detail,
        "key_numbers_tex": key_numbers_tex(r.key_numbers),
        "rule_explanation": r.rule_explanation,
        "go_deeper_link": r.go_deeper_link or "",
        "go_deeper_label": r.go_deeper_label or "",
        "scenario": r.scenario or "baseline",
        "source_piece": r.source_piece or "",
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        yaml.dump(params, f, allow_unicode=True, default_flow_style=False)
        params_file = f.name

    try:
        # Quarto writes --output relative to the process CWD, not the template dir.
        result = subprocess.run(
            ["quarto", "render", str(TEMPLATE),
             "--execute-params", params_file,
             "--output", f"{qid}.pdf",
             "--no-cache"],
            capture_output=True, text=True, cwd=str(ROOT),
        )
    finally:
        os.unlink(params_file)

    rendered = ROOT / f"{qid}.pdf"
    out_pdf = OUT_DIR / f"{qid}.pdf"
    if result.returncode == 0 and rendered.exists():
        shutil.move(str(rendered), str(out_pdf))
        return qid, True, f"{out_pdf.stat().st_size // 1024} KB"
    if result.returncode == 0 and out_pdf.exists():
        return qid, True, f"{out_pdf.stat().st_size // 1024} KB (in place)"
    tail = (result.stderr or result.stdout or "")[-400:].replace("\n", " | ")
    return qid, False, f"quarto rc={result.returncode}: {tail}"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    wanted = set(sys.argv[1:])
    questions = [
        q for q in registry.all()
        if not q.meta().is_stub and (not wanted or q.meta().id in wanted)
    ]
    if not questions:
        print("No matching non-stub questions.")
        return 1

    results = []
    for q in sorted(questions, key=lambda x: x.meta().id):
        qid = q.meta().id
        print(f"[{qid}] running + rendering...", flush=True)
        outcome = render_one(q)
        if not outcome[1]:
            # Windows batch renders occasionally hit transient intermediate-file
            # locks; one retry clears them.
            print(f"[{qid}] failed, retrying once...", flush=True)
            outcome = render_one(q)
        results.append(outcome)

    print("\n--- render summary ---")
    failed = 0
    for qid, ok, note in results:
        print(f"  {qid}: {'OK' if ok else 'FAILED'} — {note}")
        failed += 0 if ok else 1
    print(f"{len(results) - failed}/{len(results)} rendered to {OUT_DIR}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
