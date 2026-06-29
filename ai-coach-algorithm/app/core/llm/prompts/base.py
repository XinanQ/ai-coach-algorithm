"""5-layer prompt architecture — base classes.

A PromptLayer is one section of a prompt that knows how to render itself given
a context dict. Layers are tagged `is_dynamic`: dynamic layers re-render every
call (because the context changes), static layers render once and cache.

LayeredPromptBuilder stitches the layers in order. For DeepSeek prefix caching
to work, put all static layers FIRST (so identical byte prefixes accumulate
across requests). Only the trailing dynamic layers cause cache misses, and the
rest is billed at ~10% of normal rate.

A separate `system_layer` slot exists because the OpenAI Chat API wants the
persona/system prompt as a separate `role: "system"` message, not as part of
the user prompt body. The builder returns (system_text, user_text).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class PromptLayer(ABC):
    """One named section of a layered prompt.

    Subclasses override `render(context)`. Set `is_dynamic = True` when the
    layer's output depends on per-call context (e.g. dialog history); set
    `is_dynamic = False` for content that only depends on builder construction
    args (e.g. persona text, output schema) — those layers render once.
    """

    name: str = "unnamed"
    is_dynamic: bool = True

    @abstractmethod
    def render(self, context: dict[str, Any]) -> str: ...


@dataclass
class RenderedPrompt:
    """Output of LayeredPromptBuilder — paired system + user messages."""

    system: str
    user: str

    def to_chat_messages(self) -> list[dict[str, str]]:
        msgs: list[dict[str, str]] = []
        if self.system.strip():
            msgs.append({"role": "system", "content": self.system})
        if self.user.strip():
            msgs.append({"role": "user", "content": self.user})
        return msgs


class LayeredPromptBuilder:
    """Composes PromptLayers into a final (system, user) prompt pair.

    Pass the persona/system layer separately via `system_layer`; the other 4
    layers (context / instruction / boundary / format) go into `user_layers`
    in the order they should appear in the user message.

    Static layers are memoized on first render so repeated calls only re-render
    dynamic ones. The static cache is invalidated by constructing a new builder
    — by design, since changing the static config means a different prompt
    schema and should not be hot-swapped silently.
    """

    def __init__(
        self,
        system_layer: PromptLayer,
        user_layers: list[PromptLayer],
    ):
        self.system_layer = system_layer
        self.user_layers = list(user_layers)
        self._static_cache: dict[str, str] = {}

    def _render_layer(self, layer: PromptLayer, context: dict[str, Any]) -> str:
        if layer.is_dynamic:
            return layer.render(context)
        cached = self._static_cache.get(layer.name)
        if cached is None:
            cached = layer.render(context)
            self._static_cache[layer.name] = cached
        return cached

    def build(self, context: dict[str, Any] | None = None) -> RenderedPrompt:
        ctx = context or {}
        system_text = self._render_layer(self.system_layer, ctx)
        user_parts = [self._render_layer(layer, ctx) for layer in self.user_layers]
        # Two blank lines between sections so a reader (human or model) can scan
        # the 5-layer structure visually.
        user_text = "\n\n".join(part for part in user_parts if part.strip())
        return RenderedPrompt(system=system_text, user=user_text)

    def to_chat_messages(self, context: dict[str, Any] | None = None) -> list[dict[str, str]]:
        return self.build(context).to_chat_messages()
