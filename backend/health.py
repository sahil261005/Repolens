"""Health diagnostics for the repository's knowledge graph."""

from collections import Counter

import networkx as nx


def graph_density(graph):
    if graph.number_of_nodes() < 2:
        return 0.0
    return round(nx.density(graph), 4)


def connected_components(graph):
    return list(nx.connected_components(graph))


def fragmentation_score(graph):
    """0 = everything connected, 1 = completely isolated nodes.

    Combines two signals: how dominant the largest component is,
    and how many completely isolated nodes there are.
    """
    if graph.number_of_nodes() < 2:
        return 0.0
    components = connected_components(graph)
    largest = max(len(c) for c in components)
    isolated = sum(1 for c in components if len(c) == 1)
    return round((1 - largest / graph.number_of_nodes()) + (isolated / graph.number_of_nodes()) * 0.5, 4)


def coverage_stats(graph):
    """Check how well commits and PRs are linked to issues."""
    commit_nodes = [n for n, d in graph.nodes(data=True) if d.get("type") == "commit"]
    issue_nodes = [n for n, d in graph.nodes(data=True) if d.get("type") == "issue"]
    pr_nodes = [n for n, d in graph.nodes(data=True) if d.get("type") == "pull_request"]

    # count how many commits reference at least one issue
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
    """How recent is the latest activity in the graph."""
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
    if age_days <= 7:
        freshness = "very_recent"
    elif age_days <= 30:
        freshness = "recent"
    elif age_days <= 90:
        freshness = "moderate"
    else:
        freshness = "stale"

    return {"age_days": age_days, "freshness": freshness}


def coupling_stats(graph):
    """How well PRs link to issues (via Fixes/Closes/Mentions)."""
    pr_nodes = [n for n, d in graph.nodes(data=True) if d.get("type") == "pull_request"]
    resolved = 0
    mentioned = 0
    orphan = 0

    for node_id in pr_nodes:
        has_resolve = False
        has_mention = False
        for _, _, data in graph.edges(node_id, data=True):
            rel = data.get("relation")
            if rel == "RESOLVES":
                has_resolve = True
            elif rel == "MENTIONS":
                has_mention = True

        if has_resolve:
            resolved += 1
        elif has_mention:
            mentioned += 1
        else:
            orphan += 1

    total = len(pr_nodes) or 1
    return {
        "total_prs": len(pr_nodes),
        "resolves_count": resolved,
        "mentions_count": mentioned,
        "orphan_count": orphan,
        "coupling_ratio": round((resolved + mentioned) / total, 4),
    }


def health_report(graph):
    """Put together a full health report for the frontend."""
    density = graph_density(graph)
    frag = fragmentation_score(graph)
    components = connected_components(graph)
    coverage = coverage_stats(graph)
    freshness = freshness_stats(graph)
    coupling = coupling_stats(graph)

    # generate actionable insights based on the metrics
    insights = []

    if density < 0.05:
        insights.append({
            "severity": "warning",
            "message": "Very sparse graph",
            "suggestion": "The repository may have few cross-references between PRs and issues. "
                         "Consider linking PRs to issues with 'Fixes #N' or 'Closes #N'.",
        })

    if frag > 0.5:
        insights.append({
            "severity": "warning",
            "message": "Fragmented knowledge graph",
            "suggestion": "Many isolated nodes. Contributors may be working in silos.",
        })

    if coverage.get("commit_issue_coverage", 0) < 0.3 and coverage.get("total_commits", 0) > 5:
        insights.append({
            "severity": "info",
            "message": f"Only {round(coverage['commit_issue_coverage'] * 100)}% of commits reference issues",
            "suggestion": "Linking commits to issues improves traceability and retrieval quality.",
        })

    if coupling.get("orphan_count", 0) > coupling.get("total_prs", 0) * 0.5:
        insights.append({
            "severity": "info",
            "message": f"{coupling['orphan_count']} PRs have no issue references",
            "suggestion": "Use 'Fixes #N' in PR descriptions to build stronger connections.",
        })

    if freshness.get("freshness") == "stale":
        insights.append({
            "severity": "info",
            "message": f"Last activity was {freshness['age_days']} days ago",
            "suggestion": "Stale repositories may have outdated information.",
        })

    # overall health: simple heuristic based on the metrics
    # TODO: maybe weight these differently or make it configurable
    score = 0
    if density >= 0.05:
        score += 1
    if frag < 0.3:
        score += 1
    if coupling.get("coupling_ratio", 0) >= 0.4:
        score += 1
    if freshness.get("freshness") in ("very_recent", "recent"):
        score += 1

    if score >= 3:
        overall = "healthy"
    elif score >= 2:
        overall = "moderate"
    else:
        overall = "needs_attention"

    return {
        "overall": overall,
        "density": density,
        "fragmentation": frag,
        "component_count": len(components),
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "coverage": coverage,
        "freshness": freshness,
        "coupling": coupling,
        "insights": insights,
    }