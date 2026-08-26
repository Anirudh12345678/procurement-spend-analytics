import json
from typing import Protocol

import httpx


class LLMProviderError(RuntimeError):
    """Safe provider exception without secret-bearing request details."""


class RecommendationLLM(Protocol):
    model_name: str

    def generate(self, *, system_prompt: str, context_json: str, schema: dict) -> dict:
        """Return one JSON object matching the supplied schema."""


class OpenAIResponsesClient:
    """Minimal server-side OpenAI Responses API structured-output client."""

    def __init__(self, *, api_key: str, model: str, timeout_seconds: float):
        self.api_key = api_key
        self.model_name = model
        self.timeout_seconds = timeout_seconds

    @classmethod
    def _strict_schema(cls, value: object) -> object:
        """Convert Pydantic JSON Schema to the strict subset accepted by Responses."""
        if isinstance(value, list):
            return [cls._strict_schema(item) for item in value]
        if not isinstance(value, dict):
            return value
        unsupported = {
            "default",
            "maximum",
            "maxItems",
            "maxLength",
            "minimum",
            "minItems",
            "minLength",
            "pattern",
            "title",
        }
        result = {
            key: cls._strict_schema(item)
            for key, item in value.items()
            if key not in unsupported
        }
        if result.get("type") == "object" and isinstance(result.get("properties"), dict):
            result["additionalProperties"] = False
            result["required"] = list(result["properties"])
        return result

    def generate(self, *, system_prompt: str, context_json: str, schema: dict) -> dict:
        payload = {
            "model": self.model_name,
            "store": False,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "Generate one recommendation from this verified context:\n"
                            + context_json,
                        }
                    ],
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "procurement_recommendation",
                    "schema": self._strict_schema(schema),
                    "strict": True,
                }
            },
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(
                    "https://api.openai.com/v1/responses",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise LLMProviderError("OpenAI request timed out") from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError("OpenAI request failed") from exc

        if response.status_code == 429:
            raise LLMProviderError("OpenAI rate limit reached")
        if response.status_code >= 400:
            raise LLMProviderError(f"OpenAI returned HTTP {response.status_code}")

        try:
            body = response.json()
            for output in body.get("output", []):
                for content in output.get("content", []):
                    if content.get("type") == "output_text":
                        return json.loads(content["text"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise LLMProviderError("OpenAI returned malformed structured output") from exc
        raise LLMProviderError("OpenAI response did not contain structured output")
