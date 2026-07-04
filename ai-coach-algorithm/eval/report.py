"""Report generation for evaluation results."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from eval.metrics import StageResult


def build_report(results: list[StageResult], run_id: str | None = None) -> dict[str, Any]:
    if not run_id:
        run_id = f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    stages = [r.to_dict() for r in results]
    values = [r.value for r in results if r.value > 0]
    e2e = 1.0
    for v in values:
        e2e *= v

    bottleneck = min(results, key=lambda r: r.value).stage if results else "none"
    runtime_info: dict[str, Any] = {}
    for result in results:
        stage_runtime = result.details.get("runtime_info")
        if isinstance(stage_runtime, dict):
            runtime_info.update(stage_runtime)

    report = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "stages": stages,
        "end_to_end_estimate": round(e2e, 4) if values else None,
        "bottleneck": bottleneck,
    }
    if runtime_info:
        report["runtime_info"] = runtime_info
    return report


def format_ascii_table(report: dict[str, Any]) -> str:
    lines = [
        f"=== RAG Evaluation Report: {report['run_id']} ===",
        f"Timestamp: {report['timestamp']}",
        "",
        f"{'Stage':<25} {'Metric':<15} {'Value':<10} {'Gold Size':<10}",
        "-" * 60,
    ]
    for stage in report["stages"]:
        lines.append(
            f"{stage['stage']:<25} {stage['primary_metric']:<15} {stage['value']:<10.4f} {stage['gold_size']:<10}"
        )
    lines.append("-" * 60)
    if report.get("end_to_end_estimate") is not None:
        lines.append(f"End-to-end estimate: {report['end_to_end_estimate']:.4f}")
    lines.append(f"Bottleneck: {report['bottleneck']}")
    return "\n".join(lines)


def save_report(report: dict[str, Any], path: str = "data/eval/report.json") -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(format_ascii_table(report))
    print(f"\nReport saved to {path}")
