import os
import chromadb


# ---------- Client ----------

_persistent_clients = {}  # persist_dir -> chromadb.PersistentClient, cached


def get_persistent_client(persist_dir="chroma_store"):
    """Writes to disk, survives across runs. Use this for playbook/
    precedent collections that should stick around between sessions.

    Cached per persist_dir: constructing two independent PersistentClient
    instances pointing at the same directory within one process is not
    safe with chromadb's segment engine -- a second instance's index
    reader can fail to see data a first instance just wrote (raises
    "Nothing found on disk" on query), since the write isn't visible
    outside the client that made it until the process restarts. Ingestion
    (write) and retrieval (read) both need to go through the same client
    instance within a process, so every caller should get the same
    cached instance for a given path."""
    # Normalize before using as a cache key -- "chroma_store" (relative,
    # cwd-dependent) and an absolute path to the same directory are
    # different strings but must resolve to the same cached client, or
    # this cache does nothing for callers that don't happen to pass the
    # exact same string. normcase() matters on Windows specifically:
    # abspath() alone doesn't fix drive-letter case (cwd-relative paths
    # can resolve with an uppercase "C:\" while a hardcoded path uses
    # lowercase "c:\"), which silently defeated this cache and
    # reproduced the exact bug it's meant to prevent.
    key = os.path.normcase(os.path.abspath(persist_dir))
    if key not in _persistent_clients:
        _persistent_clients[key] = chromadb.PersistentClient(path=key)
    return _persistent_clients[key]


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