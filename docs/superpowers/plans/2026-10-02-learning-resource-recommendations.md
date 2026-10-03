# Learning Resource Recommendations Implementation Plan

> **For agentic workers:** Implement natively, one task at a time, and review the resulting changes before continuing. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Attach up to two relevant, source-backed learning resources to each action-plan task and preserve them in the UI and Markdown export.

**Architecture:** Enrich curated resource metadata, add a document-type-filtered RAG query, attach exact retrieved source fields to tasks after plan generation, and render them in the existing task card and export. Retrieval failure must not fail plan generation.

**Tech Stack:** Python, FastAPI service layer, Chroma/keyword retrieval, Streamlit, Markdown, YAML frontmatter.

**Spec:** `docs/superpowers/specs/2026-10-02-learning-resource-recommendations-design.md`

## Global Constraints

- Recommend only `document_type: learning_resource` entries from `data/knowledge/learning_resources/`.
- Each task displays at most 2 resources matching its role or `all`.
- URLs and resource metadata come from knowledge records; the model never invents them.
- Keep generation working when retrieval fails and keep historical plans without the new field compatible.
- Do not represent link accessibility as course certification.

## Review Focus

- Vector retrieval must filter both `document_type` and `job_category`; manually inspect an indexed query for each role.
- Keyword fallback must apply the same filters; repeat the same query with Chroma unavailable.
- Missing URLs and no matches must yield no recommendation; inspect an empty-resource task.
- Historical plans without `learning_resources` must still render and export; open an existing saved plan.
- Per-task results must stay within the two-item cap and preserve exact source URLs; generate a plan with overlapping task topics and inspect it.

---

### Task 1: Add explicit learning-resource metadata

**Files:**
- Modify: `data/knowledge/learning_resources/*.md` (14 curated resource files)

**Interfaces:**
- Produces the YAML fields consumed by the retrieval and presentation tasks: `recommendation_hint`, `language`, and `access_note`.

- [ ] Add those three fields to every curated learning-resource file. Use concise task-specific guidance; only state language/access details already recorded in the resource text, and leave unknown details blank rather than guessing.
- [ ] Manually inspect one file per role and the shared Git file. Confirm each has a unique existing `id`, exact `source_url`, `document_type: learning_resource`, and all three new fields.

**Deliverable:** All 14 existing resources can provide the task match reason and optional language/access details as structured metadata.

### Task 2: Add filtered resource retrieval

**Files:**
- Modify: `app/rag.py`

**Interfaces:**
- Produces: `search_learning_resources(query: str, job_category: str, limit: int = 2) -> list[dict]`.
- Consumes existing `get_chroma_collection`, `embedding_for`, `_unique_sources`, and `tokenize` behavior.

- [ ] Extend lexical and vector search paths with an optional `document_type` filter while preserving the existing behavior when no filter is provided.
- [ ] Implement `search_learning_resources` using `document_type="learning_resource"`, role-or-`all` filtering, and a maximum result count of 2. Require positive lexical overlap or a meaningful vector similarity; a role match alone must not produce a recommendation.
- [ ] Re-run `POST /knowledge/index` so the existing Chroma records receive the new resource metadata without re-embedding unchanged document text.
- [ ] Manually inspect returned metadata from one backend, one frontend, one testing, and one shared-resource query; confirm irrelevant document types and other roles are absent. Repeat with vector retrieval unavailable and confirm lexical fallback applies the same filters.

**Deliverable:** A bounded resource-only search that returns exact source metadata and works with both vector and lexical retrieval.

### Task 3: Attach resources to generated plan tasks

**Files:**
- Modify: `app/services.py`

**Interfaces:**
- Consumes: `search_learning_resources(query, job_category, limit=2) -> list[dict]` from Task 2.
- Produces: optional task field `learning_resources: list[dict]` containing `id`, `title`, `source_name`, `source_url`, `recommendation_hint`, `language`, `access_note`, `review_status`, and `updated_at`.

- [ ] Add a focused helper that builds a query from the task title, description, completion criteria, and job category; request at most 2 resource records.
- [ ] After model or fallback weeks are finalized, attach recommendations to each task, dropping records without `source_url` and mapping only the specified fields.
- [ ] Catch retrieval exceptions locally and leave `learning_resources` empty so the plan is still returned.
- [ ] Manually inspect a generated plan and a retrieval-failure plan. Confirm task resource counts are at most 2, URLs exactly match source records, and the latter still generates successfully.

**Deliverable:** Every generated plan task has zero to two reliable resource records independent of whether the task text came from the model or local fallback.

### Task 4: Render task recommendations and export them

**Files:**
- Modify: `app/ui.py`
- Modify: `app/services.py`

**Interfaces:**
- Consumes `task["learning_resources"]` from Task 3; absent field is treated as an empty list.

- [ ] Render a compact “学习资料” section inside each task card after its completion criteria. Show title as a clickable source URL, source name, recommendation hint, and only nonempty language/access notes.
- [ ] Update `plan_as_markdown` so each task includes the same resources as Markdown links with source and recommendation hint; omit the section for an empty or absent list.
- [ ] Manually open a new plan, an older saved plan, and its downloaded Markdown. Confirm links belong to their specific tasks, old plans remain readable, and empty recommendations produce no empty section.

**Deliverable:** Recommendations are visible in the current plan UI and remain usable in downloaded Markdown without changing old plans.
