
# RepoLens

RepoLens is a retrieval-intelligence workbench for public GitHub repositories. It shows not only what a hybrid retriever found, but how vector search, graph traversal, recency, and answer-overlap signals shaped the final evidence set.

The central question is deliberately practical: **of the items retrieved for an answer, which appear to have made it into that answer—and which were dead weight?**

## What it demonstrates

- Public GitHub ingestion for recent pull requests, issues, and commits
- A weighted knowledge graph linking people, PRs, issues, and commits
- Local `all-MiniLM-L6-v2` semantic embeddings and NumPy cosine search
- Intent-aware hybrid retrieval: semantic queries prefer vectors, relationship questions prefer graph paths
- Path provenance, per-arm scores, recency decay, and retrieval funnel telemetry
- Interactive lexical token overlap highlighting linking answers directly to evidence
- Context bloat & dead-weight token cost quantification
- Interactive client-side "What-If" fusion slider for instantaneous weight tuning
- Radial traversal graph canvas with bidirectional node selection
- Repository knowledge health diagnostics (density, fragmentation, coupling)
- Retrieval diagnostics: dead-weight detection, low-signal queries, and actionable tuning suggestions
- Evidence confidence tiers (high / medium / low / unknown) replacing a binary used/not-used label
- SQLite-backed query history and a side-by-side experiment lab


## Architecture

```text
GitHub API → typed repository graph → local embeddings
                                    ↓
Question → intent router → vector search + weighted graph traversal
                                    ↓
                  fusion + recency → answer context → Groq answer
                                    ↓
                     overlap analysis + trace + saved query run
```

### Why hybrid retrieval?

Vector search finds semantically similar text, but it can miss exact engineering relationships—such as who authored the PR that resolved an issue. Graph traversal exposes those relationships, but it can wander without semantic seeds. RepoLens starts from vector hits, traverses the weighted graph, then fuses both signals.

| Relation | Weight | Reason |
| --- | ---: | --- |
| `AUTHORED` | 0.95 | Direct GitHub authorship fact |
| `RESOLVES` | 0.90 | Explicit `Fixes #N` / `Closes #N` reference |
| `REPORTED` | 0.75 | Issue authorship is useful context |
| `MENTIONS` | 0.70 | A bare issue reference is weaker evidence |

Relational questions use 20% vector / 80% graph scoring. Semantic questions use 80% vector / 20% graph scoring. Fresh evidence receives a small boost through type-specific recency decay, while missing dates are never penalized.

## Overlap analysis: useful, but not causal

RepoLens tokenizes each answer and retrieved item, removes a small stopword set, and calculates shared-token overlap normalized by the smaller token set. Each retrieved item is then assigned an evidence confidence band:

- **High** (overlap ≥ 0.5) — item text appears directly in the answer
- **Medium** (overlap ≥ 0.2) — some shared tokens, likely relevant
- **Low** (overlap < 0.2) — retrieved but barely referenced (dead weight)
- **Unknown** — answer was not generated or overlap could not be computed

This is a lexical proxy—not causal attribution. It cannot reliably detect paraphrases, evidence used as a negative constraint, or facts that influenced reasoning without appearing in the final wording. If answer generation fails, RepoLens marks all overlap statuses as unknown rather than pretending nothing was used.

## Local setup

Requirements: Python 3.11+, Node 20+, and a free Groq API key. A GitHub token is optional but strongly recommended to avoid public rate limits.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload
```

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Tests and verification

```bash
cd backend
.venv/bin/python -m unittest discover tests

cd ../frontend
npm run build
```

GitHub Actions repeats the backend unit tests and frontend production build on every push and pull request.

## Lessons learned

- **Vector search alone doesn't answer relationship questions.** Early on, I tried pure semantic search, but queries like "who authored the login fix?" returned random text that happened to mention logins. Adding the graph traversal arm and fusing both signals fixed this — relational queries now surface authorship paths instead of keyword matches.
- **Overlap is lexical, not causal — and that's intentional.** I considered using the LLM to judge whether each item "influenced" the answer, but that would be slow, expensive, and just as unreliable. Simple shared-token overlap is transparent: you can see exactly why an item was flagged as used or dead weight. The limitation is clearly stated in the UI.
- **Recency decay needs a floor.** My first version used pure exponential decay, which made anything older than a few months basically invisible. Adding a `0.35` floor means old items are deprioritised but not erased — useful when someone asks about historical decisions.
- **Client-side reranking was a happy accident.** I originally built the weight slider to re-query the server on every change, but it was too slow. Sending all the per-arm scores to the frontend and recomputing the fusion client-side made the slider feel instant. The tradeoff is that the graph traversal seeds don't change (those are fixed at query time), but for exploring weight sensitivity it works well enough.

## Known limitations

- Public repositories only; the app reads the latest 30 PRs, 30 issues, and 50 commits rather than full history.
- Graphs and embeddings remain in memory and are lost on backend restart. SQLite persists analysis summaries and query experiments, not the graph itself.
- The app uses free-tier GitHub and Groq APIs. GitHub limits anonymous access; free deployments may cold-start.
- The overlap metric is lexical, not a measure of causal evidence use.



