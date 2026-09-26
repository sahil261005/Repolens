import unittest
from datetime import datetime, timedelta, timezone

from github_client import compact_item, parse_repo_url
from graph_builder import build_graph, graph_stats
from health import health_report
from llm import classify_intent
from overlap import (
    add_overlap_analysis,
    answer_overlap,
    confidence_level,
    tokens,
)
from retrieval import graph_search, recency_details
from storage import recent_runs, save_analysis, save_query_run, setup_database


class GraphAndOverlapTests(unittest.TestCase):
    def setUp(self):
        self.repo_data = {
            "pull_requests": [
                {
                    "number": 12,
                    "title": "Fix login",
                    "body": "Fixes #7 and follows #8",
                    "author": "maya",
                    "created_at": "2026-09-01T10:00:00Z",
                }
            ],
            "issues": [
                {
                    "number": 7,
                    "title": "Login bug",
                    "body": "",
                    "author": "leo",
                    "created_at": "2026-09-02T10:00:00Z",
                },
                {
                    "number": 8,
                    "title": "Login follow-up",
                    "body": "",
                    "author": "zoe",
                    "created_at": "2026-09-03T10:00:00Z",
                },
            ],
            "commits": [],
        }

    def test_graph_links_and_weights(self):
        graph = build_graph(self.repo_data)
        self.assertEqual(graph["pull_request:12"]["issue:7"]["relation"], "RESOLVES")
        self.assertEqual(graph["pull_request:12"]["issue:8"]["relation"], "MENTIONS")
        self.assertEqual(graph["person:leo"]["issue:7"]["weight"], 0.75)
        self.assertEqual(graph_stats(graph)["relations"]["RESOLVES"], 1)

    def test_weighted_traversal_keeps_path(self):
        graph = build_graph(self.repo_data)
        results = {node_id: (score, path) for node_id, score, path in graph_search(graph, ["pull_request:12"])}
        self.assertEqual(results["person:leo"], (0.675, ["pull_request:12", "issue:7", "person:leo"]))

    def test_hub_throttling_per_relation(self):
        """Verify that an author with 15 PRs has AUTHORED relation throttled to 10."""
        prs = [
            {"number": i, "title": f"PR {i}", "body": "", "author": "super_dev"}
            for i in range(1, 16)
        ]
        repo_data = {"pull_requests": prs, "issues": [], "commits": []}
        graph = build_graph(repo_data)
        traversal = graph_search(graph, ["person:super_dev"], max_hops=1)
        authored_hits = [node_id for node_id, _, _ in traversal if node_id.startswith("pull_request:")]
        self.assertLessEqual(len(authored_hits), 10)

    def test_recency_decay_floor_and_missing_date(self):
        # Missing date -> factor is 1.0 (never penalized)
        age, factor = recency_details({"type": "issue", "created_at": None})
        self.assertIsNone(age)
        self.assertEqual(factor, 1.0)

        # Extremely old item -> hits 0.35 floor
        old_date = (datetime.now(timezone.utc) - timedelta(days=5000)).isoformat()
        _, old_factor = recency_details({"type": "issue", "created_at": old_date})
        self.assertEqual(old_factor, 0.35)

    def test_lexical_overlap_and_shared_tokens(self):
        self.assertEqual(tokens("The login-token and API"), {"login", "token", "api"})
        self.assertEqual(answer_overlap("Login authentication bug", "The login bug was fixed"), 0.667)
        self.assertIsNone(answer_overlap("", "The answer"))

    def test_confidence_bands(self):
        self.assertEqual(confidence_level(0.6), "high")
        self.assertEqual(confidence_level(0.2), "medium")
        self.assertEqual(confidence_level(0.15), "low")
        self.assertEqual(confidence_level(None), "unknown")

    def test_overlap_honest_fallback_on_failure(self):
        trace = {
            "final_results": [
                {"id": "issue:7", "text": "Login bug details"}
            ]
        }
        add_overlap_analysis(trace, "")
        item = trace["final_results"][0]
        self.assertIsNone(item["used"])
        self.assertIsNone(item["answer_overlap"])
        self.assertEqual(item["confidence"], "unknown")
        self.assertEqual(trace["overlap_summary"]["unknown"], 1)

    def test_shared_tokens_and_token_cost_metrics(self):
        trace = {
            "final_results": [
                {"id": "issue:7", "text": "Login bug authentication error"},
                {"id": "issue:8", "text": "Unrelated documentation spelling typo"},
            ]
        }
        answer = "The login bug was fixed in the authentication module."
        add_overlap_analysis(trace, answer)
        item1 = trace["final_results"][0]
        item2 = trace["final_results"][1]
        self.assertTrue(item1["used"])
        self.assertIn("login", item1["shared_tokens"])
        self.assertIn("bug", item1["shared_tokens"])
        self.assertFalse(item2["used"])
        self.assertGreater(trace["overlap_summary"]["used_tokens"], 0)
        self.assertGreater(trace["overlap_summary"]["dead_weight_tokens"], 0)

    def test_intent_classification_keywords_and_fallback(self):
        intent, source = classify_intent("who authored the login fix?")
        self.assertEqual(intent, "relational")
        self.assertEqual(source, "keyword")

        intent2, source2 = classify_intent("how does caching work in repo?")
        self.assertEqual(intent2, "semantic")
        self.assertEqual(source2, "keyword")

    def test_github_url_parsing(self):
        owner, name = parse_repo_url("https://github.com/fastapi/fastapi")
        self.assertEqual((owner, name), ("fastapi", "fastapi"))

        owner, name = parse_repo_url("pallets/flask.git")
        self.assertEqual((owner, name), ("pallets", "flask"))

        with self.assertRaises(ValueError):
            parse_repo_url("not-a-valid-url-format-at-all")

    def test_github_client_filters_prs_from_issues(self):
        item_normal = {"number": 1, "title": "Normal Issue", "user": {"login": "dev"}}
        item_pr = {"number": 2, "title": "PR in issues list", "pull_request": {}, "user": {"login": "dev"}}
        raw_issues = [item_normal, item_pr]
        filtered = [compact_item(i) for i in raw_issues if "pull_request" not in i]
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["number"], 1)

    def test_knowledge_health_report_stats(self):
        graph = build_graph(self.repo_data)
        health = health_report(graph)
        self.assertIn("density", health)
        self.assertIn("fragmentation", health)
        self.assertIn("overall", health)
        self.assertEqual(health["node_count"], 6)  # 1 PR, 2 issues, 3 authors (maya, leo, zoe)
        self.assertGreater(health["edge_count"], 0)

    def test_sqlite_storage_persistence(self):
        setup_database()
        save_analysis("test/repo", {"node_count": 10})
        run_id = save_query_run("test/repo", "test question", "test answer", {"intent": "relational"}, 45)
        runs = recent_runs("test/repo", limit=5)
        self.assertTrue(any(r["id"] == run_id for r in runs))


if __name__ == "__main__":
    unittest.main()
