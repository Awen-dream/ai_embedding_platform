import unittest

from embedding_preprocess_service.domain.chunking import chunk_words, normalize_text


class ChunkingTest(unittest.TestCase):
    def test_normalize_text_collapses_whitespace(self) -> None:
        self.assertEqual(normalize_text("hello   embedding \n platform"), "hello embedding platform")

    def test_chunk_words_generates_overlap(self) -> None:
        chunks = list(chunk_words(["a", "b", "c", "d", "e"], 3, 1))
        self.assertEqual(chunks[0], (0, 3, ["a", "b", "c"]))
        self.assertEqual(chunks[1], (2, 5, ["c", "d", "e"]))

