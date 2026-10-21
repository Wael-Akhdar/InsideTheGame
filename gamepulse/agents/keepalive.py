"""Keep the fine-tuned model deployed.

Developer deployments of fine-tuned models have no hourly fee but are removed after 24 hours. When the app runs on Azure with a
managed identity allowed to manage the Foundry resource, this task checks the deployment every 30 minutes and recreates it
when it is gone (Azure Resource Manager API). Meanwhile the agents answer with the offline planner, so nothing breaks.

Configuration (environment variables, all required to enable it):
    AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP, AZURE_FOUNDRY_ACCOUNT  (the Foundry / Azure OpenAI resource)
    AZURE_OPENAI_DEPLOYMENT                                              (deployment name, e.g. gamepulse-commentator)
    AZURE_FT_MODEL                                                       (fine-tuned model name shown in Foundry)
Optional: AZURE_FT_CAPACITY (tokens per minute in thousands, default 50), KEEPALIVE_MINUTES (default 30).
"""
from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.request

API = "2024-10-01"
STATE: dict = {"enabled": False, "last": None, "error": None}


def _cfg() -> dict | None:
    keys = ("AZURE_SUBSCRIPTION_ID", "AZURE_RESOURCE_GROUP", "AZURE_FOUNDRY_ACCOUNT", "AZURE_OPENAI_DEPLOYMENT", "AZURE_FT_MODEL")
    if not all(os.getenv(k) for k in keys):
        return None
    return {k: os.environ[k] for k in keys}


def _url(c: dict) -> str:
    return (f"https://management.azure.com/subscriptions/{c['AZURE_SUBSCRIPTION_ID']}/resourceGroups/{c['AZURE_RESOURCE_GROUP']}"
            f"/providers/Microsoft.CognitiveServices/accounts/{c['AZURE_FOUNDRY_ACCOUNT']}/deployments/{c['AZURE_OPENAI_DEPLOYMENT']}"
            f"?api-version={API}")


def _token() -> str:
    from azure.identity import ManagedIdentityCredential

    return ManagedIdentityCredential().get_token("https://management.azure.com/.default").token


def ensure_deployed() -> str:
    """Check the deployment once; recreate it if it is missing. Returns what happened."""
    c = _cfg()
    if c is None:
        return "disabled"
    headers = {"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"}
    try:
        with urllib.request.urlopen(urllib.request.Request(_url(c), headers=headers), timeout=30) as r:
            state = json.loads(r.read()).get("properties", {}).get("provisioningState", "?")
            return f"present ({state})"
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
    body = {"sku": {"name": "DeveloperTier", "capacity": int(os.getenv("AZURE_FT_CAPACITY", "50"))},
            "properties": {"model": {"format": "OpenAI", "name": c["AZURE_FT_MODEL"], "version": "1"}}}
    req = urllib.request.Request(_url(c), data=json.dumps(body).encode(), headers=headers, method="PUT")
    with urllib.request.urlopen(req, timeout=60) as r:
        return f"recreated (HTTP {r.status})"


async def keep_alive_loop() -> None:
    if _cfg() is None:
        return
    STATE["enabled"] = True
    minutes = float(os.getenv("KEEPALIVE_MINUTES", "30"))
    while True:
        try:
            STATE["last"] = await asyncio.to_thread(ensure_deployed)
            STATE["error"] = None
        except Exception as exc:  # never take the app down for this
            STATE["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
        print(f"[keepalive] {STATE}", flush=True)
        await asyncio.sleep(minutes * 60)
