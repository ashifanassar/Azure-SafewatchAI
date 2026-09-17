from __future__ import annotations

import json
from typing import Protocol
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from safewatch_contracts.models import RegulationCitation


class EmbeddingClient(Protocol):
    def embed(self, text: str) -> list[float]:
        ...


class AzureRegulationSearchClient:
    def __init__(
        self,
        endpoint: str,
        index_name: str,
        embedding_client: EmbeddingClient,
        index_version: str,
        api_version: str = "2024-07-01",
    ) -> None:
        from azure.identity import DefaultAzureCredential

        self.endpoint = endpoint.rstrip("/")
        self.index_name = index_name
        self.embedding_client = embedding_client
        self.index_version = index_version
        self.api_version = api_version
        self.credential = DefaultAzureCredential()

    def search(self, query: str, top: int = 5) -> list[RegulationCitation]:
        query_vector = self.embedding_client.embed(query)
        payload = {
            "search": query,
            "top": top,
            "select": "id,source,clause_id,title,content,index_version",
            "vectorQueries": [
                {
                    "kind": "vector",
                    "vector": query_vector,
                    "fields": "content_vector",
                    "k": 50,
                }
            ],
        }
        body = self._post_json(
            f"/indexes/{quote(self.index_name, safe='')}/docs/search",
            payload,
        )
        citations: list[RegulationCitation] = []
        for item in body.get("value", []):
            content = item.get("content", "")
            citations.append(
                RegulationCitation(
                    source=item["source"],
                    clause_id=item["clause_id"],
                    title=item["title"],
                    excerpt=content[:1200],
                    relevance_score=score_to_relevance(item.get("@search.score", 0.0)),
                    index_version=item.get("index_version") or self.index_version,
                )
            )
        return citations

    def _post_json(self, path: str, payload: dict) -> dict:
        token = self.credential.get_token("https://search.azure.com/.default").token
        url = f"{self.endpoint}{path}?api-version={self.api_version}"
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Azure AI Search request failed: {exc.code} {detail}") from exc


def score_to_relevance(score: float) -> float:
    if score <= 0:
        return 0.0
    return round(min(1.0, score / (score + 1.0)), 4)
