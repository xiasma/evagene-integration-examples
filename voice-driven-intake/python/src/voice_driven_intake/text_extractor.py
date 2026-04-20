"""Extract an :class:`ExtractedFamily` from a spoken-transcript string.

The ``TextExtractor`` depends on an ``LlmGateway`` abstraction so tests
can substitute a fake that returns a canned tool-use payload. The
concrete :class:`AnthropicGateway` wraps the official Anthropic SDK.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, cast

from anthropic import Anthropic, AnthropicError
from anthropic.types import ToolParam

from .extracted_family import ExtractedFamily
from .extraction_schema import (
    SYSTEM_PROMPT,
    ExtractionSchemaError,
    build_tool_schema,
    parse_extraction,
)

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 2048


class LlmUnavailableError(RuntimeError):
    """Raised when the LLM provider is unreachable or returns an error."""


@dataclass(frozen=True)
class LlmRequest:
    model: str
    system_prompt: str
    user_prompt: str
    tool: dict[str, Any]
    max_tokens: int
    temperature: float


class LlmGateway(Protocol):
    """Narrow surface the extractor depends on; tests supply a fake."""

    def invoke_tool(self, request: LlmRequest) -> dict[str, Any]: ...


class TextExtractor:
    def __init__(self, gateway: LlmGateway, *, model: str = DEFAULT_MODEL) -> None:
        self._gateway = gateway
        self._model = model

    def extract(self, transcript: str) -> ExtractedFamily:
        tool_input = self._gateway.invoke_tool(
            LlmRequest(
                model=self._model,
                system_prompt=SYSTEM_PROMPT,
                user_prompt=transcript,
                tool=build_tool_schema(),
                max_tokens=DEFAULT_MAX_TOKENS,
                temperature=0.0,
            )
        )
        try:
            return parse_extraction(tool_input)
        except ExtractionSchemaError:
            raise
        except (TypeError, ValueError) as exc:
            raise ExtractionSchemaError(f"Model output was not parseable: {exc}") from exc


class AnthropicGateway:
    """Concrete :class:`LlmGateway` backed by the Anthropic SDK."""

    def __init__(self, api_key: str) -> None:
        self._client = Anthropic(api_key=api_key)

    def invoke_tool(self, request: LlmRequest) -> dict[str, Any]:
        tool_name = request.tool["name"]
        try:
            response = self._client.messages.create(
                model=request.model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                system=request.system_prompt,
                tools=[cast("ToolParam", request.tool)],
                tool_choice={"type": "tool", "name": tool_name},
                messages=[{"role": "user", "content": request.user_prompt}],
            )
        except AnthropicError as exc:
            raise LlmUnavailableError(f"Anthropic API call failed: {exc}") from exc
        return _extract_tool_input(response, tool_name)


def _extract_tool_input(response: Any, tool_name: str) -> dict[str, Any]:
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == tool_name:
            tool_input = getattr(block, "input", None)
            if not isinstance(tool_input, dict):
                raise ExtractionSchemaError(
                    f"Tool-use block for {tool_name!r} did not carry a dict input."
                )
            return tool_input
    raise ExtractionSchemaError(
        f"Anthropic response did not include a tool_use block for {tool_name!r}."
    )
