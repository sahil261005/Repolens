"""Builds an in-memory graph from GitHub repo data using NetworkX."""

import re

import networkx as nx


RESOLVE_PATTERN = re.compile(r"(?:fixes|closes|resolves)\s+#(\d+)", re.IGNORECASE)
MENTION_PATTERN = re.compile(r"#(\d+)")

# truncate long PR/issue bodies so they don't blow up the embedding model
BODY_LIMIT = 500

# edge weights - higher = stronger signal for the retriever
# I tuned these manually by looking at what produced the best traversal results
RELATION_WEIGHTS = {
    "AUTHORED": 0.95,
    "RESOLVES": 0.90,
    "REPORTED": 0.75,
    "MENTIONS": 0.70,
}


def text_value(value):
    # github fields can be None or missing, this just handles that
    return value if isinstance(value, str) else ""


def item_author(item):
    """Figure out who authored this item - handles both compact and raw github data."""
    author = item.get("author")
    if isinstance(author, dict):
        return text_value(author.get("login"))
    if isinstance(author, str):
        return author

    # fallback for raw github response format
    user = item.get("user")
    if isinstance(user, dict):
        return text_value(user.get("login"))
    return text_value(item.get("author_login"))


def item_text(item):
    title = text_value(item.get("title"))
    body = text_value(item.get("body") or item.get("message"))[:BODY_LIMIT]
    return f"{title}\n{body}".strip()


def add_person(graph, login):
    if not login:
        return None

    node_id = f"person:{login}"
    if node_id not in graph:
        graph.add_node(
            node_id,
            id=node_id,
            label=login,
            type="person",
            text=login,
            url="",
            created_at=None,
        )
    return node_id


def add_authored_edge(graph, node_id, item, relation):
    person_id = add_person(graph, item_author(item))
    if person_id:
        graph.add_edge(
            person_id,
            node_id,
            relation=relation,
            weight=RELATION_WEIGHTS[relation],
        )


def add_item_node(graph, item, node_type):
    """Add a PR, issue, or commit node and return its id."""
    if node_type == "pull_request":
        number = item.get("number")
        node_id = f"pull_request:{number}"
        label = f"PR #{number}: {text_value(item.get('title'))}"
    elif node_type == "issue":
        number = item.get("number")
        node_id = f"issue:{number}"
        label = f"Issue #{number}: {text_value(item.get('title'))}"
    else:
        sha = text_value(item.get("sha"))
        node_id = f"commit:{sha}"
        label = f"Commit {sha[:7]}: {text_value(item.get('message') or item.get('title'))}"

    graph.add_node(
        node_id,
        id=node_id,
        label=label,
        type=node_type,
        text=item_text(item),
        url=text_value(item.get("html_url")),
        created_at=item.get("created_at"),
    )
    return node_id


def add_issue_links(graph, node_id, text):
    """Link PRs/commits to issues they reference.

    Only adds edges when the referenced issue actually exists in our graph,
    otherwise we'd get dangling edges to issues we never fetched.
    """
    resolved_numbers = set(RESOLVE_PATTERN.findall(text))

    for number in resolved_numbers:
        issue_id = f"issue:{number}"
        if issue_id in graph:
            graph.add_edge(
                node_id,
                issue_id,
                relation="RESOLVES",
                weight=RELATION_WEIGHTS["RESOLVES"],
            )

    for number in MENTION_PATTERN.findall(text):
        if number in resolved_numbers:
            continue
        issue_id = f"issue:{number}"
        if issue_id in graph:
            graph.add_edge(
                node_id,
                issue_id,
                relation="MENTIONS",
                weight=RELATION_WEIGHTS["MENTIONS"],
            )


def build_graph(repo_data):
    # using undirected graph - tried DiGraph first but for our traversal
    # it doesn't matter if we go person->PR or PR->person
    graph = nx.Graph()
    link_sources = []

    for pull_request in repo_data.get("pull_requests", []):
        node_id = add_item_node(graph, pull_request, "pull_request")
        add_authored_edge(graph, node_id, pull_request, "AUTHORED")
        link_sources.append((node_id, item_text(pull_request)))

    for issue in repo_data.get("issues", []):
        node_id = add_item_node(graph, issue, "issue")
        add_authored_edge(graph, node_id, issue, "REPORTED")
        link_sources.append((node_id, item_text(issue)))

    for commit in repo_data.get("commits", []):
        node_id = add_item_node(graph, commit, "commit")
        add_authored_edge(graph, node_id, commit, "AUTHORED")
        link_sources.append((node_id, item_text(commit)))

    # second pass - now that all nodes exist, we can safely link issues
    for node_id, text in link_sources:
        add_issue_links(graph, node_id, text)

    return graph


def graph_stats(graph):
    """Counts for the UI stats bar."""
    node_types = {}
    relations = {}

    for _, data in graph.nodes(data=True):
        node_type = data.get("type", "unknown")
        node_types[node_type] = node_types.get(node_type, 0) + 1

    for _, _, data in graph.edges(data=True):
        relation = data.get("relation", "unknown")
        relations[relation] = relations.get(relation, 0) + 1

    return {
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "node_types": node_types,
        "relations": relations,
    }
