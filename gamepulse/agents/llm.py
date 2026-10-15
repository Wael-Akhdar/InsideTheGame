"""LLM access. Uses Azure OpenAI (Microsoft Foundry deployment) when configured,
otherwise returns None so agents fall back to deterministic templates (offline demo / tests)."""
from __future__ import annotations

import json
import os
import re
from typing import Any, Optional


class LLM:
    def __init__(self):
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.key = os.getenv("AZURE_OPENAI_API_KEY")
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5.4-mini")
        self.version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
        self._client = None

        self.github_token = os.getenv("GITHUB_MODELS_TOKEN")
        if not (self.endpoint and self.key) and self.github_token:
            self.deployment = os.getenv("GITHUB_MODEL", "openai/gpt-4.1-mini")

    @property
    def enabled(self) -> bool:
        return bool(self.endpoint and self.key) or bool(self.github_token)

    def _get(self):
        if self._client is None:  # lazy import: optional dependency at runtime
            if self.endpoint and self.key:
                from openai import AzureOpenAI
                self._client = AzureOpenAI(azure_endpoint=self.endpoint, api_key=self.key, api_version=self.version)
            else:  # GitHub Models (OpenAI-compatible endpoint)
                from openai import OpenAI
                self._client = OpenAI(base_url="https://models.github.ai/inference", api_key=self.github_token)
        return self._client

    def complete(self, system: str, user: str, max_tokens: int = 220) -> Optional[str]:
        if not self.enabled:
            return None
        try:
            # reasoning models (gpt-5 family) take max_completion_tokens and no temperature; the budget covers their reasoning too
            r = self._get().chat.completions.create(
                model=self.deployment, max_completion_tokens=max_tokens * 6,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            )
            return r.choices[0].message.content.strip()
        except Exception as exc:  # never break the live pipeline on an LLM hiccup
            print(f"[llm] fallback to templates: {exc}")
            return None

    def complete_json(self, system: str, user: str, max_tokens: int = 500) -> Optional[dict[str, Any]]:
        """Ask for a JSON object. Returns None when the LLM is unavailable or answers garbage (callers then fall back)."""
        text = self.complete(system + " Reply with a single JSON object and nothing else.", user, max_tokens)
        if not text:
            return None
        m = re.search(r"\{.*\}", text, re.S)
        try:
            return json.loads(m.group(0)) if m else None
        except json.JSONDecodeError:
            return None
