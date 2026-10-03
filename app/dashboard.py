from app.catalog import JOB_BY_ID


def select_dashboard_state(profile, plans, conversations, analyses):
    profile = profile or {}
    has_profile = any(
        profile.get(key)
        for key in ("grade", "major", "skills", "experience_text", "interests", "target_city")
    )
    latest_plan = plans[0] if plans else None
    latest_analysis = analyses[0] if analyses else None
    latest_conversation = conversations[0] if conversations else None
    candidates = [item for item in (latest_plan, latest_analysis) if item]
    newest = None
    if latest_plan and latest_analysis:
        newest = latest_analysis if latest_analysis.get("created_at", "") >= latest_plan.get("created_at", "") else latest_plan
    elif candidates:
        newest = candidates[0]
    selected_job = newest.get("job_category") if newest else None

    if not has_profile:
        next_action = "profile"
    elif not candidates:
        next_action = "explore"
    elif newest is latest_plan:
        next_action = "plan"
    else:
        next_action = "analysis"

    return {
        "has_profile": bool(has_profile),
        "selected_job": selected_job,
        "next_action": next_action,
        "latest_analysis": latest_analysis,
        "latest_plan": latest_plan,
        "latest_conversation": latest_conversation,
    }


def summarize_experience_feedback(feedback):
    known = set(JOB_BY_ID)
    latest = {}
    for item in feedback:
        job = item.get("job_category")
        if job in known and job not in latest:
            latest[job] = {
                "job_category": job,
                "task_status": item.get("task_status") or (
                    "skipped" if item.get("choice") == "skipped" else "started"
                ),
                "interest": item.get("interest"),
                "difficulty": item.get("difficulty"),
                "continue_interest": item.get("continue_interest"),
                "note": item.get("note", ""),
                "created_at": item.get("created_at", ""),
            }
    return latest
