"""LLM access. Uses Azure OpenAI (Microsoft Foundry deployment) when configured,
otherwise returns None so agents fall back to deterministic templates (offline demo / tests)."""
from __future__ import annotations

import os
from typing import Optional


class LLM:
    def __init__(self):
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.key = os.getenv("AZURE_OPENAI_API_KEY")
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
        self.version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
        self._client = None

    @property
    def enabled(self) -> bool:
        return bool(self.endpoint and self.key)

    def _get(self):
        if self._client is None:
            from openai import AzureOpenAI  # lazy import: optional dependency at runtime
            self._client = AzureOpenAI(azure_endpoint=self.endpoint, api_key=self.key, api_version=self.version)
        return self._client

    def complete(self, system: str, user: str, max_tokens: int = 220) -> Optional[str]:
        if not self.enabled:
            return None
        try:
            r = self._get().chat.completions.create(
                model=self.deployment, max_tokens=max_tokens, temperature=0.7,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            )
            return r.choices[0].message.content.strip()
        except Exception as exc:  # never break the live pipeline on an LLM hiccup
            print(f"[llm] fallback to templates: {exc}")
            return None
