import unittest

from embedding_runtime_service.domain.encoder import estimate_input_tokens, stable_embedding


class EncoderTest(unittest.TestCase):
    def test_stable_embedding_is_deterministic(self) -> None:
        first = stable_embedding("industrial embedding platform", 8)
        second = stable_embedding("industrial embedding platform", 8)
        self.assertEqual(first, second)

    def test_estimate_input_tokens_has_minimum_one(self) -> None:
        self.assertEqual(estimate_input_tokens("hello world"), 2)
