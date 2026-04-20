"""Extract an :class:`ExtractedFamily` from a pedigree image.

The ``VisionExtractor`` depends on an ``LlmGateway`` abstraction so
tests can substitute a fake that returns a canned tool-use payload.
The concrete :class:`AnthropicVisionGateway` wraps the Anthropic SDK's
multimodal messages API (text + image in one user turn, tool-use to
force structured JSON back).
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any, Protocol, cast

from anthropic import Anthropic, AnthropicError, Omit, omit
from anthropic.types import MessageParam, ToolParam

from .extracted_family import ExtractedFamily
from .extraction_schema import (
    SYSTEM_PROMPT,
    ExtractionSchemaError,
    build_tool_schema,
    parse_extraction,
)
from .image_source import LoadedImage

DEFAULT_MODEL = "claude-opus-4-7"
DEFAULT_MAX_TOKENS = 2048
_USER_INSTRUCTION = (
    "Read the pedigree in this image and call the record_extracted_family tool "
    "with everything you can identify."
)


class LlmUnavailableError(RuntimeError):
    """Raised when the LLM provider is unreachable or returns an error."""


@dataclass(frozen=True)
class VisionRequest:
    model: str
    system_prompt: str
    user_text: str
    image: LoadedImage
    tool: dict[str, Any]
    max_tokens: int
    temperature: float | None


class LlmGateway(Protocol):
    """Narrow surface the extractor depends on; tests supply a fake."""

    def invoke_tool(self, request: VisionRequest) -> dict[str, Any]: ...


class VisionExtractor:
    def __init__(self, gateway: LlmGateway, *, model: str = DEFAULT_MODEL) -> None:
        self._gateway = gateway
        self._model = model

    def extract(self, image: LoadedImage) -> ExtractedFamily:
        tool_input = self._gateway.invoke_tool(
            VisionRequest(
                model=self._model,
                system_prompt=SYSTEM_PROMPT,
                user_text=_USER_INSTRUCTION,
                image=image,
                tool=build_tool_schema(),
                max_tokens=DEFAULT_MAX_TOKENS,
                temperature=None,
            )
        )
        try:
            return parse_extraction(tool_input)
        except ExtractionSchemaError:
            raise
        except (TypeError, ValueError) as exc:
            raise ExtractionSchemaError(f"Model output was not parseable: {exc}") from exc


class AnthropicVisionGateway:
    """Concrete :class:`LlmGateway` backed by the Anthropic multimodal API."""

    def __init__(self, api_key: str) -> None:
        self._client = Anthropic(api_key=api_key)

    def invoke_tool(self, request: VisionRequest) -> dict[str, Any]:
        tool_name = request.tool["name"]
        try:
            response = self._client.messages.create(
                model=request.model,
                max_tokens=request.max_tokens,
                temperature=_temperature_or_omit(request.temperature),
                system=request.system_prompt,
                tools=[cast("ToolParam", request.tool)],
                tool_choice={"type": "tool", "name": tool_name},
                messages=[_user_message(request.image, request.user_text)],
            )
        except AnthropicError as exc:
            raise LlmUnavailableError(f"Anthropic API call failed: {exc}") from exc
        return _extract_tool_input(response, tool_name)


def _temperature_or_omit(value: float | None) -> float | Omit:
    return omit if value is None else value


def _user_message(image: LoadedImage, text: str) -> MessageParam:
    image_block: dict[str, Any] = {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": image.media_type,
            "data": base64.standard_b64encode(image.data).decode("ascii"),
        },
    }
    text_block: dict[str, Any] = {"type": "text", "text": text}
    return cast("MessageParam", {"role": "user", "content": [image_block, text_block]})


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
