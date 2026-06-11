"""
Gate 1 render proof — renders one question to PDF and reports.
Usage: python -m scripts.render_proof [question_id]
Default: q10
"""
import os
import sys
import shutil
import subprocess
import tempfile
import yaml
from pathlib import Path

ROOT = Path(__file__).parent.parent
TEMPLATE = ROOT / "quarto" / "_template.qmd"
OUT_DIR = ROOT / "static" / "pdfs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("PYTHONPATH", str(ROOT))

question_id = sys.argv[1] if len(sys.argv) > 1 else "q10"

print(f"Importing {question_id}...")
if question_id == "q10":
    from engine.questions.q10_deduction_recovery import DeductionRecoveryQuestion
    q = DeductionRecoveryQuestion()
elif question_id == "q12":
    from engine.questions.q12_forecast_accuracy import ForecastAccuracyQuestion
    q = ForecastAccuracyQuestion()
elif question_id == "q01":
    from engine.questions.q01_biggest_customer import BiggestCustomerQuestion
    q = BiggestCustomerQuestion()
else:
    raise ValueError(f"Unknown question_id for render proof: {question_id}")

print("Running question...")
r = q.run()
print(f"  verdict: {r.verdict[:60]}...")
print(f"  verdict_detail: {r.verdict_detail}")
print(f"  key_numbers: {[(kn.label, kn.value) for kn in r.key_numbers]}")

# Params passed raw — the template's tex_esc() R function handles LaTeX escaping
# inside {=latex} raw blocks, bypassing pandoc's markdown parser.
params = {
    "question": r.question,
    "verdict": r.verdict,
    "verdict_detail": r.verdict_detail,
    # key_numbers excluded: Quarto reserves the `value:` key in param dicts;
    # rendered separately in Gate 2 via a JSON string param.
    "key_numbers_json": "[]",
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

out_pdf = OUT_DIR / f"{question_id}.pdf"
print(f"Rendering to {out_pdf}...")

# Run from ROOT so --output places the file at ROOT/{question_id}.pdf (Quarto
# writes to the process CWD, not the template directory).
cmd = [
    "quarto", "render", str(TEMPLATE),
    "--execute-params", params_file,
    "--output", f"{question_id}.pdf",
    "--no-cache",
]
result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
print("STDOUT:", result.stdout[-2000:] if result.stdout else "(none)")
print("STDERR:", result.stderr[-3000:] if result.stderr else "(none)")
print("Return code:", result.returncode)

os.unlink(params_file)

rendered_pdf = ROOT / f"{question_id}.pdf"  # Quarto writes to CWD
if result.returncode == 0 and rendered_pdf.exists():
    shutil.move(str(rendered_pdf), str(out_pdf))
    size_kb = out_pdf.stat().st_size // 1024
    print(f"\nSUCCESS: {out_pdf} ({size_kb} KB)")
elif result.returncode == 0 and out_pdf.exists():
    size_kb = out_pdf.stat().st_size // 1024
    print(f"\nSUCCESS (already in place): {out_pdf} ({size_kb} KB)")
else:
    print("\nFAILED: PDF not produced")
    sys.exit(1)
