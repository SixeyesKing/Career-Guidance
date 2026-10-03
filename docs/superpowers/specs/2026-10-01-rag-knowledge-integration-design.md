# RAG Knowledge Integration Design

**Date:** 2026-10-01  
**Status:** Approved by user for implementation  
**Source:** `知识库/` workbook and Markdown documents

## Goal

Make the user's curated knowledge usable by the current three-role career assistant while preserving all source files and communicating source review status accurately.

## Design

- Keep `知识库/` as the untouched source area. Generate normalized Markdown under `data/knowledge/generated/` so the current project path can index it.
- Convert only Excel rows for backend, frontend, and test development. Keep one record per posting, join each ledger row to its raw text by sequence number, and retain its company, source URL, update date, and review status.
- Normalize relevant general Markdown documents into role-scoped documents with YAML metadata. Omit documents about roles the application does not support. Treat broad or missing citations as unverified rather than inventing sources.
- Preserve review states as `verified`, `pending_review`, or `not_reviewed`. Verified means the source workbook's own status; it is not an independent audit by the application.
- Split long documents into bounded overlapping chunks for both lexical and vector retrieval. Return source-level metadata and deduplicate citations by source document.
- Use a new Chroma collection version and upsert current chunks. This avoids serving stale whole-document vectors from the prior collection without deleting that collection.
- Keep the existing keyword fallback when Chroma or Embeddings are unavailable. Do not require the recruitment workbook at application runtime.

## Scope

Included: a repeatable corpus preparation script, normalized generated documents, chunked retrieval/indexing, source review labels, and README instructions.

Excluded: live crawling, external verification of all 214 job entries, support for additional roles, changes to the original workbook or Markdown, and automatic recurring index rebuilds.

## Acceptance

1. Running the preparation script generates only supported-role postings plus relevant general material and leaves `知识库/` unchanged.
2. Every generated Markdown document has the metadata required by the loader and a stable ID.
3. Review status and source links remain attached to retrieved chunks; unreviewed or pending material is not presented as verified.
4. Long documents are chunked, citation results are deduplicated, and re-indexing updates rather than duplicates current chunk IDs.
5. Retrieval still falls back to local lexical search when vector indexing is unavailable.
