# 画像、岗位探索与职业分析交互优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复技术下拉框可见性、兴趣自定义、岗位探索信息层级和更新职业分析可见性问题。

**Architecture:** 保持 Streamlit 页面、FastAPI profile schema 和 SQLite 数据结构不变。所有行为调整集中在 `app/ui.py`，视觉可见性规则放在现有 `workspace.css`，AppTest 回归覆盖数据合并、页面顺序和分析刷新状态。

**Tech Stack:** Python 3、Streamlit、FastAPI、SQLite、`unittest`、Streamlit AppTest。

**Spec:** `docs/superpowers/specs/2026-10-12-profile-exploration-analysis-ux-design.md`

## Global Constraints

- 不新增数据库表或 API 字段。
- `profile.interests` 仍保存去重后的字符串列表。
- 更新职业分析失败时保留已有分析和问答；只有成功后清理当前问答状态。
- 不覆盖工作区中与本需求无关的既有修改。

## Review Focus

- 已保存的自定义兴趣必须重新进入页面时仍可选择；测试放在 Task 1。
- 自定义兴趣与内置兴趣重复、混用中英文逗号时必须去重并保序；测试放在 Task 1。
- 分析更新请求失败时不能丢失现有问答；测试放在 Task 3。
- 更新成功后最新分析必须出现在问答之前且旧问答不再显示；测试放在 Task 3。
- 岗位探索窄屏下比较区和体验区仍按顺序纵向排列；测试放在 Task 2 的 AppTest 文本顺序断言和 CSS 检查中。

---

### Task 1: 支持自定义兴趣并增强画像表单候选项

**Files:**
- Modify: `app/ui.py: profile_page` and add a small local helper near existing parsing helpers
- Modify: `app/assets/workspace.css: form widget rules`
- Test: `scripts/test_ui.py`

**Interfaces:**
- Consumes: existing `/profile` GET/PUT payloads and `known`/`options` lists.
- Produces: normalized `interests` list passed to the existing `/profile` PUT endpoint; stable form widget labels/keys for AppTest.

- [x] **Step 1: Write AppTest coverage**

Add tests that open `个人画像`, enter custom interests such as `写脚本，做实验, 写脚本`, save, and assert the PUT payload contains the built-in selections plus one ordered `写脚本` value. Add a second run with the returned profile and assert the custom value is included in the interest multiselect options/default selection.

- [ ] **Step 2: Run the focused tests to verify they fail**

Run: `\.venv\Scripts\python.exe -m unittest scripts.test_ui.WorkspaceTest.test_custom_interests_are_saved_and_restored -v`

Expected: FAIL because the current form has no custom-interest input and only filters interests against the built-in list.

- [x] **Step 3: Implement interest normalization and form wiring**

Add a helper with the exact behavior `split_comma_values(value: str) -> list[str]`: replace full-width commas with ASCII commas, split, strip whitespace, discard empty values, and preserve first occurrence order. Build `interest_options` from the built-in list plus saved custom values. Add a labeled `其他想做的事情（选填）` text input in the existing interest section. On submit, combine selected built-in values and parsed custom values with the same order-preserving de-duplication before calling `/profile`.

Keep the existing “其他技术（选填）” parsing behavior compatible with this helper. Add focused CSS for the technology multiselect trigger and option popover so the control visibly expands on focus/hover/click without changing widget dimensions or hiding option text.

- [x] **Step 4: Run the focused tests to verify they pass**

Run: `\.venv\Scripts\python.exe -m unittest scripts.test_ui.WorkspaceTest.test_custom_interests_are_saved_and_restored scripts.test_ui.WorkspaceTest.test_partial_profile_save_preserves_empty_fields -v`

Expected: PASS, with the existing skills payload behavior unchanged.

- [ ] **Step 5: Commit**

```bash
git add app/ui.py app/assets/workspace.css scripts/test_ui.py
git commit -m "feat: allow custom interests in profile form"
```

### Task 2: Move role comparison above the optional experience task

**Files:**
- Modify: `app/ui.py: opportunity_page`
- Modify: `scripts/test_ui.py`

**Interfaces:**
- Consumes: existing experience feedback API and `JOB_BY_ID` starter task data.
- Produces: unchanged feedback payloads and role selection controls with a new render order.

- [x] **Step 1: Write order regression test**

Add an AppTest that opens `岗位探索`, reads the rendered markdown/text elements, and asserts the first occurrence of `比较三个方向` precedes `想先试试看？` while the existing start/skip controls remain available.

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `\.venv\Scripts\python.exe -m unittest scripts.test_ui.WorkspaceTest.test_experience_section_precedes_role_comparison -v`

Expected: FAIL because the current page renders the experience panel before the comparison heading.

- [x] **Step 3: Reorder the page rendering**

Move the existing `section_heading("比较三个方向", ...)` block and its role-card loop above the experience panel and feedback summary. Preserve all existing widget keys, feedback calls, `choose_job`, and role card content so saved behavior is unchanged.

- [x] **Step 4: Verify desktop and narrow layout rules**

Run the focused AppTest and inspect the existing `@media (max-width: 900px)`/`760px` rules to ensure the two sections remain stacked without new fixed widths or overlap.

- [ ] **Step 5: Commit**

```bash
git add app/ui.py scripts/test_ui.py
git commit -m "fix: show exploration task before role comparison"
```

### Task 3: Keep refreshed analysis above consultation and clear stale chat only after success

**Files:**
- Modify: `app/ui.py: consultation_section and analysis_page`
- Modify: `scripts/test_ui.py`

**Interfaces:**
- Consumes: existing `/analysis/{job_category}`, `/analyses`, `/chat`, and `/conversations` responses.
- Produces: current analysis state rendered before consultation; successful refresh resets only current chat display/session identifiers.

- [x] **Step 1: Write success and failure regression tests**

Add a test that creates a chat, updates analysis successfully, reruns, and asserts the latest analysis text appears before `职业问答` and the old answer is absent from the visible chat messages. Add a failure variant using a FakeAPI analysis exception/failed response and assert the existing chat remains visible.

- [ ] **Step 2: Run the focused tests to verify they fail**

Run: `\.venv\Scripts\python.exe -m unittest scripts.test_ui.WorkspaceTest.test_analysis_refresh_reorders_and_resets_chat scripts.test_ui.WorkspaceTest.test_failed_analysis_refresh_keeps_chat -v`

Expected: FAIL because consultation currently renders before the saved/current analysis and successful analysis refresh does not clear chat state.

- [x] **Step 3: Refactor page render order and success state transition**

Keep the job selector and refresh button at the top. After loading the profile and selecting the current analysis from session/saved rows, render normalized analysis, actions, and sources first. Render `consultation_section(selected)` only after that result block. Move history analysis expander after consultation. On a successful refresh result, set `analysis`, `analysis_job`, an optional `analysis_updated_at` session value, and remove `chat_display`, `conversation_id`, and `loaded_conversation_id`. Do not clear these keys before a successful response.

- [x] **Step 4: Run focused and existing analysis/chat tests**

Run: `\.venv\Scripts\python.exe -m unittest scripts.test_ui.WorkspaceTest.test_analysis_refresh_reorders_and_resets_chat scripts.test_ui.WorkspaceTest.test_failed_analysis_refresh_keeps_chat scripts.test_ui.WorkspaceTest.test_analysis_and_chat_do_not_leak_across_jobs scripts.test_ui.WorkspaceTest.test_custom_question_uses_visible_consultation_form -v`

Expected: PASS, with job-switch isolation and custom questions unchanged.

- [ ] **Step 5: Commit**

```bash
git add app/ui.py scripts/test_ui.py
git commit -m "fix: keep refreshed career analysis visible above chat"
```

### Task 4: Full verification

**Files:**
- Test: `scripts/test_ui.py`
- Verify: `app/ui.py`, `app/assets/workspace.css`

**Interfaces:**
- Consumes: all changes from Tasks 1-3.
- Produces: a passing regression suite and a browser-checked UI state.

- [x] **Step 1: Run the full UI regression suite**

Run: `\.venv\Scripts\python.exe -m unittest discover -s scripts -p test_ui.py -v`

Expected: all tests pass with no AppTest exceptions.

- [x] **Step 2: Run existing visit-session checks**

Run: `\.venv\Scripts\python.exe -m unittest discover -s scripts -p test_visit_sessions.py -v`

Expected: all visit isolation/session tests pass.

- [ ] **Step 3: Browser-check the four requested interactions**

Start the existing Streamlit app using the project launcher, inspect the profile multiselect on hover/focus/click, save and reload a custom interest, confirm the experience panel is above comparison, and update an analysis after a chat to confirm the new analysis is immediately visible above the cleared consultation area.

- [x] **Step 4: Review the final diff**

Run: `git diff HEAD~3 -- app/ui.py app/assets/workspace.css scripts/test_ui.py`

Expected: only the scoped UI/state/test changes are present; no API schema or database changes are introduced.
