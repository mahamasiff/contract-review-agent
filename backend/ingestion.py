"""
Minimal ingestion for the demo: reuses the full contract text already
sitting in data/<slug>.json (from CUAD, via prepare_cuad_data.py)
instead of building real PDF upload/parsing yet. Real PDF ingestion
(ingestion/loader.py) is a separate, later piece -- this just gets
contracts into the vectorstore so the agent runner has something to
query against.
"""

import json
import os

from backend import mcp_tools, vectorstore as vs
from backend.clause_types import CLAUSE_SLUGS

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
SELECTION_PATH = os.path.join(DATA_DIR, "eval_contracts_selection.json")


def get_demo_contract_ids():
    """The 14 contracts picked by select_contracts.py, for a dropdown/
    picker in the UI."""
    with open(SELECTION_PATH, encoding="utf-8") as f:
        selection = json.load(f)
    return list(selection.keys())


def get_contract_text(contract_id):
    """Full contract text, pulled from whichever data/<slug>.json file
    happens to contain it first -- the text is identical no matter which
    clause-type file it's read from, since it's all the same document."""
    for slug in CLAUSE_SLUGS:
        path = os.path.join(DATA_DIR, f"{slug}.json")
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for ex in data:
            if ex["contract"] == contract_id:
                return ex["context"]
    raise ValueError(f"contract_id '{contract_id}' not found in any data/<slug>.json file")


def is_ingested(contract_id):
    client = vs.get_persistent_client()
    collection = vs.get_or_create_collection(client, mcp_tools.CONTRACTS_COLLECTION)
    existing = collection.get(where={"doc_id": contract_id}, limit=1)
    return bool(existing["ids"])


def ensure_ingested(contract_id):
    """Chunk + embed a contract if it isn't already in the store.
    Idempotent -- safe to call every time the UI loads a contract."""
    if is_ingested(contract_id):
        return

    text = get_contract_text(contract_id)
    client = vs.get_persistent_client()
    collection = vs.get_or_create_collection(client, mcp_tools.CONTRACTS_COLLECTION)
    chunks = vs.chunk_text(text)
    vs.add_chunks(collection, chunks, doc_id=contract_id)
