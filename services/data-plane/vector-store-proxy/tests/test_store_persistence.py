import tempfile
import unittest

from embedding_vector_store_proxy.models import VectorItem
from embedding_vector_store_proxy.store import SqliteVectorStore


class SqliteVectorStoreTest(unittest.TestCase):
    def test_sqlite_store_persists_vectors_between_instances(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = f"{temp_dir}/vectors.db"
            store = SqliteVectorStore(path=path)
            store.upsert(
                "tenant-a",
                "demo-index",
                [
                    VectorItem(
                        id="doc-1",
                        vector=[1.0, 0.0],
                        metadata={"scene": "rag"},
                    )
                ],
            )

            reloaded = SqliteVectorStore(path=path)
            dimension, hits = reloaded.search(
                "tenant-a",
                "demo-index",
                [1.0, 0.0],
                3,
                {"scene": "rag"},
            )

            self.assertEqual(dimension, 2)
            self.assertEqual(hits[0].id, "doc-1")
