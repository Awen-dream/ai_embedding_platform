import asyncio
import json
import unittest
from unittest.mock import patch

import httpx

from embedding_platform_common.errors import PlatformError
from embedding_runtime_service.config import EmbeddingRuntimeSettings
from embedding_runtime_service.domain.providers import (
    HashingEmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
    build_embedding_provider,
)


class ProvidersTest(unittest.TestCase):
    def test_build_provider_returns_hashing_provider(self) -> None:
        provider = build_embedding_provider(EmbeddingRuntimeSettings())
        self.assertIsInstance(provider, HashingEmbeddingProvider)

    def test_openai_compatible_provider_parses_embeddings(self) -> None:
        response = httpx.Response(
            200,
            json={
                "data": [
                    {"embedding": [0.1, 0.2]},
                    {"embedding": [0.3, 0.4]},
                ],
                "usage": {"prompt_tokens": 7},
            },
        )

        async def handler(*_args, **_kwargs):
            return response

        with patch("httpx.AsyncClient.post", side_effect=handler):
            provider = OpenAICompatibleEmbeddingProvider(
                base_url="https://example.com/v1",
                api_key="secret",
                path="/embeddings",
                timeout=3.0,
            )
            batch = asyncio.run(
                provider.embed(
                    texts=["hello", "world"],
                    model="text-embedding-3-small",
                    dimension=2,
                    encoding_format="float",
                    metadata={},
                    request_id="req-1",
                    tenant_id="tenant-a",
                )
            )

        self.assertEqual(batch.vectors[0], [0.1, 0.2])
        self.assertEqual(batch.input_tokens, 7)

    def test_openai_compatible_provider_surfaces_downstream_errors(self) -> None:
        response = httpx.Response(500, content=json.dumps({"error": {"message": "provider down"}}))

        async def handler(*_args, **_kwargs):
            return response

        with patch("httpx.AsyncClient.post", side_effect=handler):
            provider = OpenAICompatibleEmbeddingProvider(
                base_url="https://example.com/v1",
                api_key="secret",
                path="/embeddings",
                timeout=3.0,
            )
            with self.assertRaises(PlatformError):
                asyncio.run(
                    provider.embed(
                        texts=["hello"],
                        model="text-embedding-3-small",
                        dimension=2,
                        encoding_format="float",
                        metadata={},
                        request_id="req-1",
                        tenant_id="tenant-a",
                    )
                )
