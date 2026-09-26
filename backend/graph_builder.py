"""Build an in-memory graph from the GitHub data collected for a repository."""

import re

import networkx as nx


RESOLVE_PATTERN = re.compile(r"(?:fixes|closes|resolves)\s+#(\d+)", re.IGNORECASE)
MENTION_PATTERN = re.compile(r"#(\d+)")
BODY_LIMIT = 500
RELATION_WEIGHTS = {
    "AUTHORED": 0.95,
    "RESOLVES": 0.90,
    "REPORTED": 0.75,
    "MENTIONS": 0.70,
}


def text_value(value):
    """Return a safe string because GitHub fields can be missing or null."""
    return value if isinstance(value, str) else ""


def item_author(item):
    """Read an author login from the compact API data or raw GitHub data."""
    author = item.get("author")
    if isinstance(author, dict):
        return text_value(author.get("login"))
    if isinstance(author, str):
        return author

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
    """Add one PR, issue, or commit and return its stable graph node id."""
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
    """Add issue references only when that issue was included in this graph."""
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
    """Create a graph containing people, pull requests, issues, and commits."""
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

    for node_id, text in link_sources:
        add_issue_links(graph, node_id, text)

    return graph


def graph_stats(graph):
    """Return the counts shown in the UI and used for ingestion debugging."""
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
