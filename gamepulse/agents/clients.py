"""Chat clients for the agents (Microsoft Agent Framework).

- Azure OpenAI / Microsoft Foundry model deployment when `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY` are set
  (deployment name in `AZURE_OPENAI_DEPLOYMENT`), or a Foundry project when `FOUNDRY_PROJECT_ENDPOINT` is set (Azure CLI login).
- Otherwise an offline client: the same agents, tools and function-calling loop, but the "model" is a small deterministic planner.
  The demo and the tests never depend on a network or a key, and every number still comes from a tool call.
"""
from __future__ import annotations

import itertools
import os
from typing import Any, Callable, Optional

from agent_framework import BaseChatClient, ChatResponse, Content, FunctionInvocationLayer, Message

# planner(question, tool names) -> [(tool name, arguments)];  writer(question, [(tool name, result)]) -> answer text
Planner = Callable[[str, list[str]], list[tuple[str, dict[str, Any]]]]
Writer = Callable[[str, list[tuple[str, Any]]], str]


class OfflineChatClient(FunctionInvocationLayer, BaseChatClient):
    """Deterministic stand-in for a model: plans tool calls from the question, then writes the answer from the tool results."""

    OTEL_PROVIDER_NAME = "gamepulse-offline"

    def __init__(self, planner: Planner, writer: Writer, **kwargs):
        super().__init__(**kwargs)
        self._planner, self._writer = planner, writer
        self._ids = itertools.count(1)

    async def _inner_get_response(self, *, messages, stream, options, **kwargs):
        question = next((m.text for m in messages if m.role == "user" and m.text), "")
        calls = {c.call_id: c.name for m in messages for c in m.contents if c.type == "function_call"}
        results = [(calls.get(c.call_id, "?"), c.result) for m in messages for c in m.contents if c.type == "function_result"]
        if results:
            contents = [Content.from_text(self._writer(question, results))]
        else:
            names = [t.name for t in (options.get("tools") or []) if getattr(t, "name", None)]
            plan = [(n, a) for n, a in self._planner(question, names) if n in names]
            if plan:
                contents = [Content.from_function_call(call_id=f"call_{next(self._ids)}", name=n, arguments=a) for n, a in plan]
            else:
                contents = [Content.from_text(self._writer(question, []))]
        response = ChatResponse(messages=[Message(role="assistant", contents=contents)], response_id=f"offline-{next(self._ids)}")
        if stream:
            raise NotImplementedError("the offline client does not stream")
        return response


def backend() -> str:
    if os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_API_KEY"):
        return "azure-openai"
    if os.getenv("FOUNDRY_PROJECT_ENDPOINT"):
        return "foundry"
    return "offline"


def make_client(planner: Planner, writer: Writer):
    """The model behind an agent: Azure OpenAI / Foundry when configured, the offline planner otherwise."""
    kind = backend()
    if kind == "azure-openai":
        from agent_framework.openai import OpenAIChatCompletionClient

        return OpenAIChatCompletionClient(model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5.4-mini"), api_key=os.environ["AZURE_OPENAI_API_KEY"],
                                          azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                                          api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview"))
    if kind == "foundry":
        from agent_framework.foundry import FoundryChatClient
        from azure.identity import AzureCliCredential

        return FoundryChatClient(project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"], model=os.getenv("FOUNDRY_MODEL", "gpt-5.4-mini"),
                                 credential=AzureCliCredential())
    return OfflineChatClient(planner, writer)


def fmt(v: Optional[float], digits: int = 1) -> str:
    return "-" if v is None else f"{v:.{digits}f}"
