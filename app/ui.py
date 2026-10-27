import os
import re
from pathlib import Path
from uuid import uuid4

import requests
import streamlit as st
from dotenv import load_dotenv
from app.dashboard import select_dashboard_state, summarize_experience_feedback
from app.catalog import JOB_BY_ID
from app.services import normalize_analysis

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
API_PORT = os.getenv("API_PORT", "8002")
API_URL = os.getenv("CAREER_API_URL", "http://127.0.0.1:{0}".format(API_PORT)).rstrip("/")
JOBS = [
    {"id": "backend", "name": "后端开发"},
    {"id": "frontend", "name": "前端开发"},
    {"id": "testing", "name": "测试开发"},
]

SKILL_CHECKS = {
    "backend": [
        ("Java 或 Python", ("java", "python")),
        ("SQL 与数据库", ("sql", "mysql", "数据库")),
        ("HTTP 与接口", ("http", "接口", "api")),
        ("Git 与 Linux", ("git", "linux")),
    ],
    "frontend": [
        ("HTML / CSS", ("html", "css")),
        ("JavaScript / TypeScript", ("javascript", "typescript", "js")),
        ("Vue / React", ("vue", "react")),
        ("接口接入与浏览器调试", ("接口", "api", "浏览器")),
    ],
    "testing": [
        ("测试方法与用例设计", ("测试", "用例")),
        ("Python / Java", ("python", "java")),
        ("API 测试", ("接口测试", "api", "postman")),
        ("SQL 与 Linux", ("sql", "mysql", "linux")),
    ],
}

st.set_page_config(page_title="向前 · 职业规划", page_icon=":material/near_me:", layout="wide", initial_sidebar_state="expanded")
from app.ui_components import (
    load_theme, page_header, section_heading, empty_state, html,
    format_date, render_runtime_state, render_sources, render_resources,
)
load_theme()
_read_cache = {}
PAGES = ("今日概览", "个人画像", "岗位探索", "职业分析", "行动计划")
url_visit = st.query_params.get("visit", "")
if not url_visit:
    try:
        response = requests.request("GET", API_URL + "/visits", timeout=3)
        response.raise_for_status()
        recent = response.json()
    except (requests.RequestException, ValueError):
        recent = []
    candidate = recent[0].get("visit_id", "") if isinstance(recent, list) and recent and isinstance(recent[0], dict) else ""
    url_visit = candidate if re.fullmatch(r"[0-9a-f]{32}", candidate) else uuid4().hex
    st.query_params["visit"] = url_visit
elif not isinstance(url_visit, str) or not re.fullmatch(r"[0-9a-f]{32}", url_visit):
    url_visit = uuid4().hex
    st.query_params["visit"] = url_visit
if st.session_state.get("visit_id") != url_visit:
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state["visit_id"] = url_visit
    url_page = st.query_params.get("page", "今日概览")
    st.session_state["page_nav"] = url_page if url_page in PAGES else "今日概览"
    url_job = st.query_params.get("job", "")
    if url_job in (job["id"] for job in JOBS):
        st.session_state["job_category"] = url_job


def api(method, path, **kwargs):
    if st.session_state.get("backend_offline"):
        return None
    cache_key = (st.session_state.get("visit_id"), path)
    if method == "GET" and cache_key in _read_cache:
        return _read_cache[cache_key]
    try:
        headers = dict(kwargs.pop("headers", {}))
        headers["X-Career-Session"] = st.session_state["visit_id"]
        response = requests.request(method, API_URL + path, headers=headers, timeout=(3, 110 if method != "GET" else 12), **kwargs)
        response.raise_for_status()
        result = response.json()
        if method == "GET":
            _read_cache[cache_key] = result
        else:
            _read_cache.clear()
        return result
    except (requests.RequestException, ValueError):
        st.error("暂时无法读取或保存内容，请稍后重试。你的输入仍保留在当前页面。")
        return None


def job_name(job_id):
    return next((job["name"] for job in JOBS if job["id"] == job_id), job_id)


def split_comma_values(value):
    return list(dict.fromkeys(item.strip() for item in value.replace("，", ",").split(",") if item.strip()))


def choose_job(job_id):
    changed = job_id != st.session_state.get("job_category")
    if changed:
        for key in ("analysis", "analysis_job", "conversation_id", "loaded_conversation_id", "pending_question"):
            st.session_state.pop(key, None)
        st.session_state["chat_display"] = []
    st.session_state["job_category"] = job_id
    st.session_state["plan_job"] = job_id
    st.query_params["job"] = job_id
    return changed


def go_to(page):
    st.query_params["page"] = page
    st.session_state["next_page"] = page
    st.rerun()


def activate_visit(visit_id):
    """Switch the active local record without deleting saved visits."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state["visit_id"] = visit_id
    st.session_state["page_nav"] = "今日概览"
    st.query_params["visit"] = visit_id
    st.query_params["page"] = "今日概览"
    if "job" in st.query_params:
        del st.query_params["job"]
    st.rerun()


def new_visit():
    activate_visit(uuid4().hex)


def overview_page():
    profile = api("GET", "/profile") or {}
    plans = api("GET", "/plans") or []
    conversations = api("GET", "/conversations") or []
    analyses = api("GET", "/analyses") or []
    state = select_dashboard_state(profile, plans, conversations, analyses)
    if not state["has_profile"]:
        with st.container(key="welcome_stage"):
            intro, visual = st.columns([1.05, 1], gap="large", vertical_alignment="center")
            with intro:
                st.markdown('<div class="welcome-overline"><span class="welcome-spark">✦</span> 向前 / 职业探索工作台</div><h1 class="welcome-title">未来的方向，<br><em>从现在出发。</em></h1><p class="welcome-lead">把你学过的、做过的和感兴趣的事放在一起，慢慢找到值得投入的方向。</p>', unsafe_allow_html=True)
                if st.button("开始填写个人画像", key="overview_start_profile", type="primary", icon=":material/arrow_forward:"):
                    st.session_state["profile_started"] = True
                    go_to("个人画像")
                st.markdown('<div class="welcome-time">约 2 分钟，先写下你已经知道的部分。</div>', unsafe_allow_html=True)
            with visual:
                st.image((PROJECT_ROOT / "app" / "assets" / "career-journey.svg").read_text(encoding="utf-8"), width="stretch")
        section_heading("先认识现在的你", "从这里开始")
        st.markdown('<div class="welcome-steps"><div class="welcome-step"><span>01</span><div><b>你的学习阶段</b><small>专业与年级</small></div></div><div class="welcome-step"><span>02</span><div><b>你做过的事</b><small>技能、课程与项目</small></div></div><div class="welcome-step"><span>03</span><div><b>你的准备节奏</b><small>每周可投入的时间</small></div></div></div>', unsafe_allow_html=True)
        return
    page_header("YOUR CAREER SPACE / 工作台", "每一步，都更接近你的方向。", "从认识自己，到了解岗位，再把想法变成可以开始的行动。")
    action = state["next_action"]
    targets = {"profile": "个人画像", "explore": "岗位探索", "analysis": "职业分析", "plan": "行动计划"}
    titles = {"profile": "先从认识自己开始。", "explore": "让兴趣，遇见具体的工作。", "analysis": "接着上次的思考，继续向前。", "plan": "把下一步，落在行动里。"}
    descriptions = {
        "profile": "写下你的专业、接触过的技术和项目经历。不必一次填完整，我们从你已经知道的部分开始。",
        "explore": "你的画像已经保存。看看后端、前端与测试开发的日常工作，找到值得进一步了解的方向。",
        "analysis": "回到已保存的职业分析，梳理已有基础、还需要确认的信息，以及值得尝试的准备行动。",
        "plan": "打开已保存的准备计划，从一个具体任务开始。你也可以根据自己的节奏调整周期与时间。",
    }
    primary, budget = st.columns([2.2, 1], gap="medium")
    with primary, st.container(key="next_step"):
        st.markdown('<div class="eyebrow">建议的下一步 / {0}</div><div class="hero-title">{1}</div><p class="hero-copy">{2}</p>'.format(
            html(job_name(state["selected_job"])) if state["selected_job"] else "从这里开始", titles[action], descriptions[action]), unsafe_allow_html=True)
        if st.button("开始填写画像" if action == "profile" else "继续" + targets[action], key="overview_continue", type="primary", icon=":material/arrow_forward:"):
            if state["selected_job"]:
                choose_job(state["selected_job"])
            if action == "plan" and state["latest_plan"]:
                st.session_state["next_saved_plan_id"] = state["latest_plan"]["id"]
            go_to(targets[action])
        st.markdown('<div class="hero-meta">随时补充，按自己的节奏探索。</div>', unsafe_allow_html=True)
    with budget, st.container(key="time_budget"):
        st.markdown('<div class="budget-title">每周留给未来的时间</div><div class="budget-value">{0}<small>小时 / 周</small></div><div class="budget-copy">{1}<br>仅用于职业探索与求职准备，不含上课和课程作业。</div>'.format(
            html(profile.get("weekly_hours") or 5), "按已保存的画像安排" if state["has_profile"] else "默认预算，可以随时调整"), unsafe_allow_html=True)
        if st.button("调整准备时间", key="overview_hours", use_container_width=True):
            go_to("个人画像")
    st.markdown('<div class="journey">' + ''.join('<div class="journey-step"><span>{0:02d}</span><div><b>{1}</b><small>{2}</small></div></div>'.format(i, title, copy) for i, title, copy in [
        (1, "认识自己", "整理技能与经历"), (2, "比较方向", "了解真实工作内容"), (3, "找到下一步", "梳理基础与待确认项"), (4, "开始行动", "按时间安排准备任务")]) + '</div>', unsafe_allow_html=True)
    if state["has_profile"]:
        section_heading("继续本次的探索", "本次访问中保存的记录")
        recent = st.columns(3, gap="medium")
        record_types = [("职业分析", "latest_analysis", "职业分析"), ("行动计划", "latest_plan", "行动计划"), ("最近咨询", "latest_conversation", "职业分析")]
        for col, (label, field, target) in zip(recent, record_types):
            with col, st.container(border=True, key="record_" + field):
                item = state[field]
                st.markdown('<div class="record-title">{0}</div>'.format(label), unsafe_allow_html=True)
                if item:
                    detail = format_date(item.get("created_at"))
                    if field == "latest_plan":
                        detail = "{0} 周准备计划 · {1}".format(item.get("plan", {}).get("duration_weeks", 4), detail)
                    elif field == "latest_conversation":
                        detail = (item.get("last_message") or "已保存的咨询")[:60]
                    st.markdown('<div class="record-value">{0}</div><div class="record-meta">{1}</div>'.format(html(job_name(item.get("job_category", ""))), html(detail)), unsafe_allow_html=True)
                    if st.button("继续咨询" if field == "latest_conversation" else "打开" + label, key="overview_" + field, use_container_width=True):
                        choose_job(item.get("job_category", "backend"))
                        if field == "latest_plan":
                            st.session_state["next_saved_plan_id"] = item["id"]
                        if field == "latest_conversation":
                            st.session_state["conversation_id"] = item["id"]
                            st.session_state.pop("loaded_conversation_id", None)
                            st.session_state["chat_display"] = []
                        go_to(target)
                else:
                    st.markdown('<div class="record-empty">还没有保存的{0}<br>从感兴趣的方向开始就好。</div>'.format(label), unsafe_allow_html=True)
                    if st.button("开始探索", key="empty_" + field, use_container_width=True):
                        go_to("岗位探索")
    section_heading("三个方向，慢慢了解", "不急着决定，先看看每天会做什么")
    for col, job in zip(st.columns(3, gap="medium"), JOBS):
        with col, st.container(border=True, key="shortcut_" + job["id"]):
            code, detail = {"backend": ("</>", "服务、接口与数据"), "frontend": ("[]", "页面、交互与体验"), "testing": ("✓", "质量、测试与自动化")}[job["id"]]
            st.markdown('<div class="role-mini"><div class="role-monogram {0}">{1}</div><div><b>{2}</b><small>{3}</small></div></div>'.format(job["id"], html(code), job["name"], detail), unsafe_allow_html=True)
            if st.button("了解这个方向", key="overview_role_" + job["id"], use_container_width=True):
                choose_job(job["id"])
                go_to("岗位探索")


def profile_page():
    page_header("01 / PROFILE", "从你的故事开始。", "每一段课程、项目和兴趣，都是理解职业方向的线索。")
    profile = api("GET", "/profile")
    if profile is None:
        return
    form_col, note_col = st.columns([2.7, 1], gap="large")
    with form_col:
        with st.form("profile_form"):
            st.markdown('<div class="form-section"><span>01</span>基本信息</div>', unsafe_allow_html=True)
            col_a, col_b = st.columns(2)
            grade_options = ["暂不填写", "大一", "大二", "大三", "大四", "其他"]
            saved_grade = profile.get("grade") or "暂不填写"
            grade = col_a.selectbox("年级", grade_options, index=grade_options.index(saved_grade) if saved_grade in grade_options else 5)
            major = col_b.text_input("专业", profile.get("major") or "", placeholder="例如：软件工程")
            st.markdown('<div class="form-section"><span>02</span>技能与经历</div>', unsafe_allow_html=True)
            current_skills = profile.get("skills", [])
            known = ["Java", "Python", "MySQL", "HTML / CSS", "JavaScript", "Git", "Linux", "接口测试"]
            with st.container(key="skills_dropdown"):
                selected_skills = st.multiselect("接触过的技术", known, default=[item for item in current_skills if item in known], placeholder="选出你接触过的技术，不要求熟练")
                st.markdown('<div class="skills-hover-options">' + ''.join('<span>{0}</span>'.format(html(item)) for item in known) + '</div>', unsafe_allow_html=True)
            other_skills = st.text_input("其他技术（选填）", value=", ".join([item for item in current_skills if item not in known]), placeholder="例如：Vue，Docker，用逗号分隔")
            experience = st.text_area("课程项目或实习经历", profile.get("experience_text", ""), height=135, placeholder="做过什么项目？你负责哪一部分？遇到过什么问题？课程作业和个人小项目都可以写。")
            st.markdown('<div class="form-section"><span>03</span>兴趣与准备节奏</div>', unsafe_allow_html=True)
            options = ["实现功能", "制作页面", "发现和定位问题", "分析数据", "还不确定"]
            saved_interests = profile.get("interests", [])
            interest_options = list(dict.fromkeys(options + saved_interests))
            interests = st.multiselect("你更愿意做哪些事情？", interest_options, default=saved_interests, placeholder="不确定也没关系")
            other_interests = st.text_input("其他想做的事情（选填）", placeholder="例如：写脚本，做实验，用逗号分隔")
            col_c, col_d = st.columns(2)
            city = col_c.text_input("意向城市（选填）", profile.get("target_city", ""), placeholder="例如：杭州，或暂时不限")
            hours = col_d.number_input("每周准备时间（小时）", min_value=1, max_value=40, value=max(1, min(40, int(profile.get("weekly_hours") or 5))), step=1)
            st.caption("准备时间只统计职业探索、项目梳理、学习和求职准备，不包括上课和课程作业。")
            submitted = st.form_submit_button("保存个人画像", type="primary", use_container_width=True)
        if submitted:
            skills = list(dict.fromkeys(selected_skills + split_comma_values(other_skills)))
            selected_interests = list(dict.fromkeys(interests + split_comma_values(other_interests)))
            result = api("PUT", "/profile", json={"grade": "" if grade == "暂不填写" else grade, "major": major, "skills": skills, "experience_text": experience, "interests": selected_interests, "target_city": city, "weekly_hours": int(hours)})
            if result is not None:
                st.success("画像已保存。下一步，看看不同岗位的日常工作。")
                st.session_state["profile_saved"] = True
        if st.session_state.get("profile_saved"):
            if st.button("去比较岗位方向", icon=":material/arrow_forward:"):
                go_to("岗位探索")
    with note_col:
        st.markdown('<aside class="profile-aside"><div class="eyebrow">A NOTE FOR YOU</div><h3>不需要完美的起点，<br>真实就很好。</h3><p><b>写你知道的部分</b>不要求给技能打分。接触过，不等于已经精通。</p><p><b>空白也是一种信息</b>未填写的内容会被列为“还需要确认”，不会被当作能力不足。</p><p><b>之后还可以改变</b>画像可以多次补充；新的经历和想法，都能成为下一次探索的起点。</p></aside>', unsafe_allow_html=True)


def opportunity_page():
    page_header("02 / EXPLORE", "看看不同方向的日常。", "比较工作内容、常见技能和你的经历，再决定想深入了解哪一个。")
    profile = api("GET", "/profile") or {}
    jobs = api("GET", "/jobs")
    if not jobs:
        return
    selected = st.session_state.get("job_category")
    if profile.get("skills"):
        st.caption("画像中提到：" + " · ".join(profile["skills"]))
    else:
        st.caption("还没有填写技术经历也可以先比较；未填写的信息不会被当作能力不足。")
    section_heading("比较三个方向", "结合日常工作、技能与自己的经历")
    for index, (col, job) in enumerate(zip(st.columns(3, gap="medium"), jobs)):
        with col, st.container(key="role_card_" + job["id"]):
            code = {"backend": "</>", "frontend": "[]", "testing": "✓"}[job["id"]]
            is_selected = selected == job["id"]
            badge = '<span class="state-pill ok role-selected">当前关注</span>' if is_selected else '<span class="job-code">0{0}</span>'.format(index + 1)
            st.markdown('<div class="job-card-top"><div class="role-monogram {0}">{1}</div>{2}</div><div class="job-title">{3}</div><div class="job-code">{4}</div><p class="job-summary">{5}</p>'.format(job["id"], html(code), badge, html(job["name"]), html(job["english"]), html(job["summary"])), unsafe_allow_html=True)
            st.markdown('<div class="comparison-label">日常会做什么</div><ul class="work-list">' + ''.join('<li>{0}</li>'.format(html(item)) for item in job["daily_work"]) + '</ul>', unsafe_allow_html=True)
            st.markdown('<div><div class="comparison-label">经常用到的技能</div><div class="skill-tags">' + ''.join('<span class="tag">{0}</span>'.format(html(skill)) for skill in job["skills"]) + '</div></div>', unsafe_allow_html=True)
            skills = [value.lower() for value in profile.get("skills", [])]
            matched = [label for label, aliases in SKILL_CHECKS[job["id"]] if any(alias in skill for alias in aliases for skill in skills)]
            gaps = [label for label, aliases in SKILL_CHECKS[job["id"]] if label not in matched]
            st.markdown('<div class="comparison-box"><p><b>画像中已提到</b>{0}</p><p class="unknown"><b>目前还待了解</b>{1}</p></div>'.format(html("、".join(matched) or "暂无相关记录，可以之后补充。"), html("、".join(gaps) or "已有技能的实际应用与熟练程度。")), unsafe_allow_html=True)
            if st.button("继续分析此方向" if is_selected else "选择这个方向", key="choose_" + job["id"], type="primary" if is_selected else "secondary", use_container_width=True):
                choose_job(job["id"])
                go_to("职业分析")
    st.caption("岗位介绍是通用工作内容，不代表具体企业要求；画像对照只反映填写情况，不是熟练度评估。")
    with st.container(key="experience_panel"):
        details, controls = st.columns([2.2, 1], gap="large", vertical_alignment="center")
        with controls:
            task_job = st.selectbox("选择想体验的方向", [job["id"] for job in jobs], index=[job["id"] for job in jobs].index(selected) if selected in [job["id"] for job in jobs] else 0, format_func=job_name, key="experience_job")
        task = JOB_BY_ID[task_job]["starter_task"]
        with details:
            st.markdown('<div class="experience-intro"><span>动手试试 · {0}</span><h2>想先试试看？</h2><p>先体验一个真实的小任务，再判断自己是否喜欢这个方向。可以跳过，不影响继续探索。</p><strong>{1}</strong><p>{2}</p></div>'.format(html(task["duration"]), html(task["title"]), html(task["description"])), unsafe_allow_html=True)
        with controls:
            if st.button("开始体验", key="start_" + task_job, type="primary", icon=":material/play_arrow:", use_container_width=True):
                result = api("POST", "/experience-feedback", json={"job_category": task_job, "choice": "started", "task_status": "started"})
                if result is not None:
                    st.session_state["active_task"] = task_job
            if st.button("暂不体验", key="skip_" + task_job, use_container_width=True):
                if api("POST", "/experience-feedback", json={"job_category": task_job, "choice": "skipped", "task_status": "skipped"}) is not None:
                    st.session_state.pop("active_task", None)
                    st.success("已记录跳过。你可以直接选择方向继续分析。")
        if st.session_state.get("active_task") == task_job:
            with st.form("feedback_" + task_job):
                task_status = st.radio("本次体验状态", ["started", "completed"], format_func=lambda value: "已开始，尚未完成" if value == "started" else "已完成", horizontal=True)
                feedback_cols = st.columns(3)
                interest = feedback_cols[0].slider("兴趣程度", 1, 5, 3)
                difficulty = feedback_cols[1].slider("主观难度", 1, 5, 3, help="1 很轻松；3 有挑战但能完成；5 非常吃力。")
                continued = feedback_cols[2].slider("继续意愿", 1, 5, 3)
                st.caption("三个维度分别记录，不会合并为岗位分数。难度：1 很轻松，3 有挑战但能完成，5 非常吃力。")
                note = st.text_input("体验感受（选填）")
                save = st.form_submit_button("保存体验反馈", type="primary")
            if save:
                result = api("POST", "/experience-feedback", json={"job_category": task_job, "choice": "started", "task_status": task_status, "interest": interest, "difficulty": difficulty, "continue_interest": continued, "note": note})
                if result is not None:
                    st.success("反馈已保存。兴趣、难度和继续意愿只反映你的主观感受。")
    feedback = summarize_experience_feedback(api("GET", "/experience-feedback") or [])
    if feedback:
        with st.expander("回顾已保存的体验反馈"):
            for job in jobs:
                item = feedback.get(job["id"])
                if not item:
                    continue
                status = {"skipped": "已跳过", "started": "已开始，尚未完成", "completed": "已完成"}.get(item["task_status"], "状态未知")
                st.markdown("**{0} · {1}**".format(job["name"], status))
                if item.get("interest") is not None:
                    st.caption("兴趣 {0}/5 · 主观难度 {1}/5 · 继续意愿 {2}/5".format(item["interest"], item.get("difficulty", "—"), item.get("continue_interest", "—")))
                if item.get("note"):
                    st.write(item["note"])


def consultation_section(selected):
    with st.container(key="consultation_panel"):
        st.markdown('<div class="consultation-intro"><span>职业问答</span><h2>想了解这个岗位？直接问。</h2><p>关于日常工作、已有经历和下一步准备，都可以从这里开始。</p></div>', unsafe_allow_html=True)
        with st.form("consultation_form", clear_on_submit=True, border=False):
            custom_question = st.text_area("你的问题", placeholder="例如：后端开发需要怎样的项目经历？", height=95, key="consultation_question")
            submitted = st.form_submit_button("发送问题", type="primary", icon=":material/send:")
        st.markdown('<div class="consultation-shortcuts">也可以直接问</div>', unsafe_allow_html=True)
        shortcuts = ["这个岗位日常做什么？", "哪些经历还需要确认？", "下一步可以先做什么？"]
        short_cols = st.columns(3)
        for index, shortcut in enumerate(shortcuts):
            if short_cols[index].button(shortcut, key="shortcut_" + str(index), use_container_width=True):
                st.session_state["pending_question"] = shortcut
        question = custom_question.strip() if submitted else None
        if submitted and not question:
            st.info("先输入想了解的问题，再发送。")
        if not question:
            question = st.session_state.pop("pending_question", None)
        if "conversation_id" not in st.session_state:
            st.session_state["conversation_id"] = None
        active_conversation = st.session_state.get("conversation_id")
        if active_conversation and st.session_state.get("loaded_conversation_id") != active_conversation:
            messages = api("GET", "/conversations/{0}/messages".format(active_conversation))
            if messages is not None:
                st.session_state["chat_display"] = [
                    {"role": item["role"], "content": item["content"], "sources": item.get("sources", [])}
                    for item in messages
                ]
                st.session_state["loaded_conversation_id"] = active_conversation
        if question:
            with st.spinner("正在整理回答…"):
                result = api("POST", "/chat", json={"question": question, "job_category": selected, "conversation_id": st.session_state["conversation_id"]})
            if result:
                st.session_state["conversation_id"] = result["conversation_id"]
                st.session_state["loaded_conversation_id"] = result["conversation_id"]
                st.session_state.setdefault("chat_display", []).extend([
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": result["answer"], "sources": result.get("sources", []), "mode": result.get("mode")},
                ])
        for message in st.session_state.get("chat_display", []):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if message["role"] == "assistant" and message.get("sources"):
                    with st.expander("查看回答依据"):
                        render_sources(message["sources"])
                if message["role"] == "assistant" and message.get("mode") in ("demo", "demo_fallback"):
                    st.caption("本地演示回答 · 模型 API 当前不可用或未配置")
        with st.expander("打开历史对话"):
            history = api("GET", "/conversations")
            if history:
                options = {"选择一段对话": None}
                for item in history:
                    if item["job_category"] == selected:
                        preview = (item.get("last_message") or "新对话").replace("\n", " ")[:32]
                        options["#{0} · {1}".format(item["id"], preview)] = item["id"]
                chosen = st.selectbox("最近保存的对话", list(options.keys()))
                if options[chosen] and st.button("加载这段对话"):
                    messages = api("GET", "/conversations/{0}/messages".format(options[chosen]))
                    if messages is not None:
                        st.session_state["conversation_id"] = options[chosen]
                        st.session_state["loaded_conversation_id"] = options[chosen]
                        st.session_state["chat_display"] = [
                            {"role": item["role"], "content": item["content"], "sources": item.get("sources", [])}
                            for item in messages
                        ]
                        st.rerun()


def analysis_page():
    page_header("03 / ANALYSIS", "看清基础，再找到下一步。", "以你提供的信息为起点，把已经知道的与还需要确认的分开梳理。")
    toolbar, update = st.columns([2.4, 1], vertical_alignment="bottom")
    selected = st.session_state.get("job_category", "backend")
    selected = toolbar.selectbox("当前分析岗位", [job["id"] for job in JOBS], format_func=job_name, index=[job["id"] for job in JOBS].index(selected))
    if choose_job(selected):
        st.rerun()
    if update.button("更新职业分析", type="primary", icon=":material/refresh:", use_container_width=True):
        with st.spinner("正在结合画像与资料整理分析…"):
            result = api("POST", "/analysis/" + selected)
        if result:
            st.session_state["analysis"] = result
            st.session_state["analysis_job"] = selected
            for key in ("chat_display", "conversation_id", "loaded_conversation_id", "pending_question"):
                st.session_state.pop(key, None)
    profile = api("GET", "/profile") or {}
    profile_parts = [profile.get("grade"), profile.get("major"), "、".join(profile.get("skills", []))]
    st.caption("画像摘要：" + (" · ".join(part for part in profile_parts if part) or "尚未填写，可以先补充个人画像。"))
    saved = [item for item in (api("GET", "/analyses") or []) if item.get("job_category") == selected]
    analysis = st.session_state.get("analysis")
    if analysis is None and saved:
        analysis = saved[0].get("result")
        st.session_state["analysis"] = analysis
        st.session_state["analysis_job"] = selected
    if analysis is None:
        empty_state("你的第一份岗位分析，从这里开始", "点击“更新职业分析”，查看已有基础、待确认信息与建议行动。也可以继续在下方提问。")
    else:
        analysis = normalize_analysis(analysis)
        render_runtime_state(analysis.get("mode"), analysis.get("grounding_status", "no_sources"))
        if analysis.get("warning"):
            st.warning(analysis["warning"])
        if analysis.get("grounding_status") == "review_required":
            st.caption("引用资料包含待复核内容，具体招聘要求请以来源页面为准。")
        for col, key, title, note, symbol in zip(st.columns(2, gap="medium"),
                ["known_basics", "to_confirm"], ["已经提到的基础", "还需要确认"],
                ["来自你的画像；接触过不等于已验证熟练度。", "未知不等于不足，补充信息后再判断。"], ["✓", "?"]):
            with col, st.container(key="analysis_" + key):
                st.markdown('<div class="insight-heading"><span class="insight-icon {0}">{1}</span><h3>{2}</h3></div>'.format("warm" if key == "to_confirm" else "", symbol, title), unsafe_allow_html=True)
                st.caption(note)
                items = analysis.get(key, [])
                if items:
                    st.markdown('<ul class="insight-list">' + ''.join('<li>{0}</li>'.format(html(item)) for item in items) + '</ul>', unsafe_allow_html=True)
                else:
                    st.caption("目前还没有足够信息，可以补充画像后重新分析。")
        section_heading("建议先做的事", "从小而具体的行动开始")
        for index, item in enumerate(analysis.get("actions", []), 1):
            st.markdown('<div class="action-row"><span>{0:02d}</span><p>{1}</p></div>'.format(index, html(item)), unsafe_allow_html=True)
        if not analysis.get("actions"):
            st.caption("暂无可执行建议，请补充画像或重新生成分析。")
        render_sources(analysis.get("sources", []))
        if st.button("用这份分析制定行动计划", type="primary", icon=":material/arrow_forward:"):
            st.session_state["plan"] = None
            go_to("行动计划")
    consultation_section(selected)
    if saved:
        with st.expander("查看历史分析 · {0} 个版本".format(len(saved))):
            history_options = {"当前分析": None}
            for row in saved:
                history_options["#{0} · {1}".format(row["id"], format_date(row.get("created_at")))] = row
            choice = st.selectbox("已保存的分析版本", list(history_options), key="analysis_history_" + selected)
            if history_options[choice] and st.button("打开这个分析版本"):
                st.session_state["analysis"] = history_options[choice]["result"]
                st.rerun()


def set_duration(job, weeks):
    st.session_state["duration_" + job] = weeks


def plan_page():
    page_header("04 / PLAN", "把方向，变成可执行的计划。", "合理安排每周的投入，让准备有节奏，也为生活留出空间。")
    profile = api("GET", "/profile") or {}
    selected = st.session_state.get("job_category", "backend")
    with st.container(key="plan_settings"):
        controls = st.columns([1.4, 1, 1], gap="medium")
        selected = controls[0].selectbox("计划目标岗位", [job["id"] for job in JOBS], index=[job["id"] for job in JOBS].index(selected), format_func=job_name)
        if choose_job(selected):
            st.rerun()
        duration = controls[1].number_input("准备周期（周）", min_value=1, max_value=12, value=4, step=1, key="duration_" + selected)
        weekly_hours = controls[2].number_input("每周准备时间（小时）", min_value=1, max_value=40, value=max(1, min(40, int(profile.get("weekly_hours") or 5))), step=1, key="hours_" + selected)
        with st.container(key="presets"):
            preset_cols = st.columns([1, 1, 1, 1, 3])
            for col, weeks in zip(preset_cols, [1, 2, 4, 8]):
                col.button("{0} 周".format(weeks), key="preset_" + str(weeks), on_click=set_duration, args=(selected, weeks), use_container_width=True)
        st.caption("每周预算只包含职业探索、学习和求职准备，不含上课与作业。在这里调整，不会修改个人画像。")
        generate = st.button("生成新计划", type="primary", icon=":material/auto_awesome:")
    previous = [item for item in (api("GET", "/plans") or []) if item.get("job_category") == selected]
    plan = None
    choices = {}
    for item in previous:
        stored = item.get("plan", {})
        choices["#{0} · {1} · {2} 周 / 每周 {3} 小时".format(item["id"], format_date(item.get("created_at")), stored.get("duration_weeks", 4), stored.get("weekly_hours", "未记录"))] = item
    if choices:
        history_key = "saved_plan_" + selected
        next_id = st.session_state.pop("next_saved_plan_id", None)
        next_label = next((label for label, item in choices.items() if item["id"] == next_id), None)
        if next_label:
            st.session_state[history_key] = next_label
        elif st.session_state.get(history_key) not in choices:
            st.session_state[history_key] = next(iter(choices))
        saved_choice = st.selectbox("已保存的计划版本", list(choices), key=history_key)
        row = choices[saved_choice]
        plan = dict(row["plan"], id=row["id"])
    if generate:
        with st.spinner("正在根据你的时间预算安排任务…"):
            result = api("POST", "/plans/" + selected, json={"duration_weeks": int(duration), "weekly_hours": int(weekly_hours)})
        if result:
            plan = result
            st.session_state["next_saved_plan_id"] = result.get("id")
            st.session_state["active_plan"] = result
            st.session_state["plan"] = result
            st.rerun()
    if not plan:
        active = st.session_state.get("active_plan") or {}
        if active.get("job_category") == selected:
            plan = active
    if not plan:
        empty_state("先安排一个可以做到的开始", "选择准备周期和每周时间，生成你的第一份计划。建议先查看职业分析；没有分析时，会从当前画像出发整理准备任务。")
        if st.button("先看看职业分析", icon=":material/arrow_forward:"):
            go_to("职业分析")
        return
    st.session_state["plan"] = plan
    plan_duration = int(plan.get("duration_weeks") or len(plan.get("weeks", [])) or 4)
    plan_budget = plan.get("weekly_hours", "—")
    total = sum(float(task.get("estimated_hours", 0) or 0) for week in plan.get("weeks", []) for task in week.get("tasks", []))
    section_heading("{0} · 准备路线".format(plan.get("job_name") or job_name(selected)), "调整上方设置后，生成并保存新版本")
    st.markdown('<div class="plan-summary"><div>准备周期<b>{0} 周</b></div><div>每周预算<b>{1} 小时</b></div><div>计划实际安排<b>{2:g} 小时</b></div></div>'.format(plan_duration, html(plan_budget), total), unsafe_allow_html=True)
    render_runtime_state(plan.get("mode"), plan.get("grounding_status", "no_sources"))
    if plan.get("warning"):
        st.warning(plan["warning"])
    elif plan.get("mode") in ("demo", "demo_fallback"):
        st.caption("当前为本地演示计划，不能作为已由模型核验的个性化结论。")
    markdown = api("GET", "/plans/{0}/markdown".format(plan["id"])) if plan.get("id") else None
    if markdown:
        st.download_button("下载 Markdown 计划", markdown["markdown"], file_name="{0}_{1}周职业准备计划.md".format(plan.get("job_name", "岗位"), plan_duration), mime="text/markdown", icon=":material/download:")
    for week in plan.get("weeks", []):
        week_total = sum(float(task.get("estimated_hours", 0) or 0) for task in week.get("tasks", []))
        try:
            budget_number = float(plan_budget)
        except (TypeError, ValueError):
            budget_number = 0
        label, tasks = st.columns([1, 3.5], gap="large")
        with label:
            st.markdown('<div class="week-label">WEEK</div><div class="week-number">{0:02d}</div><div class="week-goal">{1}</div><div class="week-budget">预计 {2:g} / {3} 小时</div>'.format(int(week.get("week", 0) or 0), html(week.get("goal", "本周目标")), week_total, html(plan_budget)), unsafe_allow_html=True)
            if budget_number > 0:
                st.progress(min(1.0, week_total / budget_number))
                if week_total > budget_number:
                    st.warning("此版本超出周预算，请重新生成。")
        with tasks:
            for task_index, task in enumerate(week.get("tasks", [])):
                with st.container(border=True, key="task_{0}_{1}".format(week.get("week", 0), task_index)):
                    st.markdown('<div class="task-title"><b>{0}</b><span>{1} 小时</span></div><p class="task-description">{2}</p><div class="task-criteria">完成标准 · {3}</div>'.format(html(task.get("title", "行动任务")), html(task.get("estimated_hours", "待定")), html(task.get("description", "")), html(task.get("completion_criteria", "待补充"))), unsafe_allow_html=True)
                    render_resources(task.get("learning_resources"))
        st.divider()
    if plan.get("deferred_items"):
        with st.expander("这个周期之后，还可以做"):
            for item in plan["deferred_items"]:
                st.write(item)
    render_sources(plan.get("sources", []))


def main():
    next_page = st.session_state.pop("next_page", None)
    if next_page:
        st.session_state["page_nav"] = next_page
    page = st.session_state.get("page_nav", "今日概览")
    st.sidebar.markdown('<div class="side-brand"><span class="brand-mark">↗</span><div><strong>向前</strong><small>CAREER WORKSPACE</small></div></div><div class="side-label">我的职业规划</div>', unsafe_allow_html=True)
    nav = [("今日概览", "space_dashboard"), ("个人画像", "person_outline"), ("岗位探索", "explore"), ("职业分析", "donut_small"), ("行动计划", "checklist")]
    for title, icon in nav:
        if st.sidebar.button(title, key="nav_" + title, type="primary" if page == title else "secondary", icon=":material/" + icon + ":", use_container_width=True):
            go_to(title)
    try:
        health = requests.request("GET", API_URL + "/health", timeout=3)
        online = health.ok
    except requests.RequestException:
        online = False
    st.session_state["backend_offline"] = not online
    status = api("GET", "/status") if online else None
    profile = api("GET", "/profile") if online else None
    selected = st.session_state.get("job_category")
    if not selected and online:
        dashboard = select_dashboard_state(profile, api("GET", "/plans") or [], [], api("GET", "/analyses") or [])
        selected = dashboard["selected_job"]
        if selected:
            choose_job(selected)
    profile = profile or {}
    has_profile = any(profile.get(key) for key in ("grade", "major", "skills", "experience_text", "interests", "target_city"))
    if has_profile:
        st.sidebar.markdown('<div class="side-context"><span>当前关注方向</span><strong>{0}</strong><p>{1}</p></div>'.format(html(job_name(selected)) if selected else "等待一次新的探索", "可以随时切换，不必急着决定。"), unsafe_allow_html=True)
        model_label = "状态暂不可用"
        if status:
            model_label = "模型已配置" if status.get("mode") == "model" else "本地演示模式"
        retrieval = ("向量检索" if status.get("retrieval_mode") == "vector" else "关键词检索") if status else "资料状态暂不可用"
        st.sidebar.markdown('<div class="side-label">服务状态</div><div class="runtime"><div class="runtime-line"><i class="status-dot {0}"></i>{1}</div><div class="runtime-line"><i class="status-dot {2}"></i>{3}</div><div class="runtime-line"><i class="status-dot {4}"></i>{5}</div></div><div class="side-foot">资料复核状态以具体来源为准。<br>一步一步，找到自己的方向。</div>'.format(
            "" if online else "warn", "本地服务已连接" if online else "本地服务未连接",
            "" if status and status.get("mode") == "model" else "warn", model_label,
            "" if status else "warn", retrieval), unsafe_allow_html=True)
    if online:
        with st.sidebar.expander("导入历史记录", expanded=False):
            visits = [item for item in (api("GET", "/visits") or []) if item["visit_id"] != st.session_state["visit_id"]]
            if visits:
                options = {
                    "{0} · {1} · {2} · {3}".format(
                        format_date(item["updated_at"]),
                        " ".join(part for part in (item["grade"], item["major"]) if part) or "未填写画像",
                        job_name(item["job_category"]) if item["job_category"] else "方向待选",
                        item["visit_id"][-6:],
                    ): item["visit_id"] for item in visits
                }
                choice = st.selectbox("本机已保存的探索", list(options), key="saved_visit_choice")
                if st.button("导入选中记录", key="import_visit", use_container_width=True):
                    activate_visit(options[choice])
            else:
                st.caption("暂无可导入的历史记录。")
    if not online:
        page_header("CAREER WORKSPACE", "工作台正在等待连接", "启动本地服务后，就能继续查看你的画像、分析和计划。")
        st.info("请在项目目录启动后端服务，然后点击重新连接。")
        st.code(".\\.venv\\Scripts\\python.exe -m uvicorn app.api:app --host 127.0.0.1 --port " + API_PORT, language="powershell")
        if st.button("重新连接", type="primary"):
            st.rerun()
        return
    identity = " · ".join(value for value in [profile.get("grade"), profile.get("major")] if value) or "欢迎，新同学"
    with st.container(key="workspace_header"):
        st.markdown('<div class="workspace-topline"><span>向前 / <b>{0}</b></span><span class="topline-badge">{1}</span></div>'.format(html(page), html(identity)), unsafe_allow_html=True)
        if st.button("新建", key="new_visit", icon=":material/add:", use_container_width=False):
            new_visit()
    {"今日概览": overview_page, "个人画像": profile_page, "岗位探索": opportunity_page, "职业分析": analysis_page, "行动计划": plan_page}.get(page, overview_page)()
    st.markdown('<div class="page-foot">向前 · 职业规划　/　基于信息，保持探索。你的选择始终由你决定。</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
