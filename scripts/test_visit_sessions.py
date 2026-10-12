"""Visit isolation tests use temporary databases and never contact a model."""
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlparse

import requests
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from app import db
from app.api import app


class VisitSessionsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.storage_patch = patch.object(db, "DATABASE_PATH", Path(self.temp.name) / "legacy.db")
        self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)
        db.init_db()
        db.save_profile({"major": "之前的专业", "skills": ["Java"]})
        db.save_plan("backend", {"job_name": "历史计划", "weeks": []})
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def headers(self, digit):
        return {"X-Career-Session": digit * 32}

    def test_new_visit_is_blank_and_all_records_are_isolated(self):
        a, b = self.headers("a"), self.headers("b")
        self.assertEqual(self.client.get("/profile", headers=a).json()["major"], "")
        saved = self.client.put("/profile", headers=a, json={"major": "本次专业", "weekly_hours": 7})
        self.assertEqual(saved.status_code, 200)
        with db.session_database("a" * 32):
            plan_id = db.save_plan("backend", {"job_name": "本次计划", "duration_weeks": 1, "weekly_hours": 7, "weeks": [], "sources": []})
            db.save_analysis("backend", {"known_basics": ["本次基础"]})
            conversation = db.create_conversation("backend")
            db.add_message(conversation, "user", "本次问题")
            db.save_feedback("backend", "skipped")
        for route in ("/plans", "/analyses", "/conversations", "/experience-feedback"):
            self.assertEqual(len(self.client.get(route, headers=a).json()), 1)
            self.assertEqual(self.client.get(route, headers=b).json(), [])
        self.assertEqual(self.client.get("/profile", headers=a).json()["major"], "本次专业")
        self.assertEqual(self.client.get("/profile", headers=b).json()["major"], "")
        self.assertEqual(self.client.get(f"/plans/{plan_id}/markdown", headers=b).status_code, 404)
        self.assertEqual(self.client.get(f"/conversations/{conversation}/messages", headers=b).json(), [])
        # Returning from scoped requests must restore the original database.
        self.assertEqual(db.get_profile()["major"], "之前的专业")
        self.assertEqual(db.list_plans()[0]["plan"]["job_name"], "历史计划")

    def test_chat_uses_visit_profile_and_keeps_messages_in_that_visit(self):
        a, b = self.headers("a"), self.headers("b")
        self.client.put("/profile", headers=a, json={"major": "当前专业", "skills": ["Python"]})
        with patch("app.services.call_model", return_value=None) as model, patch("app.services.search_knowledge", return_value=[]):
            response = self.client.post("/chat", headers=a, json={"job_category": "backend", "question": "如何准备后端岗位？"})
            self.assertEqual(response.status_code, 200)
            prompt = model.call_args.args[0][0]["content"]
            self.assertIn("当前专业", prompt)
            self.assertNotIn("之前的专业", prompt)
            conversation_id = response.json()["conversation_id"]
            follow_up = self.client.post("/chat", headers=a, json={"job_category": "backend", "question": "有什么练习？", "conversation_id": conversation_id})
            self.assertEqual(follow_up.status_code, 200)
        self.assertEqual(len(self.client.get(f"/conversations/{conversation_id}/messages", headers=a).json()), 4)
        self.assertEqual(len(self.client.get("/conversations", headers=a).json()), 1)
        self.assertEqual(self.client.get("/conversations", headers=b).json(), [])
        self.assertEqual(self.client.get(f"/conversations/{conversation_id}/messages", headers=b).json(), [])
        self.assertEqual(db.list_conversations(), [])

    def test_parallel_visits_do_not_share_request_context(self):
        def write_and_read(digit):
            headers = self.headers(digit)
            for _ in range(3):
                response = self.client.put("/profile", headers=headers, json={"major": digit})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.client.get("/profile", headers=headers).json()["major"], digit)
        with ThreadPoolExecutor(max_workers=3) as pool:
            list(pool.map(write_and_read, ["a", "b", "c"]))
        self.assertEqual(db.get_profile()["major"], "之前的专业")

    def test_invalid_session_header_is_rejected(self):
        for session_id in ("../legacy", "", "a" * 33, "g" * 32):
            response = self.client.get("/profile", headers={"X-Career-Session": session_id})
            self.assertEqual(response.status_code, 400)
        self.assertFalse((Path(self.temp.name) / "sessions").exists())

    def test_saved_visits_lists_only_records_with_content(self):
        self.client.get("/profile", headers=self.headers("a"))
        self.client.put("/profile", headers=self.headers("b"), json={"major": "软件工程"})
        with db.session_database("c" * 32):
            db.init_db()
            db.save_analysis("frontend", {"known_basics": ["页面项目"]})
        visits = self.client.get("/visits").json()
        self.assertEqual({item["visit_id"] for item in visits}, {"b" * 32, "c" * 32})
        self.assertEqual(next(item for item in visits if item["major"] == "软件工程")["major"], "软件工程")
        self.assertEqual(next(item for item in visits if item["job_category"] == "frontend")["analysis_count"], 1)

    def test_address_without_visit_opens_most_recent_saved_record(self):
        self.client.put("/profile", headers=self.headers("a"), json={"major": "最近保存"})
        def request(method, url, **kwargs):
            kwargs.pop("timeout", None)
            result = self.client.request(method, urlparse(url).path, **kwargs)
            response = requests.Response()
            response.status_code = result.status_code
            response._content = result.content
            response.encoding = "utf-8"
            return response
        with patch("requests.request", request), patch("app.api.get_chroma_collection", return_value=None):
            at = AppTest.from_file("app/ui.py", default_timeout=25).run()
            self.assertEqual(list(at.exception), [])
            self.assertEqual(at.session_state["visit_id"], "a" * 32)
            self.assertIn("最近保存", "\n".join(m.value for m in at.markdown))
            self.assertEqual(at.query_params["visit"], ["a" * 32])

    def test_browser_refresh_restores_saved_visit(self):
        def request(method, url, **kwargs):
            kwargs.pop("timeout", None)
            result = self.client.request(method, urlparse(url).path, **kwargs)
            response = requests.Response()
            response.status_code = result.status_code
            response._content = result.content
            response.encoding = "utf-8"
            return response
        # Status metadata is unrelated to personal records; avoid vector startup.
        with patch("requests.request", request), patch("app.api.get_chroma_collection", return_value=None):
            at = AppTest.from_file("app/ui.py", default_timeout=25).run()
            self.assertEqual(list(at.exception), [])
            self.assertIn("未来的方向", "\n".join(m.value for m in at.markdown))
            first_id = at.session_state["visit_id"]
            self.assertEqual(at.query_params["visit"], [first_id])
            at.button(key="nav_个人画像").click().run()
            major = next(i for i in at.text_input if i.label == "专业")
            self.assertEqual(major.value, "")
            major.set_value("本次填写")
            next(i for i in at.button if i.label == "保存个人画像").click().run()
            at.button(key="nav_今日概览").click().run()
            self.assertIn("本次填写", "\n".join(m.value for m in at.markdown))
            self.assertEqual(at.session_state["visit_id"], first_id)
            refreshed = AppTest.from_file("app/ui.py", default_timeout=25)
            refreshed.query_params.update(at.query_params)
            refreshed.run()
            self.assertEqual(list(refreshed.exception), [])
            self.assertEqual(refreshed.session_state["visit_id"], first_id)
            self.assertIn("本次填写", "\n".join(m.value for m in refreshed.markdown))
            refreshed.button(key="nav_个人画像").click().run()
            self.assertEqual(next(i for i in refreshed.text_input if i.label == "专业").value, "本次填写")
            self.assertEqual(db.get_profile()["major"], "之前的专业")

    def test_new_visit_is_blank_and_can_import_previous_record(self):
        def request(method, url, **kwargs):
            kwargs.pop("timeout", None)
            result = self.client.request(method, urlparse(url).path, **kwargs)
            response = requests.Response()
            response.status_code = result.status_code
            response._content = result.content
            response.encoding = "utf-8"
            return response
        with patch("requests.request", request), patch("app.api.get_chroma_collection", return_value=None):
            at = AppTest.from_file("app/ui.py", default_timeout=25).run()
            self.assertIn("未来的方向", "\n".join(m.value for m in at.markdown))
            first_id = at.session_state["visit_id"]
            at.button(key="overview_start_profile").click().run()
            self.assertIn("从你的故事开始", "\n".join(m.value for m in at.markdown))
            self.assertEqual(at.session_state["page_nav"], "个人画像")
            next(i for i in at.text_input if i.label == "专业").set_value("可恢复的专业")
            next(i for i in at.button if i.label == "保存个人画像").click().run()
            at.button(key="new_visit").click().run()
            self.assertNotEqual(at.session_state["visit_id"], first_id)
            self.assertEqual(at.session_state["page_nav"], "今日概览")
            self.assertIn("未来的方向", "\n".join(m.value for m in at.markdown))
            self.assertEqual(at.query_params["visit"], [at.session_state["visit_id"]])
            at.button(key="import_visit").click().run()
            self.assertEqual(at.session_state["visit_id"], first_id)
            at.button(key="nav_个人画像").click().run()
            self.assertEqual(next(i for i in at.text_input if i.label == "专业").value, "可恢复的专业")


if __name__ == "__main__":
    unittest.main()
