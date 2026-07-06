"""Report generation for evaluation results."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from eval.metrics import StageResult


def _product(values: list[float]) -> float | None:
    if not values:
        return None
    result = 1.0
    for value in values:
        result *= value
    return result


def build_report(results: list[StageResult], run_id: str | None = None) -> dict[str, Any]:
    if not run_id:
        run_id = f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    stages = [r.to_dict() for r in results]
    component_results = [r for r in results if r.stage != "e2e_dialogue"]
    component_values = [r.value for r in component_results]
    component_quality_estimate = _product(component_values)

    e2e_result = next((r for r in results if r.stage == "e2e_dialogue"), None)
    if e2e_result is not None:
        end_to_end_value = e2e_result.value
        end_to_end_source = "e2e_dialogue"
    else:
        end_to_end_value = component_quality_estimate
        end_to_end_source = "component_product"

    bottleneck_pool = component_results or results
    bottleneck = min(bottleneck_pool, key=lambda r: r.value).stage if bottleneck_pool else "none"
    runtime_info: dict[str, Any] = {}
    for result in results:
        stage_runtime = result.details.get("runtime_info")
        if isinstance(stage_runtime, dict):
            runtime_info.update(stage_runtime)

    report = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "stages": stages,
        "end_to_end_estimate": round(end_to_end_value, 4) if end_to_end_value is not None else None,
        "end_to_end_metric_source": end_to_end_source,
        "component_quality_estimate": round(component_quality_estimate, 4) if component_quality_estimate is not None else None,
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
        f"{'Stage':<25} {'Metric':<24} {'Value':<10} {'Gold Size':<10}",
        "-" * 72,
    ]
    for stage in report["stages"]:
        lines.append(
            f"{stage['stage']:<25} {stage['primary_metric']:<24} {stage['value']:<10.4f} {stage['gold_size']:<10}"
        )
    lines.append("-" * 72)
    if report.get("end_to_end_estimate") is not None:
        if report.get("end_to_end_metric_source") == "e2e_dialogue":
            lines.append(f"End-to-end actual: {report['end_to_end_estimate']:.4f}")
        else:
            lines.append(f"End-to-end estimate: {report['end_to_end_estimate']:.4f}")
    if report.get("component_quality_estimate") is not None:
        lines.append(f"Component quality estimate: {report['component_quality_estimate']:.4f}")
    lines.append(f"Bottleneck: {report['bottleneck']}")
    return "\n".join(lines)


def save_report(report: dict[str, Any], path: str = "data/eval/report.json") -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(format_ascii_table(report))
    print(f"\nReport saved to {path}")
