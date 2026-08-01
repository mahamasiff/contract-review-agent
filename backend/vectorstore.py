"""
Shared retrieval module.

Two consumers, same logic:
  - eval/retrieval_eval.py     -- chunk a contract, check if the right
                                       chunk gets retrieved for a clause type
  - backend/mcp_server/tools.py    -- (later) embed playbook rules /
                                       precedent, retrieve the relevant one

ChromaDB uses its built-in local embedding model automatically if you don't
pass a custom embedding_function -- no API key required.
"""

import chromadb


# ---------- Client ----------

def get_persistent_client(persist_dir="chroma_store"):
    """Writes to disk, survives across runs. Use this for playbook/
    precedent collections that should stick around between sessions."""
    return chromadb.PersistentClient(path=persist_dir)


def get_ephemeral_client():
    """In-memory only, nothing written to disk, gone when the process
    exits. Use this for eval runs / one-off scripts."""
    return chromadb.EphemeralClient()


def get_or_create_collection(client, name):
    return client.get_or_create_collection(name=name)


def reset_collection(client, name):
    """Delete + recreate a collection. Handy in eval loops so each run
    starts clean instead of accumulating old data."""
    try:
        client.delete_collection(name=name)
    except Exception:
        pass
    return client.get_or_create_collection(name=name)


# ---------- Chunking ----------

def chunk_text(text, chunk_chars=800, overlap_chars=150):
    """Character-based chunking with overlap. Offsets are kept so chunks
    can be checked against character-offset ground truth (e.g. CUAD's
    answer_start)."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_chars
        chunks.append({"text": text[start:end], "start": start, "end": end})
        if end >= len(text):
            break
        start += chunk_chars - overlap_chars
    return chunks


# ---------- Add ----------

def add_chunks(collection, chunks, doc_id, extra_metadata=None):
    """Embed + store chunks under a shared doc_id, so they can be queried
    in isolation from other documents' chunks later (see query() below).
    Safe to call once per document; re-adding the same doc_id will error
    on duplicate ids -- use reset_collection() between eval runs."""
    ids = [f"{doc_id}__{i}" for i in range(len(chunks))]
    documents = [c["text"] for c in chunks]
    metadatas = []
    for c in chunks:
        meta = {"doc_id": doc_id, "start": c["start"], "end": c["end"]}
        if extra_metadata:
            meta.update(extra_metadata)
        metadatas.append(meta)

    collection.add(ids=ids, documents=documents, metadatas=metadatas)


# ---------- Query ----------

def query(collection, query_text, doc_id=None, n_results=5):
    """Semantic search. Pass doc_id to scope the search to just one
    document's chunks -- important for per-contract retrieval, so you
    don't accidentally retrieve a chunk from a different contract.

    Returns the raw ChromaDB result dict: results["documents"][0] is the
    ranked list of chunk texts, results["metadatas"][0] the matching
    metadata (including "start"/"end" offsets), results["distances"][0]
    the similarity distances (lower = more similar).
    """
    where = {"doc_id": doc_id} if doc_id else None
    return collection.query(
        query_texts=[query_text],
        n_results=n_results,
        where=where,
    )