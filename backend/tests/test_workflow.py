import copy
import json
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

EXAMPLE = json.loads((Path(__file__).resolve().parents[2] / "examples" / "workflow.json").read_text(encoding="utf-8"))


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.dsl = copy.deepcopy(EXAMPLE)

    def run_dsl(self, value="你好"):
        return self.client.post("/api/run", json={"dsl": self.dsl, "input": value})

    def test_true_branch_and_template_state_merge(self):
        response = self.run_dsl()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["outputs"], {
            "start": "你好",
            "llm_1": "[mock-llm:llm_1] 总结：你好",
            "llm_long": "[mock-llm:llm_long] 展开：[mock-llm:llm_1] 总结：你好",
        })

    def test_false_branch(self):
        self.dsl["nodes"][2]["data"]["expression"] = "len(llm_1) > 200"
        response = self.run_dsl()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(set(response.json()["outputs"]), {"start", "llm_1"})

    def test_fallback_to_last_edge(self):
        self.dsl["edges"][2].pop("condition")
        response = self.run_dsl()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn("llm_long", response.json()["outputs"])

    def test_invalid_ids_return_400(self):
        for node_id in ["1start", "bad-id", "含中文", "foo.bar", "__start__"]:
            with self.subTest(node_id=node_id):
                self.dsl = copy.deepcopy(EXAMPLE)
                self.dsl["nodes"][0]["id"] = node_id
                self.assertEqual(self.run_dsl().status_code, 400)

    def test_invalid_graphs(self):
        cases = []
        duplicate = copy.deepcopy(EXAMPLE)
        duplicate["nodes"].append(duplicate["nodes"][0])
        cases.append(duplicate)
        missing = copy.deepcopy(EXAMPLE)
        missing["edges"][0]["target"] = "missing"
        cases.append(missing)
        parallel = copy.deepcopy(EXAMPLE)
        parallel["edges"].append({"source": "llm_1", "target": "end"})
        cases.append(parallel)
        for dsl in cases:
            self.dsl = dsl
            self.assertEqual(self.run_dsl().status_code, 400)

    def test_unavailable_reference_is_actionable(self):
        self.dsl["nodes"][1]["data"]["prompt_template"] = "{{missing.output}}"
        response = self.run_dsl()
        self.assertEqual(response.status_code, 400)
        self.assertIn("missing", response.json()["detail"])

    def test_restricted_expression(self):
        for expression in ["__import__('os')", "llm_1.__class__", "len(llm_1", "missing > 2"]:
            with self.subTest(expression=expression):
                self.dsl["nodes"][2]["data"]["expression"] = expression
                self.assertEqual(self.run_dsl().status_code, 400)

    def test_consecutive_conditions(self):
        self.dsl["nodes"].append({"id": "cond_2", "type": "condition", "data": {"expression": "len(start) == 2"}})
        self.dsl["edges"][2]["target"] = "cond_2"
        self.dsl["edges"].extend([
            {"source": "cond_2", "target": "llm_long", "condition": "true"},
            {"source": "cond_2", "target": "end", "condition": "false"},
        ])
        response = self.run_dsl()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("llm_long", response.json()["outputs"])

    def test_recursion_limit(self):
        self.dsl["edges"][4]["target"] = "llm_1"
        response = self.run_dsl()
        self.assertEqual(response.status_code, 400)
        self.assertIn("25", response.json()["detail"])

    def test_requests_do_not_share_state(self):
        self.assertIn("llm_long", self.run_dsl().json()["outputs"])
        self.dsl["nodes"][2]["data"]["expression"] = "False"
        outputs = self.run_dsl("第二次").json()["outputs"]
        self.assertEqual(outputs["start"], "第二次")
        self.assertNotIn("llm_long", outputs)

    def test_cors_preflight(self):
        response = self.client.options("/api/run", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:5173")


if __name__ == "__main__":
    unittest.main()
