import unittest

from embedding_retrieval_service.domain.validation import has_query_or_vector


class RetrievalValidationTest(unittest.TestCase):
    def test_has_query_or_vector_accepts_query(self) -> None:
        self.assertTrue(has_query_or_vector("hello", None))

    def test_has_query_or_vector_rejects_empty_request(self) -> None:
        self.assertFalse(has_query_or_vector("", None))

