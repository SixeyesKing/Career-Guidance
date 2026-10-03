import json
import logging
import re
from urllib.parse import urlsplit

import requests

from app import db
from app.catalog import JOB_BY_ID
from app.rag import search_knowledge, search_learning_resources, source_status
from app.settings import setting


logger = logging.getLogger(__name__)


def demo_mode():
    return not (setting("LLM_API_KEY") and setting("LLM_MODEL") and setting("LLM_BASE_URL"))


def call_model(messages, json_mode=False, timeout=45):
    api_key = setting("LLM_API_KEY")
    base_url = setting("LLM_BASE_URL").rstrip("/")
    model = setting("LLM_MODEL")
    if not (api_key and base_url and model):
        return None
    endpoint = base_url if base_url.endswith("/v1") else base_url + "/v1"
    payload = {"model": model, "messages": messages, "temperature": 0.3}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    response = requests.post(
        endpoint + "/chat/completions",
        headers={"Authorization": "Bearer " + api_key},
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def profile_summary(profile):
    skills = ", ".join(profile.get("skills", [])) or "暂未填写"
    interests = "、".join(profile.get("interests", [])) or "暂未填写"
    return (
        "年级：{grade}；专业：{major}；技能：{skills}；经历：{experience}；"
        "兴趣：{interests}；每周可投入：{hours} 小时。"
    ).format(
        grade=profile.get("grade") or "未填写",
        major=profile.get("major") or "未填写",
        skills=skills,
        experience=profile.get("experience_text") or "未填写",
        interests=interests,
        hours=profile.get("weekly_hours") or 5,
    )


def fallback_answer(question, profile, job, sources):
    if not sources:
        return "当前知识库没有找到可靠依据。你可以先补充目标岗位资料，或把问题改成岗位职责、技能准备和项目实践方向。"
    skills = profile.get("skills", [])
    skill_note = "你提到的技能包括“{0}”。".format("、".join(skills)) if skills else "你还没有填写已掌握的技能。"
    return (
        "模型服务当前不可用，以下是基于岗位通用介绍生成的本地演示建议，不代表具体企业要求。\n\n"
        "对于“{question}”，{name}常见工作包括{work}。{skill_note}"
        "可以先完成一个范围明确的小练习，记录实现过程、结果和仍需确认的问题。"
        "请结合下方资料来源核对时效性与复核状态。"
    ).format(
        question=question,
        name=job["name"],
        work="、".join(job["daily_work"][:2]),
        skill_note=skill_note,
    )


def answer_question(question, job_category, conversation_id=None):
    if job_category not in JOB_BY_ID:
        raise ValueError("请选择有效岗位")
    profile = db.get_profile()
    sources = search_knowledge(question, job_category)
    job = JOB_BY_ID[job_category]
    source_block = "\n\n".join(
        "[资料 {i}] {title}\n来源：{source_name}\n链接：{source_url}\n更新时间：{updated_at}\n复核状态：{review_status}\n内容：{content}".format(
            i=i + 1,
            title=s.get("title", "资料"),
            source_name=s.get("source_name", "来源未提供"),
            source_url=s.get("source_url") or "暂无链接",
            updated_at=s.get("updated_at", "未提供"),
            review_status=s.get("review_status", "not_reviewed"),
            content=s.get("content", ""),
        )
        for i, s in enumerate(sources)
    )
    prompt = (
        "你是面向软件工程学生的职业探索助手。结合用户画像和提供的资料回答。"
        "区分资料事实和一般建议；不得编造公司招聘要求、薪资或来源。明确保留每条资料标注的复核状态；"
        "未复核内容不能表述为已确认事实，招聘信息须提醒用户查看来源页面。"
        "如果资料不足，明确说无法从当前资料确认。回答清楚、具体、适合大三学生理解。\n\n"
        "用户画像：{profile}\n目标岗位：{job}\n资料：\n{sources}"
    ).format(profile=profile_summary(profile), job=job["name"], sources=source_block or "当前无检索资料")
    history = []
    if conversation_id:
        history = [
            {"role": message["role"], "content": message["content"]}
            for message in db.get_messages(conversation_id, 8)
        ][-6:]
    model_warning = ""
    try:
        answer = call_model([{"role": "system", "content": prompt}] + history + [{"role": "user", "content": question}])
        mode = "model" if answer else "demo"
    except requests.RequestException as exc:
        answer = None
        mode = "demo_fallback"
        model_warning = "模型服务暂时无法连接，以下为本地演示回答。"
    if answer is None:
        answer = fallback_answer(question, profile, job, sources)
    if conversation_id is None:
        conversation_id = db.create_conversation(job_category)
    db.add_message(conversation_id, "user", question)
    db.add_message(conversation_id, "assistant", answer, sources)
    return {
        "conversation_id": conversation_id,
        "answer": answer,
        "sources": sources,
        "grounding_status": source_status(sources),
        "mode": mode,
        "warning": model_warning,
    }


def _json_from_text(text):
    if not text:
        return None
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except ValueError:
        return None


def valid_analysis(data):
    if not isinstance(data, dict):
        return False
    for key in ("known_basics", "to_confirm", "actions"):
        value = data.get(key)
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            return False
    return True


def normalize_analysis(result):
    result = dict(result or {})
    if "known_basics" not in result:
        result["known_basics"] = result.get("strengths", [])
    if "to_confirm" not in result:
        legacy = list(result.get("uncertainties", []))
        legacy.extend(
            "旧版分析曾提到，需结合当前画像重新确认：" + item
            for item in result.get("gaps", [])
        )
        result["to_confirm"] = legacy
    result.setdefault("actions", [])
    result.setdefault("sources", [])
    result.setdefault("grounding_status", source_status(result["sources"]))
    result.setdefault("mode", "demo")
    result.setdefault("warning", "")
    return result


def valid_weeks(weeks, weekly_budget, duration_weeks=4):
    if not isinstance(weeks, list) or len(weeks) != duration_weeks:
        return False
    for expected_week, week in enumerate(weeks, 1):
        if (
            not isinstance(week, dict)
            or week.get("week") != expected_week
            or not isinstance(week.get("goal"), str)
            or not week["goal"].strip()
        ):
            return False
        tasks = week.get("tasks")
        if not isinstance(tasks, list) or not tasks:
            return False
        total = 0
        for task in tasks:
            if not isinstance(task, dict):
                return False
            if not all(isinstance(task.get(key), str) and task[key].strip() for key in ("title", "description", "completion_criteria")):
                return False
            try:
                hours = float(task.get("estimated_hours"))
            except (TypeError, ValueError):
                return False
            if hours < 0:
                return False
            total += hours
        if total > weekly_budget:
            return False
    return True


def build_analysis(job_category):
    if job_category not in JOB_BY_ID:
        raise ValueError("请选择有效岗位")
    profile = db.get_profile()
    job = JOB_BY_ID[job_category]
    sources = search_knowledge(job["name"] + " 技能要求 岗位能力", job_category)
    feedback = db.list_feedback()
    feedback_context = [
        "体验自述：兴趣 {interest}/5，主观难度 {difficulty}/5，继续意愿 {continue_interest}/5，任务状态 {task_status}。"
        .format(
            interest=item.get("interest") or "未填写",
            difficulty=item.get("difficulty") or "未填写",
            continue_interest=item.get("continue_interest") or "未填写",
            task_status=item.get("task_status") or item.get("choice"),
        )
        for item in feedback if item.get("job_category") == job_category
    ][:3]
    prompt = (
        "根据用户明确填写的画像和资料生成职业分析，只返回 JSON 对象，字段为 known_basics、to_confirm、actions。"
        "三个字段都是字符串数组。known_basics 只写用户明确提供的信息；未提及、无法判断的能力只能列在 to_confirm，"
        "不能把未知描述为能力不足。体验反馈是主观感受，不是技术能力证据。不得输出匹配分数或录用概率。"
        "资料不足时说明不确定，不得编造岗位事实或来源。引用资料可能待复核或未标注复核状态，须保留其状态，不得声称均已核实。\n用户画像：{profile}\n岗位：{job}\n"
        "常见技能参考（并非已核验招聘要求）：{skills}\n用户体验自述：{feedback}\n资料：{sources}"
    ).format(
        profile=profile_summary(profile), job=job["name"], skills="、".join(job["skills"]),
        feedback="；".join(feedback_context) or "暂无体验反馈",
        sources="\n".join(
            "{title}；来源：{source_name}；链接：{source_url}；更新时间：{updated_at}；复核状态：{review_status}。{content}".format(
                title=source.get("title", "资料"),
                source_name=source.get("source_name", "来源未提供"),
                source_url=source.get("source_url") or "暂无链接",
                updated_at=source.get("updated_at", "未提供"),
                review_status=source.get("review_status", "not_reviewed"),
                content=source.get("content", ""),
            )
            for source in sources
        ) or "无可靠资料",
    )
    result = None
    warning = ""
    configured_model = not demo_mode()
    try:
        result = _json_from_text(call_model([{"role": "system", "content": prompt}], json_mode=True))
    except requests.RequestException:
        warning = "模型服务暂时无法连接，当前显示本地演示分析。"
    if not valid_analysis(result):
        if configured_model and not warning:
            warning = "模型返回内容格式无效，当前显示本地演示分析。"
        known = []
        if profile.get("major"):
            known.append("专业：" + profile["major"])
        if profile.get("skills"):
            known.append("已接触技术：" + "、".join(profile["skills"]))
        if profile.get("experience_text"):
            known.append("已记录课程或项目经历，具体负责内容仍需确认")
        result = {
            "known_basics": known,
            "to_confirm": [
                "目前还不了解你在项目中具体负责的内容和技能熟练程度",
                "当前示例资料不能代表真实招聘要求",
            ],
            "actions": ["选一个已做过的课程或个人项目，记录你负责的功能、技术选择和遇到的问题"],
        }
    result["sources"] = sources
    result["grounding_status"] = source_status(sources)
    result["mode"] = "demo_fallback" if warning and configured_model else (
        "demo" if demo_mode() else "model"
    )
    result["warning"] = warning
    result["job_category"] = job_category
    db.save_analysis(job_category, result)
    return result


def _fallback_weeks(job, duration_weeks, weekly_budget):
    task_bank = [
        ("梳理项目经历", "写清项目目标、你负责的部分、使用的技术和遇到的问题。", 1.5,
         "形成一段包含个人职责和结果的项目记录。"),
        ("完成一个岗位相关小实践", "围绕 {0} 完成一个范围明确的小功能或练习。".format(job["skills"][0]), 2.0,
         "留下可运行或可展示的成果，并写明实现过程。"),
        ("检查实践结果", "为刚完成的实践补充验证步骤，记录一个问题及处理方式。", 1.5,
         "形成可重复执行的验证记录。"),
        ("练习项目表达", "用简短语言说明项目目标、个人工作和一次技术选择。", 1.0,
         "完成约两分钟介绍，并列出仍需确认的问题。"),
    ]
    if duration_weeks == 1:
        tasks = [{
            "week": 1,
            "goal": "聚焦最重要的准备事项",
            "tasks": [{
                "title": "整理项目经历并练习表达",
                "description": "优先梳理一个代表性项目的目标、个人职责、技术选择和结果；再练习简短介绍。",
                "estimated_hours": min(weekly_budget, 2.0),
                "completion_criteria": "形成一段两分钟项目介绍，并列出一个可继续补强的实践问题。",
            }],
        }]
        deferred = [
            "增加一个岗位相关的小实践并留下可展示成果",
            "为实践补充验证记录并复盘结果",
        ]
        return tasks, deferred

    weeks = []
    for index in range(duration_weeks):
        title, description, estimate, criteria = task_bank[min(index, len(task_bank) - 1)]
        if index >= len(task_bank):
            title = "深化岗位实践与复盘"
            description = "在前面成果基础上补充一项小改进，记录取舍并复查结果。"
            criteria = "形成一次改进记录和后续问题清单。"
        weeks.append({
            "week": index + 1,
            "goal": ["梳理已有基础", "完成岗位实践", "验证实践结果", "整理并表达成果"][min(index, 3)],
            "tasks": [{
                "title": title,
                "description": description,
                "estimated_hours": min(weekly_budget, estimate),
                "completion_criteria": criteria,
            }],
        })
    return weeks, []


def _attach_learning_resources(weeks, job_category):
    fields = (
        "recommendation_hint",
        "language",
        "access_note",
        "review_status",
        "updated_at",
    )
    for week in weeks:
        for task in week.get("tasks", []):
            query = " ".join((
                job_category,
                task.get("title", ""),
                task.get("description", ""),
                task.get("completion_criteria", ""),
            ))
            try:
                matches = search_learning_resources(query, job_category, limit=2)
            except Exception as exc:
                logger.warning("Learning resource retrieval failed: %s", type(exc).__name__)
                matches = []
            resources = []
            for match in matches:
                url = str(match.get("source_url") or "").strip()
                try:
                    parsed_url = urlsplit(url)
                except ValueError:
                    continue
                if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
                    continue
                resource = {
                    "id": str(match.get("source_id") or match.get("id") or ""),
                    "title": str(match.get("title") or "学习资料"),
                    "source_name": str(match.get("source_name") or "来源未提供"),
                    "source_url": url,
                }
                resource.update({key: str(match.get(key) or "") for key in fields})
                resources.append(resource)
            task["learning_resources"] = resources[:2]


def build_plan(job_category, duration_weeks=4, weekly_hours=None):
    if job_category not in JOB_BY_ID:
        raise ValueError("请选择有效岗位")
    if not 1 <= int(duration_weeks) <= 12:
        raise ValueError("准备周期必须为 1 至 12 周")
    profile = db.get_profile()
    job = JOB_BY_ID[job_category]
    analysis = normalize_analysis(db.latest_analysis(job_category) or build_analysis(job_category))
    hours = int(weekly_hours if weekly_hours is not None else (profile.get("weekly_hours") or 5))
    if not 1 <= hours <= 40:
        raise ValueError("每周准备时间必须为 1 至 40 小时")
    weeks = None
    deferred_items = []
    warning = ""
    configured_model = not demo_mode()
    try:
        raw = call_model([
            {
                "role": "system",
                "content": (
                    "只生成 JSON 对象，含 weeks 和 deferred_items 数组。weeks 只能包含下列周次编号且数量必须完全一致：{0}。"
                    "不得添加其他周次，不得把准备周期外的事项加入 weeks。"
                    "每周含 week、goal、tasks，tasks 只放 1 个核心任务；任务含 title、description、estimated_hours、completion_criteria。"
                    "week 必须是从 1 开始的 JSON 整数，estimated_hours 必须是 JSON 数字而非带单位的文本。"
                    "estimated_hours 不得超过每周预算；可以低于预算，不要为排满时间增加低优先级任务。"
                    "任务要对应已知基础或待确认项，1 周时只保留关键任务，把未安排的重要内容列入 deferred_items。"
                    "不编造招聘时限、岗位来源或引用；不要输出 Markdown 或 JSON 以外的文字。"
                ).format(", ".join(str(week) for week in range(1, duration_weeks + 1))),
            },
            {
                "role": "user",
                "content": "岗位：{0}\n准备周期：{1} 周\n画像：{2}\n每周预算：{3} 小时\n差距：{4}".format(
                    job["name"], duration_weeks, profile_summary(profile), hours,
                    "；".join(analysis.get("to_confirm", []) + analysis.get("actions", [])),
                ),
            },
        ], json_mode=True, timeout=90)
        parsed = _json_from_text(raw)
        candidate_weeks = parsed.get("weeks") if isinstance(parsed, dict) else None
        if isinstance(candidate_weeks, list) and len(candidate_weeks) > duration_weeks:
            candidate_weeks = candidate_weeks[:duration_weeks]
            extra_note = "模型多返回的准备周期外周次未纳入本计划。"
            returned_deferred = parsed.get("deferred_items")
            deferred_items = list(returned_deferred) if isinstance(returned_deferred, list) and all(
                isinstance(item, str) for item in returned_deferred
            ) else []
            deferred_items.append(extra_note)
        if valid_weeks(candidate_weeks, hours, duration_weeks):
            weeks = candidate_weeks
            if isinstance(parsed.get("deferred_items"), list) and all(
                isinstance(item, str) for item in parsed["deferred_items"]
            ) and len(candidate_weeks) == len(parsed.get("weeks", [])):
                deferred_items = parsed["deferred_items"]
    except requests.Timeout:
        warning = "模型生成计划超时，当前使用本地演示计划。"
    except requests.ProxyError:
        warning = "连接模型服务的网络代理失败，请检查本机代理或模型服务网络状态；当前使用本地演示计划。"
    except requests.RequestException:
        warning = "模型接口请求失败，当前使用本地演示计划。"
    if weeks is None:
        if configured_model and not warning:
            warning = "模型返回的计划格式或时间预算不符合要求，当前使用本地演示计划。"
        weeks, deferred_items = _fallback_weeks(job, duration_weeks, hours)
    _attach_learning_resources(weeks, job_category)
    plan = {
        "job_category": job_category,
        "job_name": job["name"],
        "duration_weeks": duration_weeks,
        "weekly_hours": hours,
        "weeks": weeks,
        "deferred_items": deferred_items,
        "sources": analysis.get("sources", []),
        "grounding_status": analysis.get("grounding_status", "no_sources"),
        "mode": "demo_fallback" if warning and configured_model else ("demo" if demo_mode() else "model"),
        "warning": warning,
    }
    plan_id = db.save_plan(job_category, plan)
    plan["id"] = plan_id
    return plan


def plan_as_markdown(plan, profile):
    duration_weeks = int(plan.get("duration_weeks") or 4)
    mode_label = {
        "demo": "本地演示内容",
        "demo_fallback": "模型异常后的本地演示内容",
        "model": "模型生成，内容需结合来源核验",
    }.get(plan.get("mode"), "状态未知")
    lines = [
        "# {0} 周职业准备计划".format(duration_weeks),
        "",
        "- 目标岗位：{0}".format(plan.get("job_name", "")),
        "- 准备周期：{0} 周".format(duration_weeks),
        "- 每周可投入：{0} 小时".format(plan.get("weekly_hours", "")),
        "- 生成方式：{0}".format(mode_label),
        "- 资料状态：{0}".format(plan.get("grounding_status", "no_sources")),
        "",
        "## 个人情况",
        "",
        profile_summary(profile),
    ]
    for week in plan.get("weeks", []):
        lines.extend(["", "## 第 {0} 周：{1}".format(week.get("week", ""), week.get("goal", "")), ""])
        for task in week.get("tasks", []):
            lines.extend([
                "### {0}".format(task.get("title", "行动任务")),
                "",
                task.get("description", ""),
                "",
                "- 预计用时：{0} 小时".format(task.get("estimated_hours", "待调整")),
                "- 完成标准：{0}".format(task.get("completion_criteria", "待补充")),
            ])
            resources = task.get("learning_resources") or []
            if resources:
                lines.extend(["", "**学习资料**", ""])
                for resource in resources:
                    title = resource.get("title", "学习资料")
                    url = resource.get("source_url", "")
                    source_name = resource.get("source_name", "来源未提供")
                    detail = resource.get("recommendation_hint", "")
                    notes = [resource.get("language", ""), resource.get("access_note", "")]
                    notes = [note for note in notes if note]
                    suffix = "；".join(notes)
                    description = " - {0}：{1}".format(source_name, detail) if detail else " - " + source_name
                    if suffix:
                        description += "（{0}）".format(suffix)
                    lines.append("- [{0}]({1}){2}".format(title, url, description))
    deferred_items = plan.get("deferred_items", [])
    if deferred_items:
        lines.extend(["", "## 本周期未安排的后续事项", ""])
        lines.extend("- " + item for item in deferred_items)
    sources = plan.get("sources", [])
    lines.extend(["", "## 参考资料", ""])
    if not sources:
        lines.append("暂未找到可靠资料来源。")
    for source in sources:
        suffix = "（示例资料）" if source.get("is_placeholder") else ""
        url = source.get("source_url") or "暂无链接"
        lines.append("- {0}{1}：{2}，更新时间 {3}".format(source.get("title", "资料"), suffix, url, source.get("updated_at", "未提供")))
    return "\n".join(lines).strip() + "\n"
