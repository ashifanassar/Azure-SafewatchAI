from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class VisionAnalysis:
    text: str
    confidence: float
    raw: dict


class AzureVisionImageAnalyzer:
    def __init__(
        self,
        endpoint: str,
        api_version: str = "2024-02-01",
        api_key: str | None = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.api_version = api_version
        self.api_key = api_key
        self.credential = None
        if not api_key:
            from azure.identity import DefaultAzureCredential

            self.credential = DefaultAzureCredential()

    def analyze(self, image_bytes: bytes) -> VisionAnalysis:
        body = self._analyze_with_feature_fallbacks(image_bytes)

        return VisionAnalysis(
            text=analysis_text(body),
            confidence=analysis_confidence(body),
            raw=body,
        )

    def _analyze_with_feature_fallbacks(self, image_bytes: bytes) -> dict:
        feature_sets = [
            "caption,denseCaptions,tags,objects,read,people",
            "tags,objects,read,people",
            "tags,objects,read",
            "tags,read",
        ]
        last_error: RuntimeError | None = None
        for features in feature_sets:
            try:
                return self._post_analysis(image_bytes, features)
            except RuntimeError as exc:
                last_error = exc
                if not is_unsupported_region_feature_error(str(exc)):
                    raise
        if last_error:
            raise last_error
        raise RuntimeError("Azure Vision analysis request failed before a request was sent")

    def _post_analysis(self, image_bytes: bytes, features: str) -> dict:
        query = urlencode(
            {
                "overload": "stream",
                "features": features,
                "language": "en",
                "gender-neutral-caption": "true",
                "api-version": self.api_version,
            }
        )
        url = f"{self.endpoint}/computervision/imageanalysis:analyze?{query}"
        headers = {"Content-Type": "application/octet-stream"}
        if self.api_key:
            headers["Ocp-Apim-Subscription-Key"] = self.api_key
        else:
            if self.credential is None:
                raise RuntimeError("Azure Vision credential was not configured")
            token = self.credential.get_token("https://cognitiveservices.azure.com/.default").token
            headers["Authorization"] = f"Bearer {token}"

        request = Request(url, data=image_bytes, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Azure Vision analysis request failed: {exc.code} {detail}") from exc


def analysis_text(body: dict) -> str:
    parts: list[str] = []
    caption = body.get("captionResult") or {}
    if caption.get("text"):
        parts.append(caption["text"])

    for value in (body.get("denseCaptionsResult") or {}).get("values", []):
        if value.get("text"):
            parts.append(value["text"])

    for value in (body.get("tagsResult") or {}).get("values", []):
        if value.get("name"):
            parts.append(value["name"])

    for value in (body.get("objectsResult") or {}).get("values", []):
        for tag in value.get("tags", []):
            if tag.get("name"):
                parts.append(tag["name"])

    for block in (body.get("readResult") or {}).get("blocks", []):
        for line in block.get("lines", []):
            if line.get("text"):
                parts.append(line["text"])

    return " ".join(parts)


def analysis_confidence(body: dict) -> float:
    scores: list[float] = []
    caption = body.get("captionResult") or {}
    if isinstance(caption.get("confidence"), int | float):
        scores.append(float(caption["confidence"]))

    for section in ("denseCaptionsResult", "tagsResult", "peopleResult"):
        for value in (body.get(section) or {}).get("values", []):
            if isinstance(value.get("confidence"), int | float):
                scores.append(float(value["confidence"]))

    for value in (body.get("objectsResult") or {}).get("values", []):
        for tag in value.get("tags", []):
            if isinstance(tag.get("confidence"), int | float):
                scores.append(float(tag["confidence"]))

    return round(max(scores), 4) if scores else 0.0


def is_unsupported_region_feature_error(message: str) -> bool:
    lowered = message.lower()
    return "not supported in this region" in lowered and "feature" in lowered
