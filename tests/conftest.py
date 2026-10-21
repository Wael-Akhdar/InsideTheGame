"""Tests run offline and deterministic: ignore any model configured in .env (no network, no cost)."""
import os

for _k in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "FOUNDRY_PROJECT_ENDPOINT"):
    os.environ[_k] = ""  # set (empty) so that loading .env does not override it
