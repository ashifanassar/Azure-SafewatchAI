from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class RegulationChunk:
    id: str
    source: str
    clause_id: str
    title: str
    content: str
    jurisdiction: str
    document_type: str
    version: str
    tags: list[str]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the SafeWatch regulations vector index.")
    parser.add_argument("--search-endpoint", required=True)
    parser.add_argument("--openai-endpoint", required=True)
    parser.add_argument("--openai-api-key", default=os.getenv("AZURE_OPENAI_API_KEY"))
    parser.add_argument("--embedding-deployment", default="embed-safewatch-v1")
    parser.add_argument("--index-name", default="safewatch-regulations-v1")
    parser.add_argument("--corpus", default="data/regulations/safewatch_regulations.json")
    parser.add_argument("--embedding-dimensions", type=int, default=3072)
    parser.add_argument("--search-api-version", default="2024-07-01")
    parser.add_argument("--openai-api-version", default="2024-02-01")
    args = parser.parse_args()

    credential = build_credential()
    chunks = load_chunks(Path(args.corpus))
    create_or_replace_index(
        credential=credential,
        endpoint=args.search_endpoint,
        index_name=args.index_name,
        dimensions=args.embedding_dimensions,
        api_version=args.search_api_version,
    )
    documents = []
    for chunk in chunks:
        documents.append(
            {
                "@search.action": "upload",
                "id": chunk.id,
                "source": chunk.source,
                "clause_id": chunk.clause_id,
                "title": chunk.title,
                "content": chunk.content,
                "content_vector": embed_text(
                    credential=credential,
                    endpoint=args.openai_endpoint,
                    deployment=args.embedding_deployment,
                    text=chunk.content,
                    api_version=args.openai_api_version,
                    api_key=args.openai_api_key,
                ),
                "jurisdiction": chunk.jurisdiction,
                "document_type": chunk.document_type,
                "index_version": chunk.version,
                "tags": chunk.tags,
            }
        )
    upload_documents(
        credential=credential,
        endpoint=args.search_endpoint,
        index_name=args.index_name,
        documents=documents,
        api_version=args.search_api_version,
    )
    print(f"Uploaded {len(documents)} regulation chunks to {args.index_name}.")


def build_credential():
    from azure.identity import DefaultAzureCredential

    return DefaultAzureCredential()


def load_chunks(corpus_path: Path) -> list[RegulationChunk]:
    records = json.loads(corpus_path.read_text(encoding="utf-8"))
    chunks: list[RegulationChunk] = []
    for record in records:
        for index, content in enumerate(chunk_text(record["text"]), start=1):
            chunk_id = slugify(f"{record['source']}-{record['clause_id']}-{index:03d}")
            chunks.append(
                RegulationChunk(
                    id=chunk_id,
                    source=record["source"],
                    clause_id=record["clause_id"],
                    title=record["title"],
                    content=content,
                    jurisdiction=record["jurisdiction"],
                    document_type=record["document_type"],
                    version=record["version"],
                    tags=[record["source"], record["document_type"], record["jurisdiction"]],
                )
            )
    return chunks


def chunk_text(text: str, target_words: int = 120, overlap_words: int = 25) -> list[str]:
    words = text.split()
    if len(words) <= target_words:
        return [text.strip()]
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(len(words), start + target_words)
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = max(0, end - overlap_words)
    return chunks


def create_or_replace_index(
    credential,
    endpoint: str,
    index_name: str,
    dimensions: int,
    api_version: str,
) -> None:
    payload = {
        "name": index_name,
        "fields": [
            {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
            {"name": "source", "type": "Edm.String", "searchable": True, "filterable": True, "facetable": True},
            {"name": "clause_id", "type": "Edm.String", "searchable": True, "filterable": True},
            {"name": "title", "type": "Edm.String", "searchable": True},
            {"name": "content", "type": "Edm.String", "searchable": True},
            {
                "name": "content_vector",
                "type": "Collection(Edm.Single)",
                "searchable": True,
                "retrievable": False,
                "dimensions": dimensions,
                "vectorSearchProfile": "hnsw-profile",
            },
            {"name": "jurisdiction", "type": "Edm.String", "filterable": True, "facetable": True},
            {"name": "document_type", "type": "Edm.String", "filterable": True, "facetable": True},
            {"name": "index_version", "type": "Edm.String", "filterable": True},
            {"name": "tags", "type": "Collection(Edm.String)", "filterable": True, "facetable": True},
        ],
        "vectorSearch": {
            "algorithms": [
                {
                    "name": "hnsw-config",
                    "kind": "hnsw",
                    "hnswParameters": {
                        "metric": "cosine",
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500,
                    },
                }
            ],
            "profiles": [{"name": "hnsw-profile", "algorithm": "hnsw-config"}],
        },
    }
    put_json(
        credential=credential,
        endpoint=endpoint,
        path=f"/indexes/{quote(index_name, safe='')}",
        payload=payload,
        api_version=api_version,
        scope="https://search.azure.com/.default",
    )


def embed_text(
    credential,
    endpoint: str,
    deployment: str,
    text: str,
    api_version: str,
    api_key: str | None = None,
) -> list[float]:
    body = post_json(
        credential=credential,
        endpoint=endpoint,
        path=f"/openai/deployments/{quote(deployment, safe='')}/embeddings",
        payload={"input": text},
        api_version=api_version,
        scope="https://cognitiveservices.azure.com/.default",
        api_key=api_key,
    )
    return body["data"][0]["embedding"]


def upload_documents(
    credential,
    endpoint: str,
    index_name: str,
    documents: list[dict],
    api_version: str,
) -> None:
    post_json(
        credential=credential,
        endpoint=endpoint,
        path=f"/indexes/{quote(index_name, safe='')}/docs/index",
        payload={"value": documents},
        api_version=api_version,
        scope="https://search.azure.com/.default",
    )


def put_json(credential, endpoint: str, path: str, payload: dict, api_version: str, scope: str) -> dict:
    return request_json("PUT", credential, endpoint, path, payload, api_version, scope)


def post_json(
    credential,
    endpoint: str,
    path: str,
    payload: dict,
    api_version: str,
    scope: str,
    api_key: str | None = None,
) -> dict:
    return request_json("POST", credential, endpoint, path, payload, api_version, scope, api_key=api_key)


def request_json(
    method: str,
    credential,
    endpoint: str,
    path: str,
    payload: dict,
    api_version: str,
    scope: str,
    api_key: str | None = None,
) -> dict:
    url = f"{endpoint.rstrip('/')}{path}?api-version={api_version}"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["api-key"] = api_key
    else:
        token = credential.get_token(scope).token
        headers["Authorization"] = f"Bearer {token}"
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed: {exc.code} {detail}") from exc


def slugify(value: str) -> str:
    cleaned = [character.lower() if character.isalnum() else "-" for character in value]
    return "-".join("".join(cleaned).split("-"))


if __name__ == "__main__":
    main()
