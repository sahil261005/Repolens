"""Graph traversal used by the hybrid retriever."""

import heapq
from datetime import datetime, timezone

from llm import classify_intent


MAX_NEIGHBOURS_PER_RELATION = 10
HALF_LIVES = {
    "issue": 21,
    "commit": 45,
    "pull_request": 60,
    "person": 180,
}


def grouped_neighbours(graph, node_id):
    """Group neighbouring nodes by edge relation for relation-level throttling."""
    groups = {}

    for neighbour_id, edge in graph[node_id].items():
        relation = edge.get("relation", "unknown")
        groups.setdefault(relation, []).append((neighbour_id, edge))

    for relation in groups:
        groups[relation].sort(key=lambda item: item[0])

    return groups


def graph_search(graph, seed_node_ids, max_hops=2):
    """Walk from seed nodes, scoring each path by its edge-weight product.

    A priority queue makes sure the best known path is expanded first. The
    returned path includes the seed and the resulting node so the UI can draw
    exactly what the traversal followed.
    """
    if max_hops < 0:
        return []

    best_scores = {}
    best_paths = {}
    queue = []

    for node_id in seed_node_ids:
        if node_id not in graph or node_id in best_scores:
            continue
        best_scores[node_id] = 1.0
        best_paths[node_id] = [node_id]
        heapq.heappush(queue, (-1.0, 0, node_id, [node_id]))

    while queue:
        negative_score, hops, node_id, path = heapq.heappop(queue)
        score = -negative_score

        if score < best_scores[node_id]:
            continue
        if hops == max_hops:
            continue

        for neighbours in grouped_neighbours(graph, node_id).values():
            for neighbour_id, edge in neighbours[:MAX_NEIGHBOURS_PER_RELATION]:
                if neighbour_id in path:
                    continue

                edge_weight = edge.get("weight", 0.0)
                next_score = score * edge_weight
                if next_score <= best_scores.get(neighbour_id, 0.0):
                    continue

                next_path = path + [neighbour_id]
                best_scores[neighbour_id] = next_score
                best_paths[neighbour_id] = next_path
                heapq.heappush(
                    queue,
                    (-next_score, hops + 1, neighbour_id, next_path),
                )

    results = [
        (node_id, score, best_paths[node_id]) for node_id, score in best_scores.items()
    ]
    results.sort(key=lambda result: result[1], reverse=True)
    return results


def recency_details(node):
    """Return an age and decay factor, without penalising missing dates."""
    created_at = node.get("created_at")
    if not created_at:
        return None, 1.0

    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        age_days = max(0, (datetime.now(timezone.utc) - created).days)
    except (TypeError, ValueError):
        return None, 1.0

    half_life = HALF_LIVES.get(node.get("type"))
    if not half_life:
        return age_days, 1.0

    factor = 0.5 ** (age_days / half_life)
    return age_days, max(factor, 0.35)


def hybrid_search(graph, query, top_k=10, custom_vector_weight=None):
    """Fuse vector and graph retrieval with query-intent-dependent weights."""
    from embeddings import vector_search

    if custom_vector_weight is not None:
        v_weight = max(0.0, min(1.0, float(custom_vector_weight)))
        weights = {"vector": round(v_weight, 2), "graph": round(1.0 - v_weight, 2)}
        intent = "relational" if v_weight < 0.5 else "semantic"
        intent_source = "custom_weight"
    else:
        intent, intent_source = classify_intent(query)
        if intent == "relational":
            weights = {"vector": 0.2, "graph": 0.8}
        else:
            weights = {"vector": 0.8, "graph": 0.2}

    vector_results = vector_search(graph, query, top_k=top_k)
    seed_count = 8 if (custom_vector_weight is not None and custom_vector_weight < 0.5) else 5
    graph_results = graph_search(
        graph,
        [node_id for node_id, _ in vector_results[:seed_count]],
    )
    vector_scores = dict(vector_results)
    graph_scores = {node_id: score for node_id, score, _ in graph_results}


    final_results = []
    for node_id in set(vector_scores) | set(graph_scores):
        node = graph.nodes[node_id]
        vector_score = vector_scores.get(node_id, 0.0)
        graph_score = graph_scores.get(node_id, 0.0)
        age_days, recency_factor = recency_details(node)
        final_score = (
            weights["vector"] * vector_score + weights["graph"] * graph_score
        ) * recency_factor
        final_results.append(
            {
                "id": node_id,
                "label": node.get("label", node_id),
                "type": node.get("type", "unknown"),
                "url": node.get("url", ""),
                "text": node.get("text", ""),
                "vector_score": vector_score,
                "graph_score": graph_score,
                "recency_factor": recency_factor,
                "age_days": age_days,
                "final_score": final_score,
            }
        )

    final_results.sort(key=lambda result: result["final_score"], reverse=True)
    final_results = final_results[:top_k]

    return final_results, {
        "query": query,
        "intent": intent,
        "intent_source": intent_source,
        "weights": weights,
        "vector_hits": [
            {
                "id": node_id,
                "label": graph.nodes[node_id].get("label", node_id),
                "score": score,
            }
            for node_id, score in vector_results
        ],
        "graph_hits": [
            {
                "id": node_id,
                "label": graph.nodes[node_id].get("label", node_id),
                "score": score,
                "path": path,
            }
            for node_id, score, path in graph_results
        ],
        "final_results": final_results,
    }
