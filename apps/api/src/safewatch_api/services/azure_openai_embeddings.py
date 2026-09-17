from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


class AzureOpenAIEmbeddingClient:
    def __init__(
        self,
        endpoint: str,
        deployment: str,
        api_version: str = "2024-02-01",
        api_key: str | None = None,
    ) -> None:
        from azure.identity import DefaultAzureCredential

        self.endpoint = endpoint.rstrip("/")
        self.deployment = deployment
        self.api_version = api_version
        self.api_key = api_key
        self.credential = None if api_key else DefaultAzureCredential()

    def embed(self, text: str) -> list[float]:
        deployment = quote(self.deployment, safe="")
        url = f"{self.endpoint}/openai/deployments/{deployment}/embeddings?api-version={self.api_version}"
        payload = json.dumps({"input": text}).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["api-key"] = self.api_key
        else:
            if self.credential is None:
                raise RuntimeError("Azure OpenAI credential was not configured")
            token = self.credential.get_token("https://cognitiveservices.azure.com/.default").token
            headers["Authorization"] = f"Bearer {token}"
        request = Request(
            url,
            data=payload,
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Azure OpenAI embedding request failed: {exc.code} {detail}") from exc
        return body["data"][0]["embedding"]
