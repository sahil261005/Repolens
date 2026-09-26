"""Small Groq calls for query intent and retrieval-grounded answers."""

import os

from groq import Groq


DEFAULT_MODELS = [
    os.getenv("GROQ_MODEL"),
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-20b",
    "llama-3.1-8b-instant",
]
MODEL_NAMES = [m for m in DEFAULT_MODELS if m]

RELATIONAL_KEYWORDS = [
    "who",
    "which pr",
    "which issue",
    "authored",
    "caused by",
    "related to",
]
SEMANTIC_KEYWORDS = ["how does", "explain", "what is", "why"]
ANSWER_FAILURE = "The answer couldn't be generated. The retrieval results are still available."


def get_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key, timeout=6.0)


def classify_intent(query):
    """Return an intent and the source that made that routing decision."""
    query_lower = query.lower()

    if any(keyword in query_lower for keyword in RELATIONAL_KEYWORDS):
        return "relational", "keyword"
    if any(keyword in query_lower for keyword in SEMANTIC_KEYWORDS):
        return "semantic", "keyword"

    client = get_client()
    if not client:
        return "semantic", "default"

    prompt = (
        "Classify this GitHub repository question as relational or "
        "semantic. Reply with one word only.\n\n"
        f"Question: {query}"
    )
    for model_name in MODEL_NAMES:
        try:
            response = client.chat.completions.create(
                model=model_name,
                temperature=0,
                max_completion_tokens=5,
                messages=[{"role": "user", "content": prompt}],
            )
            intent = response.choices[0].message.content.strip().lower()
            if "relational" in intent:
                return "relational", "llm"
            if "semantic" in intent:
                return "semantic", "llm"
        except Exception:
            continue

    return "semantic", "default"


def generate_answer(query, results):
    """Generate a concise answer that relies only on the retrieved evidence."""
    client = get_client()
    if not client:
        return ANSWER_FAILURE

    context_parts = []
    for item in results[:5]:
        label = item.get("label", "Retrieved item")
        text = item.get("text", "")
        context_parts.append(f"{label}\n{text}")
    context = "\n\n---\n\n".join(context_parts)

    prompt = (
        "Answer the question using only the provided repository context. "
        "Write 2–4 sentences. Name specific PRs, issues, or people "
        "where possible. Say plainly when the context does not contain "
        "the answer.\n\n"
        f"Question: {query}\n\nContext:\n{context}"
    )

    for model_name in MODEL_NAMES:
        try:
            response = client.chat.completions.create(
                model=model_name,
                temperature=0.2,
                max_completion_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            answer = response.choices[0].message.content.strip()
            if answer:
                return answer
        except Exception:
            continue

    return ANSWER_FAILURE
