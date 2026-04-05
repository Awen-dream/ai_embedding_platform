import unittest

from embedding_vector_store_proxy.domain.search import cosine_similarity, matches_filters


class VectorSearchTest(unittest.TestCase):
    def test_cosine_similarity_prefers_aligned_vectors(self) -> None:
        self.assertGreater(cosine_similarity([1.0, 0.0], [1.0, 0.0]), cosine_similarity([1.0, 0.0], [0.0, 1.0]))

    def test_matches_filters_requires_exact_match(self) -> None:
        self.assertTrue(matches_filters({"scene": "rag"}, {"scene": "rag"}))
        self.assertFalse(matches_filters({"scene": "search"}, {"scene": "rag"}))

