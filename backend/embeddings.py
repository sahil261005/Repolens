"""Local embeddings using sentence-transformers + numpy cosine search."""

import os
from pathlib import Path

# keep downloaded model in the project dir instead of cluttering ~/.cache
os.environ.setdefault("HF_HOME", str(Path(__file__).parent / ".cache"))

import numpy as np
from sentence_transformers import SentenceTransformer


# load once at startup - this was really slow when I was loading it per-request
model = SentenceTransformer("all-MiniLM-L6-v2")


def embed_nodes(graph):
    """Embed every graph node in one batch and store vectors on the node data."""
    nodes = list(graph.nodes(data=True))
    if not nodes:
        return graph

    texts = []
    for _, data in nodes:
        text = data.get("text") or data.get("label") or ""
        texts.append(text)

    embeddings = model.encode(texts, convert_to_numpy=True)
    for (node_id, _), embedding in zip(nodes, embeddings):
        graph.nodes[node_id]["embedding"] = np.asarray(embedding)

    return graph


def cosine_similarity(first, second):
    """Basic cosine similarity - no need for a vector DB at this scale."""
    first = np.asarray(first)
    second = np.asarray(second)
    denominator = np.linalg.norm(first) * np.linalg.norm(second)
    if denominator == 0:
        return 0.0
    return float(np.dot(first, second) / denominator)


def vector_search(graph, query, top_k=10):
    if not query or top_k <= 0:
        return []

    query_embedding = model.encode(query, convert_to_numpy=True)
    results = []

    for node_id, data in graph.nodes(data=True):
        embedding = data.get("embedding")
        if embedding is None:
            continue
        score = cosine_similarity(query_embedding, embedding)
        results.append((node_id, score))

    results.sort(key=lambda result: result[1], reverse=True)
    return results[:top_k]
