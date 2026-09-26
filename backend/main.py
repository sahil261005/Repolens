import os
import time
from collections import OrderedDict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from debug_suggestions import compile_debug_report
from embeddings import embed_nodes
from github_client import fetch_repo_data, parse_repo_url
from graph_builder import build_graph, graph_stats
from health import health_report
from llm import generate_answer
from overlap import add_overlap_analysis
from retrieval import hybrid_search
from storage import recent_analyses, recent_runs, save_analysis, save_query_run, setup_database


load_dotenv()
limiter = Limiter(key_func=get_remote_address)
repo_cache = OrderedDict()
MAX_CACHED_REPOS = 5


app = FastAPI(title="RepoLens")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

frontend_url = os.getenv("FRONTEND_URL")
cors_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
]
if frontend_url:
    cors_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def start_application():
    setup_database()


class AnalyzeRequest(BaseModel):
    repo_url: str


class QueryRequest(BaseModel):
    repo: str
    query: str
    vector_weight: float | None = None



class SubgraphRequest(BaseModel):
    repo: str
    node_ids: list[str]


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


def cache_graph(repo, graph):
    repo_cache[repo] = graph
    repo_cache.move_to_end(repo)
    if len(repo_cache) > MAX_CACHED_REPOS:
        repo_cache.popitem(last=False)


def cached_graph(repo):
    graph = repo_cache.get(repo)
    if graph is None:
        raise HTTPException(
            status_code=404,
            detail="Repository is not analyzed yet. Analyze it before asking a question.",
        )
    repo_cache.move_to_end(repo)
    return graph


@app.post("/api/analyze")
@limiter.limit("5/hour")
def analyze_repository(request: Request, payload: AnalyzeRequest):
    started_at = time.perf_counter()
    try:
        owner, name = parse_repo_url(payload.repo_url)
        repo_data = fetch_repo_data(owner, name, os.getenv("GITHUB_TOKEN"))
        graph = build_graph(repo_data)
        embed_nodes(graph)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    repo = f"{owner}/{name}"
    cache_graph(repo, graph)
    stats = graph_stats(graph)
    stats["indexing_ms"] = round((time.perf_counter() - started_at) * 1000)
    
    # Generate health report
    health = health_report(graph)
    
    save_analysis(repo, stats)
    return {"repo": repo, "stats": stats, "health": health}


@app.post("/api/query")
@limiter.limit("20/hour")
def query_repository(request: Request, payload: QueryRequest):
    started_at = time.perf_counter()
    graph = cached_graph(payload.repo)
    results, trace = hybrid_search(graph, payload.query, custom_vector_weight=payload.vector_weight)
    answer = generate_answer(payload.query, results)

    add_overlap_analysis(trace, answer)
    latency_ms = round((time.perf_counter() - started_at) * 1000)
    trace["timing"] = {"total_ms": latency_ms}
    trace["funnel"] = {
        "repository_nodes": graph.number_of_nodes(),
        "vector_candidates": len(trace["vector_hits"]),
        "graph_candidates": len(trace["graph_hits"]),
        "final_context": len(trace["final_results"]),
        "used_evidence": trace["overlap_summary"]["used"],
    }
    trace["debug"] = compile_debug_report(trace)
    run_id = save_query_run(payload.repo, payload.query, answer, trace, latency_ms)
    return {"run_id": run_id, "answer": answer, "trace": trace}


@app.get("/api/history")
def get_history(repo: str | None = None):
    return {"runs": recent_runs(repo), "analyses": recent_analyses()}


@app.get("/api/repo-health")
def get_repo_health(repo: str):
    """Return the knowledge health report for an analyzed repository."""
    graph = cached_graph(repo)
    return {"repo": repo, "health": health_report(graph)}


@app.post("/api/subgraph")
def get_subgraph(payload: SubgraphRequest):
    graph = cached_graph(payload.repo)
    visible_nodes = set()

    for node_id in payload.node_ids:
        if node_id in graph:
            visible_nodes.add(node_id)
            visible_nodes.update(graph.neighbors(node_id))

    nodes = [
        {
            "id": node_id,
            "data": {
                "label": graph.nodes[node_id].get("label", node_id),
                "type": graph.nodes[node_id].get("type", "unknown"),
            },
            "position": {"x": 0, "y": 0},
        }
        for node_id in visible_nodes
    ]
    edges = []
    for source, target, data in graph.edges(data=True):
        if source in visible_nodes and target in visible_nodes:
            edges.append(
                {
                    "id": f"{source}-{target}",
                    "source": source,
                    "target": target,
                    "label": data.get("relation", ""),
                    "data": {"weight": data.get("weight", 0)},
                }
            )

    return {"nodes": nodes, "edges": edges}
