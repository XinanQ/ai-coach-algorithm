from __future__ import annotations

from typing import Any

from app.core.marketing_rag import retrieve_marketing_knowledge
from app.core.memory_manager import get_memory_manager


def build_tutor_prompt_context(
    employee_answer: str,
    user_id: str | None = None,
    scenario_id: str | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    knowledge = retrieve_marketing_knowledge(employee_answer, route="tutor", top_k=top_k, scene_id=scenario_id)
    history = get_memory_manager().retrieve_history(employee_answer, user_id=user_id, scenario_id=scenario_id, limit=3)
    return {
        "system_persona_layer": "你是金融营销场景的AI导师，关注合规、客户需求识别、产品解释和下一步引导。",
        "context_injection_layer": {
            "retrieved_knowledge": knowledge.get("items", []),
            "long_term_history": history,
        },
        "core_instruction_layer": "请基于员工回答拆解意图、合规风险、知识覆盖和可执行改进建议。",
        "boundary_rule_layer": ["禁止编造具体利率", "禁止承诺收益", "禁止输出未检索到的政策细节"],
        "output_format_layer": {
            "type": "json",
            "fields": ["score", "weakness_tags", "evidence", "next_practice_suggestion"],
        },
        "retrieval_backend": knowledge.get("retrieval_backend"),
    }

