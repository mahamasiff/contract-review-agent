"""
The 3 tools the agent gets, as plain Python functions first -- no MCP
protocol here yet. Testing these directly (calling them like normal
functions) is faster to iterate on than going through a client/server
round-trip, and the MCP server (added later) will just be a thin wrapper
that calls these same functions.

All 3 are read-only / query tools. Mutations (playbook upload/edit,
contract upload) happen through plain FastAPI endpoints, not through
tools the agent can call -- keeps the agent from being able to alter
compliance rules or ingest data on its own initiative.
"""

from backend import playbook_store, vectorstore as vs
from backend.clause_types import CLAUSE_SLUGS, CLAUSE_TYPES

CONTRACTS_COLLECTION = "contracts"


def list_clause_types():
    """No input. Returns the 7 clause types this project reviews, so the
    agent can loop over all of them without them being hardcoded into
    its prompt."""
    return CLAUSE_TYPES


def get_playbook_policy(clause_type: str):
    """Returns {default, fallback, escalate, rationale} for one clause
    type from the vendor playbook."""
    if clause_type not in CLAUSE_SLUGS:
        raise ValueError(
            f"Unknown clause_type '{clause_type}'. Must be one of: {CLAUSE_SLUGS}"
        )
    policy = playbook_store.get_policy(clause_type)
    if policy is None:
        # Shouldn't happen -- load_playbook() validates every clause type
        # has a section -- but fail loudly rather than returning None if
        # the playbook and CLAUSE_TYPES ever drift out of sync.
        raise ValueError(f"Playbook has no policy for '{clause_type}'")
    return policy


def retrieve_clause(contract_id: str, clause_type: str, n_results: int = 3):
    """Semantic search for the chunk(s) of `contract_id`'s text most
    relevant to `clause_type`. Returns a ranked list of
    {text, start, end, distance} -- distance is lower = more similar.

    Raises if contract_id hasn't been ingested (no chunks under that
    doc_id exist), so the agent doesn't mistake "not ingested" for
    "clause not present in the contract"."""
    if clause_type not in CLAUSE_SLUGS:
        raise ValueError(
            f"Unknown clause_type '{clause_type}'. Must be one of: {CLAUSE_SLUGS}"
        )

    client = vs.get_persistent_client()
    collection = vs.get_or_create_collection(client, CONTRACTS_COLLECTION)

    existing = collection.get(where={"doc_id": contract_id}, limit=1)
    if not existing["ids"]:
        raise ValueError(
            f"No ingested chunks found for contract_id '{contract_id}'. "
            "The contract must be uploaded/ingested before it can be queried."
        )

    query_text = next(c["description"] for c in CLAUSE_TYPES if c["slug"] == clause_type)
    results = vs.query(collection, query_text, doc_id=contract_id, n_results=n_results)

    chunks = []
    for text, meta, distance in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        chunks.append({
            "text": text,
            "start": meta["start"],
            "end": meta["end"],
            "distance": distance,
        })
    return chunks
