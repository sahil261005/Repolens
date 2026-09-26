"""Fetch a small, public slice of a GitHub repository."""

import re

import requests


GITHUB_API_URL = "https://api.github.com"
REQUEST_TIMEOUT = 15


def parse_repo_url(repo_url):
    """Return owner and repository name from a GitHub URL or owner/name."""
    value = (repo_url or "").strip().rstrip("/")
    url_match = re.fullmatch(r"https?://github\.com/([^/]+)/([^/]+)", value)
    short_match = re.fullmatch(r"([^/\s]+)/([^/\s]+)", value)
    match = url_match or short_match

    if not match:
        raise ValueError(
            "Enter a public GitHub URL such as https://github.com/owner/repo "
            "or owner/repo."
        )

    owner, name = match.groups()
    if name.endswith(".git"):
        name = name[:-4]
    if not owner or not name:
        raise ValueError("The GitHub owner and repository name are required.")
    return owner, name


def request_data(path, token):
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.get(
            f"{GITHUB_API_URL}{path}",
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.Timeout as error:
        raise RuntimeError("GitHub took too long to respond. Please try again.") from error
    except requests.RequestException as error:
        raise RuntimeError("Could not reach GitHub. Please try again.") from error

    if response.status_code == 404:
        raise RuntimeError("Repository not found. Check that it is public and the URL is correct.")
    if response.status_code == 403:
        raise RuntimeError("GitHub rate limit reached. Add a GitHub token and try again later.")
    if not response.ok:
        raise RuntimeError(f"GitHub request failed with status {response.status_code}.")
    return response.json()


def compact_item(item):
    user = item.get("user") or {}
    return {
        "number": item.get("number"),
        "title": item.get("title") or "",
        "body": item.get("body") or "",
        "author": user.get("login") or "",
        "created_at": item.get("created_at"),
        "html_url": item.get("html_url") or "",
    }


def compact_commit(item):
    commit = item.get("commit") or {}
    commit_author = commit.get("author") or {}
    author = item.get("author") or {}
    return {
        "sha": item.get("sha") or "",
        "message": commit.get("message") or "",
        "author": author.get("login") or commit_author.get("name") or "",
        "created_at": commit_author.get("date"),
        "html_url": item.get("html_url") or "",
    }


def fetch_repo_data(owner, name, token=None):
    """Fetch recent PRs, issues, and commits with only needed fields."""
    pull_requests = request_data(f"/repos/{owner}/{name}/pulls?state=all&per_page=30", token)
    issues = request_data(f"/repos/{owner}/{name}/issues?state=all&per_page=30", token)
    commits = request_data(f"/repos/{owner}/{name}/commits?per_page=50", token)

    return {
        "pull_requests": [compact_item(item) for item in pull_requests],
        "issues": [
            compact_item(item)
            for item in issues
            if "pull_request" not in item
        ],
        "commits": [compact_commit(item) for item in commits],
    }
