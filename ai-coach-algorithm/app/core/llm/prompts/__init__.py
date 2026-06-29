"""5-layer prompt architecture.

Every LLM prompt in this system is composed of 5 conceptual layers:

  L1 系统人设层 (PersonaLayer)      — who the model is + supreme rules
  L2 上下文注入层 (ContextLayer)     — dynamic business data + history
  L3 核心指令层 (InstructionLayer)   — task with CoT step decomposition
  L4 边界规则层 (BoundaryLayer)      — negative rules / red lines / anti-hallucination
  L5 输出格式层 (FormatLayer)        — forced structured output (JSON or text)

Benefits:
  - testable: each layer is independently unit-testable
  - reusable: L1/L3/L4/L5 are largely shared between scorer and customer
  - cacheable: static layers (L1/L3/L4/L5 typically) render once per builder
  - prefix-cache-friendly: putting all static content first maximizes DeepSeek
    prompt prefix cache hit rate (10% cost vs 100%)
  - hallucination control: L4 is a dedicated layer for "must NOT" rules
"""
from app.core.llm.prompts.base import LayeredPromptBuilder, PromptLayer

__all__ = ["LayeredPromptBuilder", "PromptLayer"]
