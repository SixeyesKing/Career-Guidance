# RAG Knowledge Integration Implementation Plan

> **For agentic workers:** Native execution authorized by the user. Steps use checkbox syntax for tracking.

**Goal:** Prepare the curated three-role knowledge corpus and make the existing RAG loader index and retrieve it with reliable source metadata.

**Architecture:** Preserve source files in `知识库/`; produce normalized, generated Markdown in `data/knowledge/generated/`. Load normalized documents, split them into overlapping chunks, maintain them in a versioned Chroma collection, and retain lexical fallback.

**Tech Stack:** Python 3.9+, openpyxl, PyYAML, FastAPI, Chroma, OpenAI-compatible Embeddings.

**Spec:** `docs/superpowers/specs/2026-10-01-rag-knowledge-integration-design.md`

## Global Constraints

- Only backend, frontend, and test development job postings enter the first corpus.
- Original spreadsheet and Markdown files remain unchanged.
- Missing or pending review status remains visible in source metadata.
- Do not invent source names, URLs, or update dates.
- Keep vector search optional and lexical fallback available.
- Do not read, print, or commit `.env` secrets.

## Review Focus

- Blank spreadsheet separator rows must be skipped; rows with unsupported directions must not enter role retrieval.
- Pending and missing review marks must survive conversion and appear in source status.
- Long source documents must fit embedding request limits and must not duplicate citations.
- Re-running generation and indexing must update stable IDs without deleting the old collection.
- Missing Embeddings or Chroma must leave the knowledge corpus usable through lexical retrieval.

---

### Task 1: Generate normalized source documents

**Files:**
- Create: `scripts/prepare_knowledge.py`
- Create: `data/knowledge/generated/` Markdown output

**Interfaces:**
- `main()` reads the source workbook and selected Markdown, then writes stable generated documents without modifying source files.
- Excel posting IDs use the source row sequence; job labels map to `backend`, `frontend`, and `testing`.

- [x] Read both workbook sheets with `openpyxl`, join by sequence number, and skip blank or unsupported rows.
- [x] Generate one YAML-frontmatter Markdown per supported posting, preserving original text and source fields.
- [x] Generate normalized copies of the relevant role, process, timeline, learning, and interview documents; assign supported role IDs and explicit review metadata.
- [x] Preserve the workbook's verified, pending, and blank review state as metadata values.

### Task 2: Load and chunk the corpus

**Files:**
- Modify: `app/rag.py`

**Interfaces:**
- `all_documents()` returns stable source records and ignores the README and non-normalized inputs.
- `chunk_document(document, max_chars=1800, overlap_chars=120)` returns stable chunk records with source metadata.

- [x] Parse YAML metadata and normalize review state.
- [x] Split long text at paragraph boundaries with bounded overlap; keep the source ID and title on each chunk.
- [x] Deduplicate lexical search by source document and return only the best matching chunk for each source.
- [x] Use built-in sample docs only when no normalized source docs are available.

### Task 3: Maintain vector index and source status

**Files:**
- Modify: `app/rag.py`
- Modify: `app/services.py`
- Modify: `app/ui.py`

**Interfaces:**
- Chroma uses collection `career_knowledge_v2` and stable chunk IDs with `upsert` semantics.
- `source_status(sources)` returns `no_sources`, `placeholder`, `review_required`, or `grounded`.

- [x] Create a new collection version, batch Embeddings where supported, and upsert chunk contents and metadata.
- [x] Keep lexical fallback behavior when vector dependencies or Embeddings are unavailable.
- [x] Preserve review status through analysis and chat source objects; show pending or missing review marks in the UI.
- [x] Make `/knowledge/status` report the active version's indexed chunk count.

### Task 4: Document regeneration and indexing

**Files:**
- Modify: `README.md`
- Modify: `data/knowledge/README.md`

- [x] Document the source folder, generated folder, preparation command, three-role scope, and index endpoint.
- [x] Keep generated corpus files separate from the user's source workbook and Markdown.

### Completion Note

The corpus generation, static compile check, source-level retrieval checks, index status check, and UI health check completed. Unit and integration tests were not added or run, as directed. The active Chroma index is `career_knowledge_v2` with 308 chunks.
