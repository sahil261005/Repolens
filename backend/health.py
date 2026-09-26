"""Repo knowledge health analysis for the Health Layer."""

from collections import Counter

import networkx as nx


def graph_density(graph):
    """Return graph density (edges / possible edges)."""
    if graph.number_of_nodes() < 2:
        return 0.0
    return round(nx.density(graph), 4)


def connected_components(graph):
    """Return the number of isolated knowledge clusters."""
    return list(nx.connected_components(graph))


def fragmentation_score(graph):
    """Score how fragmented the graph is (0 = fully connected, 1 = isolated)."""
    if graph.number_of_nodes() < 2:
        return 0.0
    components = connected_components(graph)
    largest = max(len(c) for c in components)
    isolated = sum(1 for c in components if len(c) == 1)
    return round((1 - largest / graph.number_of_nodes()) + (isolated / graph.number_of_nodes()) * 0.5, 4)


def coverage_stats(graph):
    """Analyze how well commits/issues are linked to discussions."""
    commit_nodes = [n for n, d in graph.nodes(data=True) if d.get("type") == "commit"]
    issue_nodes = [n for n, d in graph.nodes(data=True) if d.get("type") == "issue"]
    pr_nodes = [n for n, d in graph.nodes(data=True) if d.get("type") == "pull_request"]

    commit_refs = 0
    for node_id in commit_nodes:
        for _, _, data in graph.edges(node_id, data=True):
            if data.get("relation") in ("RESOLVES", "MENTIONS"):
                commit_refs += 1
                break

    pr_refs = 0
    for node_id in pr_nodes:
        for _, _, data in graph.edges(node_id, data=True):
            if data.get("relation") in ("RESOLVES", "MENTIONS"):
                pr_refs += 1
                break

    discussion_nodes = len(issue_nodes) + len(pr_nodes)
    coverage = round(commit_refs / len(commit_nodes), 4) if commit_nodes else 0.0
    pr_coverage = round(pr_refs / len(pr_nodes), 4) if pr_nodes else 0.0

    return {
        "commit_issue_coverage": coverage,
        "pr_issue_coverage": pr_coverage,
        "commit_refs": commit_refs,
        "pr_refs": pr_refs,
        "total_commits": len(commit_nodes),
        "total_issues": len(issue_nodes),
        "total_prs": len(pr_nodes),
    }


def freshness_stats(graph):
    """Return the age of the most recent activity in the graph."""
    from datetime import datetime, timezone

    latest = None
    for _, data in graph.nodes(data=True):
        created_at = data.get("created_at")
        if not created_at:
            continue
        try:
            created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if latest is None or created > latest:
                latest = created
        except (TypeError, ValueError):
            continue

    if latest is None:
        return {"age_days": None, "freshness": "unknown"}

    age_days = max(0, (datetime.now(timezone.utc) - latest).days)
    freshness = (
        "very_recent" if age_days <= 7
        else "recent" if age_days <= 30
        else "moderate" if age_days <= 90
        else "stale"
    )
    return {"age_days": age_days, "freshness": freshness}


def coupling_stats(graph):
    """Analyze PR-to-issue coupling (how well PRs link to issues)."""
    pr_nodes = [n for n, d in graph.nodes(data=True) if d.get("type") == "pull_request"]
    resolved = 0
    mentioned = 0
    for node_id in pr_nodes:
        relations = [data.get("relation") for _, _, data in graph.edges(node_id, data=True)]
        if "RESOLVES" in relations:
            resolved += 1
        elif "MENTIONS" in relations:
            mentioned += 1

    return {
        "prs_total": len(pr_nodes),
        "prs_resolved": resolved,
        "prs_mentioned": mentioned,
        "coupling_rate": round(resolved / len(pr_nodes), 4) if pr_nodes else 0.0,
    }


def health_report(graph):
    """Compile the full repo knowledge health report."""
    node_types = Counter(data.get("type", "unknown") for _, data in graph.nodes(data=True))
    component_sizes = [len(c) for c in connected_components(graph)]

    coverage = coverage_stats(graph)
    freshness = freshness_stats(graph)
    coupling = coupling_stats(graph)

    density = graph_density(graph)
    fragmentation = fragmentation_score(graph)

    overall = "healthy"
    if density < 0.05 and graph.number_of_nodes() > 20:
        overall = "fragmented"
    elif density < 0.12:
        overall = "sparse"

    return {
        "overall": overall,
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "node_types": dict(node_types),
        "density": density,
        "fragmentation": fragmentation,
        "largest_component": max(component_sizes) if component_sizes else 0,
        "component_count": len(component_sizes),
        "coverage": coverage,
        "freshness": freshness,
        "coupling": coupling,
        "insights": build_insights(overall, density, fragmentation, coverage, freshness, coupling),
    }


def build_insights(overall, density, fragmentation, coverage, freshness, coupling):
    """Build human-readable health insights."""
    insights = []

    if overall == "fragmented":
        insights.append(
            {
                "severity": "warning",
                "message": "Graph is fragmented — knowledge is split into disconnected clusters.",
                "suggestion": "Encourage PRs/issues to reference related issues to strengthen connectivity.",
            }
        )
    elif overall == "sparse":
        insights.append(
            {
                "severity": "info",
                "message": "Graph is sparse — few relationships between items.",
                "suggestion": "Retrieval may rely heavily on semantic search; graph traversal will be limited.",
            }
        )
    else:
        insights.append(
            {
                "severity": "success",
                "message": "Graph is well-connected — graph traversal can reach most items.",
                "suggestion": "Relational queries should perform well.",
            }
        )

    if coverage.get("commit_issue_coverage", 0) < 0.3:
        insights.append(
            {
                "severity": "warning",
                "message": "Most commits don't reference issues — commit history is disconnected from problem tracking.",
                "suggestion": "Adopt 'Fixes #N' conventions to link commits to issues.",
            }
        )

    if coupling.get("coupling_rate", 0) < 0.5:
        insights.append(
            {
                "severity": "info",
                "message": "Many PRs don't explicitly resolve an issue.",
                "suggestion": "Add 'Fixes #N' references to PR bodies for better traceability.",
            }
        )

    if freshness.get("age_days") is not None and freshness.get("age_days", 999) > 180:
        insights.append(
            {
                "severity": "info",
                "message": "No recent activity — repository knowledge may be outdated.",
                "suggestion": "Expect retrieval to rely on historical context; verify answers against current branches.",
            }
        )

    return insights