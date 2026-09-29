"""Real Chroma persistence/filter checks without downloading an embedding model."""

import chromadb
from chromadb.utils.embedding_functions import EmbeddingFunction


class TestEmbeddings(EmbeddingFunction):
    __test__ = False

    def __init__(self):
        pass

    def __call__(self, input):
        return [[1.0, 0.0, 0.0] if "salary" in value else [0.0, 1.0, 0.0] for value in input]


def test_private_vector_query_and_delete(tmp_path):
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    collection = client.create_collection("test-documents", embedding_function=TestEmbeddings())
    collection.upsert(
        ids=["alice", "bob"],
        embeddings=[[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
        metadatas=[{"user_id": "alice"}, {"user_id": "bob"}],
    )
    assert collection.query(query_texts=["salary"], where={"user_id": "alice"}, n_results=2)[
        "ids"
    ] == [["alice"]]
    collection.delete(where={"user_id": "alice"})
    assert collection.get()["ids"] == ["bob"]
