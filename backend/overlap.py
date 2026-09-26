"""Lexical overlap analysis and confidence scoring for retrieved items and answers."""

import re

from llm import ANSWER_FAILURE


STOPWORDS = {
    "and",
    "are",
    "but",
    "for",
    "from",
    "has",
    "have",
    "into",
    "its",
    "not",
    "only",
    "our",
    "that",
    "the",
    "their",
    "then",
    "there",
    "these",
    "this",
    "those",
    "was",
    "were",
    "with",
    "you",
}
OVERLAP_THRESHOLD = 0.2
HIGH_CONFIDENCE_THRESHOLD = 0.5
MEDIUM_CONFIDENCE_THRESHOLD = 0.2


def tokens(text):
    """Return meaningful lowercase tokens for a simple lexical comparison."""
    words = re.split(r"[^a-z0-9]+", (text or "").lower())
    return {word for word in words if len(word) > 2 and word not in STOPWORDS}


def answer_overlap(item_text, answer_text):
    """Return shared-token fraction, normalised by the smaller token set."""
    answer_tokens = tokens(answer_text)
    item_tokens = tokens(item_text)
    if not answer_tokens or not item_tokens:
        return None
    return round(
        len(answer_tokens & item_tokens) / min(len(answer_tokens), len(item_tokens)),
        3,
    )


def confidence_level(overlap):
    """Map a lexical overlap score to a human-readable confidence band.

    High:   overlap >= 0.5  — item text appears directly in the answer
    Medium: overlap >= 0.2  — some shared tokens, likely relevant
    Low:    overlap < 0.2   — retrieved but barely referenced
    Unknown: answer was not generated or overlap could not be computed
    """
    if overlap is None:
        return "unknown"
    if overlap >= HIGH_CONFIDENCE_THRESHOLD:
        return "high"
    if overlap >= MEDIUM_CONFIDENCE_THRESHOLD:
        return "medium"
    return "low"


def estimate_tokens(text):
    """Rough token count estimation (~1.3 tokens per whitespace-separated word)."""
    if not text:
        return 0
    words = len(text.split())
    return max(1, int(words * 1.3))


def add_overlap_analysis(trace, answer):
    """Annotate final results with shared tokens, confidence bands, and token metrics.

    This is a lexical signal, not proof that an item caused the model's answer.
    """
    results = trace.get("final_results", [])
    answer_generated = bool(answer) and answer != ANSWER_FAILURE
    ans_tokens = tokens(answer) if answer_generated else set()

    used_count = 0
    high_count = 0
    medium_count = 0
    low_count = 0
    unknown_count = 0

    total_context_tokens = 0
    used_tokens = 0
    dead_weight_tokens = 0

    for item in results:
        text = item.get("text", "")
        item_toks = tokens(text)
        item_token_est = estimate_tokens(text)
        item["token_estimate"] = item_token_est
        total_context_tokens += item_token_est

        if not answer_generated:
            item["answer_overlap"] = None
            item["shared_tokens"] = []
            item["used"] = None
            item["confidence"] = "unknown"
            unknown_count += 1
            continue

        overlap = answer_overlap(text, answer)
        item["answer_overlap"] = overlap
        shared = sorted(list(ans_tokens & item_toks))
        item["shared_tokens"] = shared
        confidence = confidence_level(overlap)
        item["confidence"] = confidence
        is_used = overlap >= OVERLAP_THRESHOLD if overlap is not None else None
        item["used"] = is_used

        if is_used:
            used_count += 1
            used_tokens += item_token_est
        else:
            dead_weight_tokens += item_token_est

        if confidence == "high":
            high_count += 1
        elif confidence == "medium":
            medium_count += 1
        elif confidence == "low":
            low_count += 1
        else:
            unknown_count += 1

    retrieved_count = len(results)
    trace["overlap_summary"] = {
        "retrieved": retrieved_count,
        "used": used_count,
        "high": high_count,
        "medium": medium_count,
        "low": low_count,
        "unknown": unknown_count,
        "efficiency": round(used_count / retrieved_count, 3)
        if answer_generated and retrieved_count
        else None,
        "total_tokens": total_context_tokens,
        "used_tokens": used_tokens,
        "dead_weight_tokens": dead_weight_tokens,
        "wasted_token_pct": round((dead_weight_tokens / total_context_tokens) * 100)
        if total_context_tokens > 0 and answer_generated
        else 0,
    }
    return trace

