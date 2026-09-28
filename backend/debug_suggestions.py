"""Generates debugging suggestions based on retrieval behavior.

Shows things like "your vector scores are low, try adjusting weights"
or "this item was retrieved but contributed nothing to the answer".
"""

import math


def generate_suggestions(trace, results):
    suggestions = []

    if not results:
        return suggestions

    vector_scores = [r.get("vector_score", 0) for r in results]
    graph_scores = [r.get("graph_score", 0) for r in results]
    final_scores = [r.get("final_score", 0) for r in results]

    avg_vector = sum(vector_scores) / len(vector_scores) if vector_scores else 0
    avg_graph = sum(graph_scores) / len(graph_scores) if graph_scores else 0
    avg_final = sum(final_scores) / len(final_scores) if final_scores else 0

    weights = trace.get("weights", {})
    vector_weight = weights.get("vector", 0.8)
    graph_weight = weights.get("graph", 0.2)
    intent = trace.get("intent", "semantic")

    # check if the retrieval mode matches the actual results
    if intent == "relational" and avg_graph < 0.1:
        suggestions.append(
            {
                "type": "graph_weight",
                "message": "Relational query retrieved few graph candidates.",
                "suggestion": f"Increase graph weight from {graph_weight:.2f} to {min(0.9, graph_weight + 0.3):.2f}.",
            }
        )

    if intent == "semantic" and avg_vector < 0.1:
        suggestions.append(
            {
                "type": "vector_weight",
                "message": "Semantic query retrieved few vector candidates.",
                "suggestion": f"Increase vector weight from {vector_weight:.2f} to {min(0.9, vector_weight + 0.3):.2f}.",
            }
        )

    vector_hits = trace.get("vector_hits", [])
    if len(vector_hits) < 3:
        suggestions.append(
            {
                "type": "top_k",
                "message": "Few vector candidates retrieved.",
                "suggestion": "Increase top_k from 10 to 20 for a broader semantic search.",
            }
        )

    if avg_final < 0.1:
        suggestions.append(
            {
                "type": "scoring",
                "message": "Final scores are very low — results may be irrelevant.",
                "suggestion": "Check query clarity or consider expanding context with more repository data.",
            }
        )

    # flag when nothing got high confidence
    used_count = sum(1 for r in results if r.get("confidence") == "high")
    if used_count == 0 and len(results) > 0:
        suggestions.append(
            {
                "type": "overlap",
                "message": "No high-confidence items found.",
                "suggestion": "Answer may not directly quote retrieved text. Try rephrasing the question to match repo terminology.",
            }
        )

    # flag individual dead weight items
    for result in results:
        if result.get("confidence") == "low":
            label = result.get("label", "Item")
            suggestions.append(
                {
                    "type": "dead_weight",
                    "message": f"'{label}' likely contributed little to the answer.",
                    "suggestion": "Consider trimming prompt context or reranking with stricter filters.",
                }
            )

    return suggestions


def analyze_dead_weight(trace):
    """Find items that were retrieved but didn't really contribute."""
    dead_weight = []

    for result in trace.get("final_results", []):
        confidence = result.get("confidence")
        if confidence == "low":
            dead_weight.append(
                {
                    "id": result.get("id"),
                    "label": result.get("label"),
                    "vector_score": result.get("vector_score"),
                    "graph_score": result.get("graph_score"),
                    "reason": "Retrieved but showed low lexical overlap with answer.",
                }
            )

    return dead_weight


def suggest_weight_adjustments(trace, results):
    """Suggest better weight splits based on what the retrieval actually returned."""
    suggestions = []

    vector_hits = trace.get("vector_hits", [])
    graph_hits = trace.get("graph_hits", [])

    vector_diversity = len(vector_hits)
    graph_diversity = len(graph_hits)

    if vector_diversity < graph_diversity * 0.5:
        suggestions.append(
            {
                "type": "weight_split",
                "message": "Vector hits suggest under-exploring semantic space.",
                "suggestion": "Try 60% vector / 40% graph for this query.",
            }
        )
    elif graph_diversity < vector_diversity * 0.5:
        suggestions.append(
            {
                "type": "weight_split",
                "message": "Graph hits suggest limited path discovery.",
                "suggestion": "Try 30% vector / 70% graph for relational questions.",
            }
        )

    return suggestions


def compile_debug_report(trace):
    """Pull all the diagnostic info together into one report for the frontend."""
    suggestions = generate_suggestions(trace, trace.get("final_results", []))
    suggestions.extend(suggest_weight_adjustments(trace, trace.get("final_results", [])))

    dead_weight = analyze_dead_weight(trace)

    return {
        "has_problems": len(suggestions) > 0 or len(dead_weight) > 2,
        "problems_found": len(suggestions),
        "dead_weight_items": dead_weight,
        "suggestions": suggestions[:5],  # cap at 5 to not overwhelm the UI
    }