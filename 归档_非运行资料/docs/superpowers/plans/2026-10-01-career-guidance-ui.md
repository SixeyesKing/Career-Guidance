# Career Guidance UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved daily-use UI, clarify evidence and experience states, and support user-configurable 1–12 week career preparation plans.

**Architecture:** Keep Streamlit as the presentation layer and FastAPI/SQLite as the source of persisted state. Add a dashboard view over existing profile, analysis, conversation and plan records; extend experience feedback additively for completion status; pass plan duration and weekly hours through the API into validation, persistence and Markdown export. Preserve the current single-profile local MVP and existing stored data.

**Tech Stack:** Python 3.9+, Streamlit, FastAPI, Pydantic, SQLite, unittest.

**Spec:** `docs/superpowers/specs/2026-10-01-career-guidance-ui-design.md`

## Global Constraints

- The UI is for students' repeated daily use, with a clear route suitable for a course demo.
- Keep three role directions: backend development, frontend development and test development.
- Unknown profile details mean “needs confirmation,” not “lacks ability.”
- Experience tasks remain optional and do not block role analysis.
- Experience feedback uses separate 1–5 interest, subjective difficulty and continue-intent ratings; never combine them into a score or ranking.
- Preparation duration is 1–12 weeks, default 4; weekly preparation budget is 1–40 hours and excludes classes and coursework.
- Per-week task estimates must not exceed the selected weekly budget; planned hours may remain below the budget.
- Label placeholder sources and local fallback output accurately; model mode does not imply real-source grounding.
- Preserve previously saved profiles, feedback, analyses, conversations and plans.
- Do not import the recruitment workbook or add live crawling in this UI implementation.

## Review Focus

- Empty or partially completed profiles must still reach role exploration; unmentioned experience must appear as unknown. Pin this in dashboard and analysis tests.
- Legacy SQLite feedback rows and saved plan JSON must remain readable after additive schema/data changes. Pin this in database compatibility tests.
- Plan boundaries (1 week, 12 weeks, 1 hour/week, and 40 hours/week) must generate valid plans without exceeding weekly budgets. Pin this in service tests.
- Invalid model JSON, request failures and fallback output must never be presented as valid personalized model output. Pin this in service/API mode tests.
- Switching role, plan duration or weekly budget must not display stale analysis or overwrite an earlier saved plan. Pin this in API and UI state tests.

---

### Task 1: Extend persisted experience and analysis records

**Files:**
- Modify: `app/db.py`
- Modify: `app/api.py`
- Create: `tests/__init__.py`
- Create: `tests/test_db.py`
- Create: `tests/test_api_feedback.py`

**Interfaces:**
- Extend `db.save_feedback(job_category, choice, interest=None, difficulty=None, continue_interest=None, note="", task_status=None)` while retaining the existing `choice` values `started` and `skipped` for old callers.
- Add `db.list_analyses(limit=20)` returning newest-first rows with decoded `result` JSON.
- Add `GET /analyses` returning the latest saved analysis records.
- Extend `FeedbackInput` with `task_status`, accepting `started`, `completed`, or `skipped`; existing requests without it remain valid and infer `skipped` from `choice="skipped"`, otherwise `started`.
- `db.list_feedback()` returns legacy `choice="skipped"` rows as `task_status="skipped"` even when the additive migration populated the column's default.
- `db.save_feedback()` infers `task_status="skipped"` when old callers pass `choice="skipped"` and omit `task_status`; otherwise omitted status defaults to `started`.

- [ ] **Step 1: Add database compatibility tests**

Add `test_init_db_adds_task_status_without_rebuilding_existing_rows`, `test_list_feedback_infers_legacy_skipped_state`, and `test_list_analyses_decodes_json_newest_first`. Assert the migration preserves a preexisting profile/message, maps legacy `choice="skipped"` to returned status `skipped`, and leaves other legacy feedback as `started`.

- [ ] **Step 2: Run the focused database and API tests and confirm they fail**

Run: `python -m unittest tests.test_db tests.test_api_feedback -v`
Expected: FAIL because task status, analysis listing and the new feedback request field are not implemented.

- [ ] **Step 3: Add an additive SQLite migration**

In `db.init_db()`, inspect `PRAGMA table_info(experience_feedback)` and add `task_status TEXT NOT NULL DEFAULT 'started' CHECK(task_status IN ('started','completed','skipped'))` only when absent. Do not rebuild or drop the existing table. Update `save_feedback` and `list_feedback` to persist and return the status.

- [ ] **Step 4: Add analysis listing and API compatibility**

Implement `db.list_analyses(limit=20)` by selecting newest rows and JSON-decoding `result_json`. Add `GET /analyses`. Extend feedback validation so skipped feedback has no required ratings and started/completed feedback accepts optional 1–5 ratings.

- [ ] **Step 5: Add API feedback tests and run focused tests**

Add `test_feedback_defaults_old_payload_state`, `test_feedback_accepts_each_task_status`, and `test_feedback_rejects_out_of_range_rating`. Run: `python -m unittest tests.test_db tests.test_api_feedback -v`
Expected: PASS; existing legacy rows remain accessible.

- [ ] **Step 6: Commit the compatible feedback and analysis API changes**

```bash
git add app/db.py app/api.py tests/test_db.py tests/test_api_feedback.py
git commit -m "feat: preserve experience task states"
```

### Task 2: Make analysis distinguish known information from unknowns

**Files:**
- Modify: `app/services.py`
- Modify: `app/db.py`
- Create: `tests/test_analysis.py`

**Interfaces:**
- Standardize newly generated analysis as `known_basics: list[str]`, `to_confirm: list[str]`, `actions: list[str]`, `sources: list[dict]`, `grounding_status: str`, `mode: str`, and `warning: str`.
- Continue reading legacy analysis JSON with `strengths`, `gaps`, `actions` and `uncertainties`; normalize it for display without rewriting old database rows.
- Add `normalize_analysis(result: dict) -> dict` in `app/services.py`; map legacy `strengths` to `known_basics` and legacy `uncertainties` plus `gaps` to `to_confirm`. Prefix legacy gaps with “旧版分析曾提到，需结合当前画像重新确认：” so they are not shown as verified user deficiencies.
- Add `normalize_analysis(result: dict) -> dict` in `app/services.py`; map legacy `strengths` to `known_basics` and legacy `uncertainties` to `to_confirm`, retaining legacy `gaps` as explanatory context instead of treating them as user-verified facts.

- [ ] **Step 1: Write analysis behavior tests**

Add `test_empty_profile_returns_unknowns_not_deficiencies`, `test_partial_profile_keeps_unmentioned_skills_unconfirmed`, `test_explicit_project_experience_is_known`, and `test_legacy_analysis_normalizes_without_rewriting_saved_json`. Assert missing profile data is classified under `to_confirm` and legacy gaps receive the unconfirmed prefix.

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run: `python -m unittest tests.test_analysis -v`
Expected: FAIL because analysis still emits the legacy strengths/gaps structure and does not classify unknowns explicitly.

- [ ] **Step 3: Update analysis parsing and prompting**

Update `valid_analysis()` and `build_analysis()` in `app/services.py` to request and validate `known_basics`, `to_confirm` and `actions`. Include saved experience feedback only as subjective exploration context; never treat its ratings as demonstrated technical ability. Add `test_invalid_analysis_output_is_labeled_demo_fallback` and `test_model_request_failure_is_labeled_demo_fallback`; when parsing fails or the model is unavailable, return accurate demo mode and warning values.

- [ ] **Step 4: Normalize saved analyses for display and verify**

Implement the named normalization helper and use it in analysis listing and the UI. Preserve the original JSON when reading older records. Run: `python -m unittest tests.test_analysis -v`
Expected: PASS for empty, partial, complete and legacy profiles.

- [ ] **Step 5: Commit the analysis contract**

```bash
git add app/services.py app/db.py tests/test_analysis.py
git commit -m "feat: separate known and unconfirmed profile details"
```

### Task 3: Support configurable plan duration, budget and export

**Files:**
- Modify: `app/services.py`
- Modify: `app/api.py`
- Modify: `app/db.py`
- Create: `tests/test_plans.py`

**Interfaces:**
- Add `PlanInput(duration_weeks: int = 4, weekly_hours: Optional[int] = None)` with `duration_weeks` constrained to 1–12 and `weekly_hours` constrained to 1–40.
- Change service signature to `build_plan(job_category: str, duration_weeks: int = 4, weekly_hours: Optional[int] = None) -> dict`; omitted weekly hours use the saved profile value.
- Change `valid_weeks(weeks, weekly_budget, duration_weeks=4)` to validate the requested number of weeks and each week's total.
- Persist `duration_weeks` and the selected `weekly_hours` in each plan JSON; older plans without duration metadata load as four-week plans.
- Store `deferred_items: list[str]` in plan JSON (empty when none) for high-priority needs omitted from a short cycle; the Markdown export includes this section when non-empty. The model response uses `{ "weeks": [...], "deferred_items": [...] }`.

- [ ] **Step 1: Write plan service and route tests**

Add `test_plan_accepts_one_and_twelve_weeks`, `test_plan_uses_profile_budget_when_request_omits_hours`, `test_plan_rejects_week_over_budget`, `test_plan_rejects_wrong_week_count`, `test_invalid_model_plan_is_labeled_demo_fallback`, `test_regeneration_saves_new_plan_without_mutating_previous`, `test_legacy_plan_defaults_to_four_weeks`, and `test_markdown_export_includes_duration_budget_and_deferred_items`. Cover 1- and 12-week durations, 1- and 40-hour budgets, an omitted request body, and assert invalid model output is not labeled `model`.

- [ ] **Step 2: Run the plan tests and confirm they fail**

Run: `python -m unittest tests.test_plans -v`
Expected: FAIL because the current service always generates four weeks and has no request parameters.

- [ ] **Step 3: Extend the plans API without breaking old clients**

Allow `POST /plans/{job_category}` with an optional `PlanInput` body. A request without a body uses duration 4 and the saved profile weekly-hours value. Return 422 for values outside the declared bounds.

- [ ] **Step 4: Generate and validate the requested number of weeks**

Update model instructions and `valid_weeks` to use the requested duration. Validate each week has its exact sequence number, non-empty `goal`, and at least one task; each task must have non-empty `title`, `description`, `completion_criteria` and a non-negative numeric `estimated_hours`; each weekly sum must be within budget. Replace the fixed four-item fallback with a deterministic 1–12-week fallback that distributes a small number of role-relevant tasks across available weeks, prioritizes project evidence and preparation, includes review when duration permits, places omitted priorities in `deferred_items`, and never fills unused budget just to consume time. Any rejected model result must be labeled `demo_fallback`.

- [ ] **Step 5: Persist metadata and make Markdown duration-aware**

Store selected duration and weekly hours on every new plan. Change export heading to `# {duration_weeks} 周职业准备计划`, include both cycle and weekly budget, and retain each source's placeholder status. Legacy plans export as four-week plans.

- [ ] **Step 6: Run plan tests**

Run: `python -m unittest tests.test_plans -v`
Expected: PASS; every generated week stays within budget and exported metadata matches saved settings.

- [ ] **Step 7: Commit configurable plan generation and export**

```bash
git add app/services.py app/api.py app/db.py tests/test_plans.py
git commit -m "feat: support configurable preparation plans"
```

### Task 4: Build the daily-use dashboard and profile onboarding entry

**Files:**
- Modify: `app/ui.py`
- Modify: `app/api.py`
- Modify: `app/db.py`
- Create: `app/dashboard.py`
- Create: `tests/test_dashboard_data.py`

**Interfaces:**
- Add a dashboard renderer `overview_page()` in `app/ui.py` and make `今日概览` the default navigation page.
- Add `select_dashboard_state(profile: dict, plans: list[dict], conversations: list[dict], analyses: list[dict]) -> dict` in a new `app/dashboard.py`. Plan rows contain `created_at`, `job_category` and decoded `plan`; analysis rows contain `created_at`, `job_category` and decoded `result`; conversation rows contain `created_at`, `job_category` and `last_message`. Return `has_profile`, `selected_job`, `next_action`, `latest_analysis`, `latest_plan` and `latest_conversation`. Set `selected_job` from the newest analysis or plan by `created_at`.
- Dashboard data uses `GET /profile`, `GET /jobs`, `GET /plans`, `GET /conversations`, and `GET /analyses`.
- `has_profile` is true when any of `grade`, `major`, `skills`, `experience_text`, `interests` or `target_city` is non-empty; the default `weekly_hours=5` alone does not count as a completed profile. A missing or partial profile shows a profile-start action. A returning user sees next-step links, selected role, weekly budget, recent saved analysis/conversation, and role shortcuts.

- [ ] **Step 1: Add dashboard data selection tests**

Add `test_empty_profile_selects_profile_entry`, `test_profile_with_no_activity_selects_role_exploration`, `test_latest_analysis_selects_analysis_action`, `test_latest_plan_selects_plan_action`, `test_dashboard_keeps_recent_conversation_available`, and `test_dashboard_does_not_create_progress_percentage`. Use fixed timestamps and assert `selected_job` follows the newest saved analysis or plan.

- [ ] **Step 2: Run the dashboard tests and confirm they fail**

Run: `python -m unittest tests.test_dashboard_data -v`
Expected: FAIL because no dashboard route data selector or overview page exists.

- [ ] **Step 3: Add `select_dashboard_state()` in `app/dashboard.py`**

Implement the pure selector with the exact return keys above. `next_action` is one of `profile`, `explore`, `plan` or `analysis`: choose `profile` when the profile is empty; `explore` when no analysis or plan exists; otherwise choose whichever of the newest analysis or plan for `selected_job` has the latest `created_at`, using `analysis` if timestamps tie. Keep missing records as `None` and avoid invented progress metrics.

- [ ] **Step 4: Add Today Overview navigation and onboarding state**

Add `今日概览` to navigation. New users see “开始填写个人画像”; clicking it navigates to the existing profile page. After profile save, return to the dashboard and offer role exploration. Returning users see continue-analysis or continue-plan actions based on saved records. Add the note that weekly time excludes classes and coursework to the profile input and dashboard display. Keep the desktop sidebar/main-content layout and collapse the sidebar and content cards to a single column at narrow widths.

- [ ] **Step 5: Run dashboard tests**

Run: `python -m unittest tests.test_dashboard_data -v`
Expected: PASS for first-use and returning-user states.

- [ ] **Step 6: Commit the daily dashboard and onboarding entry**

```bash
git add app/dashboard.py app/ui.py app/api.py app/db.py tests/test_dashboard_data.py
git commit -m "feat: add daily career guidance dashboard"
```

### Task 5: Refine role exploration and experience feedback UI

**Files:**
- Modify: `app/ui.py`
- Modify: `app/dashboard.py`
- Modify: `tests/test_dashboard_data.py`

**Interfaces:**
- Keep the three job cards and `starter_task` definitions from `app/catalog.py`.
- Feedback submission uses `POST /experience-feedback` with `job_category`, `choice`, `task_status`, `interest`, `difficulty`, `continue_interest`, and `note`.
- Add `summarize_experience_feedback(feedback: list[dict]) -> dict` in `app/dashboard.py`; it returns the newest row per known job ID, preserves three independent ratings and task status, and never computes a combined score or rank.

- [ ] **Step 1: Add validation tests for feedback states**

Add `test_feedback_summary_keeps_latest_feedback_per_role`, `test_feedback_summary_preserves_independent_ratings`, `test_feedback_summary_has_no_aggregate_score_or_rank`, and `test_feedback_summary_handles_skipped_state`. Assert ratings remain separate fields and all three task states are visible.

- [ ] **Step 2: Run focused feedback tests and confirm the new cases fail**

Run: `python -m unittest tests.test_dashboard_data -v`
Expected: FAIL because experience feedback is not summarized by role yet.

- [ ] **Step 3: Update experience task interaction**

In `opportunity_page()`, keep experience optional and add clear “暂不体验，直接继续” language. After showing the task, collect interest, subjective difficulty and continue intent as separate 1–5 values; label the difficulty anchors 1=很轻松, 3=有挑战但能完成, 5=非常吃力. Let the user save feedback as started-but-not-completed or completed after trying the task. Save skipped state without requiring ratings.

- [ ] **Step 4: Show saved experience summaries without ranking roles**

Use `GET /experience-feedback` and `summarize_experience_feedback()` to show the latest feedback per role as separate ratings and task state. Any text summary must describe interest, difficulty and willingness independently; do not calculate an aggregate score or order roles by feedback.

- [ ] **Step 5: Re-run feedback tests**

Run: `python -m unittest tests.test_api_feedback tests.test_dashboard_data -v`
Expected: PASS for the three states and rating bounds.

- [ ] **Step 6: Commit the role exploration and optional feedback UI**

```bash
git add app/ui.py app/dashboard.py tests/test_dashboard_data.py
git commit -m "feat: clarify optional role experience feedback"
```

### Task 6: Align analysis, plans and app states with the approved design

**Files:**
- Modify: `app/ui.py`
- Modify: `app/services.py`
- Modify: `README.md`
- Create: `tests/test_ui_contracts.py`
- Modify: `docs/superpowers/specs/2026-09-30-ai-career-guidance-design.md`
- Modify: `docs/superpowers/specs/2026-10-01-career-guidance-ui-design.md`
- Modify: `项目计划书.md`

**Interfaces:**
- Analysis view consumes normalized analysis keys `known_basics`, `to_confirm`, `actions`, `sources`, `grounding_status`, `mode`, and `warning`.
- Plan view posts `{ "duration_weeks": int, "weekly_hours": int }` and consumes matching plan metadata and a variable-length `weeks` list.
- Plan history continues to use `GET /plans`; older rows without duration metadata remain readable as four-week plans.
- The view model helper `build_analysis_view(result: dict) -> dict` in `app/ui.py` uses `normalize_analysis()` and returns separate `known_basics`, `to_confirm`, `actions`, `sources`, `grounding_status`, `mode` and `warning` fields.

- [ ] **Step 1: Add user-visible state contract tests**

Add `test_analysis_view_labels_placeholder_source`, `test_analysis_view_reports_no_sources`, `test_analysis_view_separates_mode_from_grounding`, `test_analysis_view_normalizes_legacy_result`, `test_analysis_view_resets_state_on_role_switch`, `test_plan_view_reads_legacy_four_week_plan`, and `test_plan_view_accepts_one_and_twelve_week_plans`. Keep tests focused on `build_analysis_view()` and plan/dashboard state helpers, not brittle full-page HTML snapshots.

- [ ] **Step 2: Run the UI contract tests and confirm they fail**

Run: `python -m unittest tests.test_ui_contracts -v`
Expected: FAIL because the new analysis and variable-duration view helpers are not implemented.

- [ ] **Step 3: Implement analysis view sections**

In `analysis_page()`, render known basics, items to confirm, concrete actions, analysis references and continuing chat as distinct sections. Display “未知不等于不足”; never title unknowns as missing skills. Show model mode and grounding/source state independently. Keep changing roles from showing another role's analysis or chat state.

- [ ] **Step 4: Implement configurable plan controls and history**

In `plan_page()`, add `st.number_input` controls with duration range 1–12/default 4 and weekly-hours range 1–40/default from the profile; provide quick buttons for 1, 2, 4 and 8 weeks. Post both values to the plan API. Display each week's estimated total against budget, task completion criteria, sources, any `deferred_items`, and Markdown download. Retain access to plans generated with previous settings.

- [ ] **Step 5: Make status copy reflect actual output**

Distinguish model mode from source grounding in analysis, chat and plan screens. For API/network errors or invalid JSON fallback, display the returned fallback warning and label demo content; do not call it personalized model output. Show placeholder and empty-source states without fabricated links.

- [ ] **Step 6: Update README setup and product behavior**

Update `README.md` to describe the five destinations, configured Embedding capability as environment-dependent, current placeholder-data status, and the configurable 1–12-week plan.

- [ ] **Step 7: Run the full standard-library test suite**

Run: `python -m unittest discover -s tests -v`
Expected: PASS for database migrations, feedback validation, dashboard state, analysis normalization, plan boundaries, legacy reads and UI state contracts.

- [ ] **Step 8: Synchronize superseded design documentation**

In `项目计划书.md` and `docs/superpowers/specs/2026-09-30-ai-career-guidance-design.md`, update only superseded requirement sections to say three roles, optional experience feedback, SQLite and adjustable plan duration; retain existing member assignments and confirmed team decisions. Change the approved UI design spec status from “待用户审阅” to “已确认”. Do not change the user's recruitment workbook or import its records.

- [ ] **Step 9: Perform manual local acceptance**

Start FastAPI and Streamlit using the README commands. Walk through first-use profile entry, returning-user dashboard, three-role comparison, skip and completed experience paths, unknown-versus-known analysis, 1-week and 12-week plan generation, weekly budget limits, saved-plan history, Markdown export and model-unavailable fallback labeling.
Expected: The app remains navigable when optional profile fields or real knowledge documents are absent; all visible statuses match their underlying data.

- [ ] **Step 10: Commit the integrated UI, state copy, and documentation**

```bash
git add app/ui.py app/services.py README.md 项目计划书.md docs/superpowers/specs/2026-09-30-ai-career-guidance-design.md docs/superpowers/specs/2026-10-01-career-guidance-ui-design.md tests/test_ui_contracts.py
git commit -m "feat: align career guidance UI with approved design"
```

## Handoff Notes

- Implement tasks in order because API and service contracts feed the UI.
- Keep each task independently reviewable; do not combine real recruitment workbook ingestion with this UI implementation.
- Existing environment configuration and user credentials are outside plan scope; never print API secrets.
- Do not migrate or delete existing SQLite user data during implementation.
