import hashlib
import re

import requests
import yaml

from app.catalog import SAMPLE_DOCS
from app.settings import CHROMA_PATH, KNOWLEDGE_PATH, setting


COLLECTION_NAME = "career_knowledge_v2"
CHUNK_SIZE = 1800
CHUNK_OVERLAP = 120
EMBEDDING_BATCH_SIZE = 4


def tokenize(text):
    return [token.lower() for token in re.findall(r"[\u4e00-\u9fff]|[a-zA-Z0-9+#.]+", text or "")]


def _parse_document(path):
    text = path.read_text(encoding="utf-8-sig")
    if not text.startswith("---\n"):
        return None
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        return None
    metadata = yaml.safe_load(parts[0][4:]) or {}
    content = parts[1].strip()
    if not metadata.get("title") or not content:
        return None
    metadata["id"] = str(metadata.get("id") or "file-" + path.stem)
    metadata["title"] = str(metadata["title"])
    metadata["job_category"] = str(metadata.get("job_category", "all"))
    metadata["document_type"] = str(metadata.get("document_type", "general"))
    metadata["content"] = content
    metadata["source_name"] = str(metadata.get("source_name", "来源未提供"))
    metadata["source_url"] = str(metadata.get("source_url", ""))
    metadata["updated_at"] = str(metadata.get("updated_at", "未提供"))
    metadata["review_status"] = str(metadata.get("review_status", "not_reviewed"))
    metadata["is_placeholder"] = bool(metadata.get("is_placeholder", False))
    return metadata


def all_documents():
    documents = []
    if KNOWLEDGE_PATH.exists():
        for path in sorted(KNOWLEDGE_PATH.rglob("*.md")):
            if path.name.lower() == "readme.md":
                continue
            document = _parse_document(path)
            if document:
                documents.append(document)
    return documents or list(SAMPLE_DOCS)


def _split_text(text, max_chars, overlap_chars):
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            step = max(1, max_chars - overlap_chars)
            for start in range(0, len(paragraph), step):
                piece = paragraph[start:start + max_chars]
                chunks.append(piece)
                if start + max_chars >= len(paragraph):
                    break
            continue
        candidate = (current + "\n\n" + paragraph).strip() if current else paragraph
        if current and len(candidate) > max_chars:
            chunks.append(current)
            overlap_size = min(overlap_chars, max_chars - len(paragraph) - 2)
            overlap = current[-overlap_size:] if overlap_size > 0 else ""
            current = (overlap + "\n\n" + paragraph).strip() if overlap else paragraph
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def chunk_document(document, max_chars=CHUNK_SIZE, overlap_chars=CHUNK_OVERLAP):
    text_chunks = _split_text(document["content"], max_chars, overlap_chars)
    chunks = []
    for index, content in enumerate(text_chunks):
        chunk = {key: value for key, value in document.items() if key != "content"}
        chunk["source_id"] = document["id"]
        chunk["chunk_index"] = index
        chunk["id"] = "{0}-chunk-{1:04d}".format(document["id"], index)
        chunk["content"] = content
        chunks.append(chunk)
    return chunks


def all_chunks():
    return [chunk for document in all_documents() for chunk in chunk_document(document)]


def _unique_sources(scored_chunks, limit, retrieval):
    seen = set()
    found = []
    for score, chunk in sorted(scored_chunks, key=lambda item: item[0], reverse=True):
        source_id = chunk.get("source_id", chunk["id"])
        if source_id in seen:
            continue
        seen.add(source_id)
        result = dict(chunk, score=score, retrieval=retrieval)
        found.append(result)
        if len(found) >= limit:
            break
    return found


def lexical_search(query, job_category, limit=4, document_type=None):
    query_tokens = set(tokenize(query))
    scored = []
    for chunk in all_chunks():
        if chunk["job_category"] not in (job_category, "all"):
            continue
        if document_type and chunk.get("document_type") != document_type:
            continue
        tokens = set(tokenize(chunk["title"] + " " + chunk["content"]))
        overlap = len(tokens & query_tokens)
        if overlap or (not document_type and chunk["job_category"] == job_category):
            scored.append((overlap, chunk))
    return _unique_sources(scored, limit, "keyword")


def embeddings_for(texts):
    if not texts:
        return []
    api_key = setting("LLM_API_KEY")
    base_url = setting("LLM_BASE_URL").rstrip("/")
    model = setting("EMBEDDING_MODEL")
    if not (api_key and base_url and model):
        return None
    endpoint = base_url if base_url.endswith("/v1") else base_url + "/v1"
    response = requests.post(
        endpoint + "/embeddings",
        headers={"Authorization": "Bearer " + api_key},
        json={"model": model, "input": texts},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json().get("data", [])
    data.sort(key=lambda item: item.get("index", 0))
    vectors = [item["embedding"] for item in data]
    if len(vectors) != len(texts):
        raise ValueError("Embedding 服务返回数量与请求数量不一致")
    return vectors


def embedding_for(text):
    vectors = embeddings_for([text])
    return vectors[0] if vectors else None


def get_chroma_collection():
    try:
        import chromadb
    except ImportError:
        return None
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return client.get_or_create_collection(COLLECTION_NAME, metadata={"hnsw:space": "cosine"})


def _chroma_metadata(chunk, content_hash):
    metadata = {
        key: value for key, value in chunk.items()
        if key not in ("id", "content") and isinstance(value, (str, int, float, bool))
    }
    metadata["content_hash"] = content_hash
    return metadata


def seed_sample_knowledge():
    collection = get_chroma_collection()
    if collection is None:
        return {"available": False, "indexed_chunks": 0, "updated_chunks": 0, "removed_chunks": 0}
    chunks = all_chunks()
    texts = [chunk["title"] + "\n" + chunk["content"] for chunk in chunks]
    hashes = [hashlib.sha256(text.encode("utf-8")).hexdigest() for text in texts]
    current_ids = [chunk["id"] for chunk in chunks]
    existing = collection.get(include=["metadatas"])
    existing_metadata = dict(zip(existing.get("ids", []), existing.get("metadatas", [])))
    changed_indices = [
        index for index, chunk_id in enumerate(current_ids)
        if existing_metadata.get(chunk_id, {}).get("content_hash") != hashes[index]
    ]
    metadata_only_indices = [
        index for index, chunk_id in enumerate(current_ids)
        if chunk_id in existing_metadata
        and index not in changed_indices
        and existing_metadata[chunk_id] != _chroma_metadata(chunks[index], hashes[index])
    ]
    changed_vectors = []
    for start in range(0, len(changed_indices), EMBEDDING_BATCH_SIZE):
        batch_indices = changed_indices[start:start + EMBEDDING_BATCH_SIZE]
        batch_texts = [texts[index] for index in batch_indices]
        vectors = embeddings_for(batch_texts)
        if vectors is None:
            return {
                "available": True,
                "configured": False,
                "indexed_chunks": collection.count(),
                "updated_chunks": 0,
                "removed_chunks": 0,
            }
        changed_vectors.extend(vectors)
    if changed_indices:
        changed_chunks = [chunks[index] for index in changed_indices]
        changed_hashes = [hashes[index] for index in changed_indices]
        changed_metadata = [
            _chroma_metadata(chunk, content_hash)
            for chunk, content_hash in zip(changed_chunks, changed_hashes)
        ]
        for start in range(0, len(changed_chunks), 100):
            end = start + 100
            collection.upsert(
                ids=[chunk["id"] for chunk in changed_chunks[start:end]],
                documents=[chunk["content"] for chunk in changed_chunks[start:end]],
                embeddings=changed_vectors[start:end],
                metadatas=changed_metadata[start:end],
            )
    for start in range(0, len(metadata_only_indices), 500):
        indices = metadata_only_indices[start:start + 500]
        collection.update(
            ids=[current_ids[index] for index in indices],
            metadatas=[_chroma_metadata(chunks[index], hashes[index]) for index in indices],
        )
    desired_ids = set(current_ids)
    stale_ids = [chunk_id for chunk_id in existing.get("ids", []) if chunk_id not in desired_ids]
    for start in range(0, len(stale_ids), 500):
        collection.delete(ids=stale_ids[start:start + 500])
    return {
        "available": True,
        "configured": True,
        "indexed_chunks": collection.count(),
        "updated_chunks": len(changed_indices) + len(metadata_only_indices),
        "reembedded_chunks": len(changed_indices),
        "removed_chunks": len(stale_ids),
    }


def search_knowledge(query, job_category, limit=4, document_type=None):
    collection = get_chroma_collection()
    if collection is not None and setting("EMBEDDING_MODEL"):
        try:
            vector = embedding_for(query)
            if vector and collection.count():
                filters = [{"$or": [{"job_category": job_category}, {"job_category": "all"}]}]
                if document_type:
                    filters.append({"document_type": document_type})
                where = filters[0] if len(filters) == 1 else {"$and": filters}
                results = collection.query(
                    query_embeddings=[vector],
                    n_results=min(max(limit * 3, limit), collection.count()),
                    where=where,
                    include=["documents", "metadatas", "distances"],
                )
                scored = []
                for index, content in enumerate(results.get("documents", [[]])[0]):
                    score = 1 - results["distances"][0][index]
                    if document_type == "learning_resource" and score < 0.25:
                        continue
                    metadata = results.get("metadatas", [[]])[0][index]
                    metadata.pop("content_hash", None)
                    metadata["content"] = content
                    metadata["id"] = metadata.get("source_id") or metadata.get("id", "")
                    scored.append((score, metadata))
                if scored:
                    return _unique_sources(scored, limit, "chroma")
        except (requests.RequestException, ValueError, RuntimeError):
            pass
    return lexical_search(query, job_category, limit, document_type)


def search_learning_resources(query, job_category, limit=2):
    if limit <= 0:
        return []
    return search_knowledge(
        query,
        job_category,
        limit=min(limit, 2),
        document_type="learning_resource",
    )


def source_status(sources):
    if not sources:
        return "no_sources"
    if any(source.get("is_placeholder") for source in sources):
        return "placeholder"
    if any(source.get("review_status", "not_reviewed") != "verified" for source in sources):
        return "review_required"
    return "grounded"
