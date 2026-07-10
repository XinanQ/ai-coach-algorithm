"""Regression gate: run the frozen-baseline suites and fail on any breach.

A frozen baseline only protects the codebase if something runs it
automatically. This script is that something — run it before merging any
change that touches scoring, retrieval, prompts, or eval code:

    python scripts/regression_gate.py                # all gates (scorer needs DEEPSEEK_API_KEY)
    python scripts/regression_gate.py --skip-scorer  # deterministic gates only (free, offline)

Exit code 0 = all gates green; 1 = at least one breach (details printed).
Thresholds live in data/eval/regression_thresholds.json — floors sit slightly
below the frozen baselines so run noise doesn't flap the gate. Lowering a
floor requires a documented reason in that file.

The scorer gate additionally verifies the config fingerprint: if the scorer
changed since the blessed baseline, the gate fails until the 50-case suite is
re-run and re-blessed (eval.stages.eval_scorer --bless-fingerprint).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Running as `python scripts/regression_gate.py` puts scripts/ (not the project
# root) on sys.path — bootstrap the root so `eval.*` / `app.*` import.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

THRESHOLDS_PATH = Path("data/eval/regression_thresholds.json")


def _run_stage(name: str):
    if name == "gap":
        from eval.stages.eval_gap import evaluate
        return evaluate()
    if name == "retrieval":
        from eval.stages.eval_retrieval import evaluate
        return evaluate(candidate_k=40, final_k=8)
    if name == "must_point":
        from eval.stages.eval_must_point import evaluate
        return evaluate()
    if name == "scorer":
        from eval.stages.eval_scorer import evaluate
        return evaluate(require_llm=True)
    raise ValueError(name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-scorer", action="store_true",
                        help="Skip the LLM scorer gate (offline / no API key).")
    args = parser.parse_args()

    thresholds = json.loads(THRESHOLDS_PATH.read_text(encoding="utf-8"))
    stages = ["gap", "retrieval", "must_point"] + ([] if args.skip_scorer else ["scorer"])

    breaches: list[str] = []
    lines: list[str] = []
    for stage in stages:
        spec = thresholds.get(stage)
        if spec is None:
            continue
        try:
            result = _run_stage(stage)
        except Exception as exc:
            breaches.append(f"{stage}: FAILED TO RUN — {exc}")
            lines.append(f"  {stage:<12} ERROR  {exc}")
            continue

        value = result.value
        floor = spec.get("min")
        ok = floor is None or value >= floor
        mark = "OK  " if ok else "FAIL"
        lines.append(f"  {stage:<12} {mark} {result.primary_metric}={value:.4f} (floor {floor})")
        if not ok:
            breaches.append(f"{stage}: {result.primary_metric}={value:.4f} < floor {floor}")

        if stage == "scorer":
            details = result.details
            for key, rule in thresholds.get("scorer_details", {}).items():
                dv = details.get(key)
                if dv is None:
                    continue
                bad = ("min" in rule and dv < rule["min"]) or ("max" in rule and dv > rule["max"])
                lines.append(f"  {'scorer.' + key:<28} {'FAIL' if bad else 'OK  '} {dv} (rule {rule})")
                if bad:
                    breaches.append(f"scorer.{key}={dv} violates {rule}")
            if details.get("baseline_fingerprint_match") is False:
                breaches.append(
                    "scorer config fingerprint changed since blessed baseline — "
                    "rerun full suite and re-bless (--bless-fingerprint)"
                )
                lines.append("  scorer.fingerprint           FAIL config drift vs blessed baseline")
            if not details.get("citable_full_baseline", False):
                breaches.append("scorer run is not a citable full baseline (subset/fallback/fingerprint drift)")

    print("Regression gate results:")
    print("\n".join(lines))
    if breaches:
        print("\nGATE FAILED:")
        for b in breaches:
            print(f"  - {b}")
        return 1
    print("\nGATE PASSED — frozen baselines intact.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
