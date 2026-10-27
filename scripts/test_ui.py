"""UI regression checks with isolated HTTP fixtures; never writes the user's DB.

Run: .venv/Scripts/python.exe -m unittest discover -s scripts -p test_ui.py -v
"""
import copy
import unittest
from urllib.parse import urlparse
from unittest.mock import patch

import requests
from streamlit.testing.v1 import AppTest

from app.catalog import JOBS
from app.ui_components import safe_link


class FakeAPI:
    def __init__(self):
        self.profile = {"grade": "", "major": "", "skills": [], "experience_text": "", "interests": [], "target_city": "", "weekly_hours": 5}
        self.plans = []
        self.analyses = []
        self.feedback = []
        self.chats = []
        self.offline = False
        self.fail_analysis = False
        self.calls = []

    def request(self, method, url, **kwargs):
        path = urlparse(url).path
        self.calls.append((method, path, kwargs.get("json")))
        if self.offline:
            raise requests.ConnectionError("isolated test")
        reads = {"/health": {"status": "ok"}, "/status": {"mode": "demo", "retrieval_mode": "keyword"}, "/profile": self.profile,
                 "/jobs": JOBS, "/visits": [], "/plans": self.plans, "/analyses": self.analyses, "/experience-feedback": self.feedback, "/conversations": self.chats}
        if method == "GET" and path in reads:
            data = reads[path]
        elif method == "GET" and path.endswith("/markdown"):
            data = {"markdown": "# 准备计划\n\n完成标准：留下可复核记录。"}
        elif method == "GET" and path.endswith("/messages"):
            data = [{"role": "user", "content": "过去的问题", "sources": []}, {"role": "assistant", "content": "过去的回答", "sources": []}]
        elif method == "PUT" and path == "/profile":
            self.profile = kwargs["json"]
            data = self.profile
        elif method == "POST" and path == "/experience-feedback":
            data = {"status": "saved"}
            self.feedback.insert(0, kwargs["json"])
        elif method == "POST" and path.startswith("/analysis/"):
            if self.fail_analysis:
                raise requests.ConnectionError("analysis unavailable")
            job = path.rsplit("/", 1)[1]
            data = {"mode": "demo_fallback", "grounding_status": "no_sources", "known_basics": [job + " 已知基础"], "to_confirm": ["项目职责仍需确认"], "actions": ["整理一项项目：形成三条可复核记录。"], "sources": []}
            self.analyses.insert(0, {"id": len(self.analyses) + 1, "job_category": job, "created_at": "2026-10-03T10:00:00+08:00", "result": data})
        elif method == "POST" and path.startswith("/plans/"):
            job = path.rsplit("/", 1)[1]
            settings = kwargs["json"]
            data = self.make_plan(job, settings["duration_weeks"], settings["weekly_hours"])
        elif method == "POST" and path == "/chat":
            data = {"conversation_id": 1, "answer": "测试回答：先确认项目职责。", "mode": "demo_fallback", "sources": []}
        else:
            raise AssertionError("Unexpected request: " + method + " " + path)
        response = requests.Response()
        response.status_code = 200
        response.json = lambda: copy.deepcopy(data)
        return response

    def make_plan(self, job="backend", duration=4, hours=5):
        data = {"id": len(self.plans) + 1, "job_category": job, "job_name": next(j["name"] for j in JOBS if j["id"] == job), "duration_weeks": duration, "weekly_hours": hours,
                "mode": "demo", "grounding_status": "no_sources", "sources": [], "weeks": []}
        for n in range(1, duration + 1):
            data["weeks"].append({"week": n, "goal": "梳理项目经历", "tasks": [{"title": "记录项目 <script>内容</script>", "description": "整理接口和数据表", "completion_criteria": "形成 3 条项目记录", "estimated_hours": min(hours, 2), "learning_resources": [{"title": "Python 文档", "source_url": "https://docs.python.org/zh-cn/3/", "source_name": "Python", "review_status": "not_reviewed"}]}]})
        self.plans.insert(0, {"id": data["id"], "job_category": job, "created_at": "2026-10-03T10:00:00+08:00", "plan": data})
        return data


class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        self.api = FakeAPI()
        self.patcher = patch("requests.request", self.api.request)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.at = AppTest.from_file("app/ui.py", default_timeout=25)

    def run_app(self):
        self.at.run()
        self.assertEqual(list(self.at.exception), [])
        return self.at

    def nav(self, label):
        self.at.button(key="nav_" + label).click()
        return self.run_app()

    def button(self, label):
        return next(item for item in self.at.button if item.label == label)

    def text(self):
        return "\n".join(item.value for item in self.at.markdown)

    def test_all_five_pages_with_empty_profile(self):
        self.run_app()
        self.assertIn("未来的方向", self.text())
        for page in ["个人画像", "岗位探索", "职业分析", "行动计划", "今日概览"]:
            self.nav(page)
        self.assertFalse(any(method != "GET" for method, _, _ in self.api.calls))

    def test_partial_profile_save_preserves_empty_fields(self):
        self.run_app()
        self.nav("个人画像")
        self.assertEqual(next(i for i in self.at.text_input if i.label == "专业").value, "")
        next(i for i in self.at.text_input if i.label == "其他技术（选填）").set_value("Vue，Docker, Rust")
        self.button("保存个人画像").click()
        self.run_app()
        self.assertEqual(self.api.profile["grade"], "")
        self.assertEqual(self.api.profile["major"], "")
        self.assertEqual(self.api.profile["skills"], ["Vue", "Docker", "Rust"])
        self.nav("今日概览")
        self.assertIn("三个方向，慢慢了解", self.text())

    def test_custom_interests_are_saved_and_restored(self):
        self.run_app()
        self.nav("个人画像")
        skills = next(item for item in self.at.multiselect if item.label == "接触过的技术")
        self.assertIn("Python", skills.options)
        interests = next(item for item in self.at.multiselect if item.label == "你更愿意做哪些事情？")
        interests.set_value(["实现功能"])
        next(item for item in self.at.text_input if item.label == "其他想做的事情（选填）").set_value("写脚本，做实验, 写脚本, 实现功能")
        self.button("保存个人画像").click()
        self.run_app()
        self.assertEqual(self.api.profile["interests"], ["实现功能", "写脚本", "做实验"])
        self.nav("今日概览")
        self.nav("个人画像")
        interests = next(item for item in self.at.multiselect if item.label == "你更愿意做哪些事情？")
        self.assertIn("写脚本", interests.options)
        self.assertEqual(interests.value, ["实现功能", "写脚本", "做实验"])

    def test_role_comparison_precedes_experience(self):
        self.run_app()
        self.nav("岗位探索")
        content = self.text()
        self.assertLess(content.index("比较三个方向"), content.index("想先试试看？"))
        self.assertTrue(self.at.button(key="start_backend"))
        self.assertTrue(self.at.button(key="skip_backend"))

    def test_analysis_and_chat_do_not_leak_across_jobs(self):
        self.run_app()
        self.nav("岗位探索")
        self.at.button(key="choose_backend").click()
        self.run_app()
        self.button("更新职业分析").click()
        self.run_app()
        self.assertIn("backend 已知基础", self.text())
        self.at.button(key="shortcut_0").click()
        self.run_app()
        self.assertEqual(len(self.at.chat_message), 2)
        self.run_app()
        self.assertEqual(len(self.at.chat_message), 2, "a rerun must not duplicate persisted conversation")
        self.nav("岗位探索")
        self.at.button(key="choose_frontend").click()
        self.run_app()
        self.assertNotIn("backend 已知基础", self.text())
        self.assertEqual(len(self.at.chat_message), 0)

    def test_custom_question_uses_visible_consultation_form(self):
        self.run_app()
        self.nav("职业分析")
        self.at.text_area(key="consultation_question").set_value("我该如何准备第一个后端项目？")
        self.button("发送问题").click()
        self.run_app()
        chat_calls = [body for method, path, body in self.api.calls if method == "POST" and path == "/chat"]
        self.assertEqual(len(chat_calls), 1)
        self.assertEqual(chat_calls[0]["question"], "我该如何准备第一个后端项目？")
        self.assertEqual(chat_calls[0]["job_category"], "backend")
        self.assertEqual(len(self.at.chat_message), 2)

    def test_analysis_refresh_reorders_and_resets_chat(self):
        self.run_app()
        self.nav("职业分析")
        self.at.button(key="shortcut_0").click()
        self.run_app()
        self.assertEqual(len(self.at.chat_message), 2)
        self.button("更新职业分析").click()
        self.run_app()
        content = self.text()
        self.assertLess(content.index("backend 已知基础"), content.index("职业问答"))
        self.assertEqual(len(self.at.chat_message), 0)
        self.assertIsNone(self.at.session_state["conversation_id"])
        self.assertNotIn("测试回答", content)

    def test_failed_analysis_refresh_keeps_chat(self):
        self.run_app()
        self.nav("职业分析")
        self.at.button(key="shortcut_0").click()
        self.run_app()
        self.api.fail_analysis = True
        self.button("更新职业分析").click()
        self.run_app()
        self.assertEqual(len(self.at.chat_message), 2)
        self.assertIn("测试回答", self.text())

    def test_feedback_start_complete_and_skip(self):
        self.run_app()
        self.nav("岗位探索")
        self.at.button(key="start_backend").click()
        self.run_app()
        self.at.radio[0].set_value("completed")
        self.button("保存体验反馈").click()
        self.run_app()
        self.assertEqual(self.api.feedback[0]["task_status"], "completed")
        self.assertEqual(self.api.feedback[0]["difficulty"], 3)
        self.at.button(key="skip_backend").click()
        self.run_app()
        self.assertEqual(self.api.feedback[0]["task_status"], "skipped")

    def test_plan_generation_history_budget_and_real_resource_links(self):
        self.api.make_plan("frontend", 2, 3)
        old = self.api.make_plan("backend", 2, 5)
        self.run_app()
        self.nav("行动计划")
        self.assertTrue(self.at.get("download_button"))
        self.at.button(key="preset_1").click()
        self.run_app()
        self.assertEqual(self.at.number_input(key="duration_backend").value, 1)
        self.at.number_input(key="hours_backend").set_value(3)
        self.button("生成新计划").click()
        self.run_app()
        self.assertEqual(self.api.plans[0]["plan"]["duration_weeks"], 1)
        self.assertEqual(self.api.plans[0]["plan"]["weekly_hours"], 3)
        self.assertIn('href="https://docs.python.org/zh-cn/3/"', self.text())
        self.assertIn("&lt;script&gt;", self.text())
        self.assertNotIn("<script>内容</script>", self.text())
        history = self.at.selectbox(key="saved_plan_backend")
        self.assertTrue(all("前端" not in option for option in history.options))
        history.select(next(option for option in history.options if option.startswith("#" + str(old["id"]) + " ·")))
        self.run_app()
        self.assertIn("2 周", self.text())
        self.assertEqual(len(self.api.plans), 3)

    def test_overview_history_and_html_escaping(self):
        self.api.profile.update(grade="大三", major="<img src=x onerror=alert(1)>", skills=["Python"])
        self.api.make_plan()
        self.run_app()
        self.assertIn("&lt;img", self.text())
        self.assertNotIn("<img src=x", self.text())
        self.at.button(key="overview_latest_plan").click()
        self.run_app()
        self.assertIn("准备路线", self.text())

    def test_offline_has_one_reconnect_view(self):
        self.api.offline = True
        self.run_app()
        self.assertIn("工作台正在等待连接", self.text())
        self.assertEqual(len(self.at.error), 0)
        self.assertEqual([(method, path) for method, path, _ in self.api.calls], [("GET", "/visits"), ("GET", "/health")])
        self.api.offline = False
        self.button("重新连接").click()
        self.run_app()
        self.assertIn("未来的方向", self.text())

    def test_unsafe_source_urls_are_not_links(self):
        self.assertIsNone(safe_link("javascript:alert(1)"))
        self.assertIsNone(safe_link("file:///etc/passwd"))
        self.assertEqual(safe_link("https://example.com/resource"), "https://example.com/resource")


if __name__ == "__main__":
    unittest.main()
