"""
Retrieval eval, run across all 7 clause types this project covers.

Key design point: the same 510 CUAD contracts get reused across clause
types (a contract can have a Renewal Term AND a Cap On Liability clause,
etc). So every unique contract is chunked + embedded exactly ONCE into a
single shared collection, then queried differently per clause type --
instead of re-embedding the same contract text once per clause type it
happens to appear in.

For each clause type:
  1. Load data/<slug>.json (built by data/prepare_cuad_data.py)
  2. Keep only contracts where that clause is actually present
  3. Query the shared collection with a clause-specific description,
     restricted to that contract's chunks, and check whether the
     retrieved top-k chunks overlap the ground-truth character span
  4. Report recall@1 / @3 / @5

Run from the project root:
    python eval/retrieval_eval.py
"""

import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from backend import vectorstore as vs
from backend.clause_types import CLAUSE_TYPES

DATA_DIR = os.path.join(PROJECT_ROOT, "data")

# Optional: cap the number of UNIQUE contracts used, for fast iteration.
# None = use everything (the real eval number). Set e.g. to 150 while
# you're debugging/tuning, then set back to None for your reported result.
MAX_UNIQUE_CONTRACTS = None

# Two-stage retrieval (query_with_rerank: wide vector search + cross-
# encoder rerank) vs plain vector search alone. Toggle to get a direct
# before/after comparison on the same sample.
USE_RERANK = True
RERANK_CANDIDATE_POOL = 15

# slug (matches data/<slug>.json) -> description used as the retrieval
# query. Built from backend/clause_types.py -- the single source of
# truth for the 7 clause types -- rather than a separate hardcoded copy.
CLAUSE_QUERIES = {
    c["slug"]: f'{c["display_name"]} clause: {c["description"]}'
    for c in CLAUSE_TYPES
}

K_VALUES = (1, 3, 5)
CHUNK_CHARS = 800
OVERLAP_CHARS = 150


def load_all_examples():
    """slug -> list of positive examples, for every clause file that exists."""
    all_data = {}
    for slug in CLAUSE_QUERIES:
        path = os.path.join(DATA_DIR, f"{slug}.json")
        if not os.path.exists(path):
            print(f"SKIPPING {slug}: {path} not found "
                  f"(run data/prepare_cuad_data.py first)")
            continue
        with open(path) as f:
            data = json.load(f)
        all_data[slug] = [ex for ex in data if not ex["is_impossible"]]
    return all_data


def build_unique_contract_texts(all_data):
    """contract title -> context text, deduped across all clause types
    (a contract's text is identical no matter which clause file it came
    from, since it's the same underlying document)."""
    texts = {}
    for examples in all_data.values():
        for ex in examples:
            texts.setdefault(ex["contract"], ex["context"])
    return texts


def find_gold_chunk_indices(chunks, answer_start, answer_text):
    gold_start = answer_start
    gold_end = answer_start + len(answer_text)
    return [i for i, c in enumerate(chunks)
            if c["start"] < gold_end and c["end"] > gold_start]


def embed_all_contracts_once(unique_texts):
    client = vs.get_ephemeral_client()
    collection = vs.reset_collection(client, "eval_shared")

    contract_chunks = {}
    total = len(unique_texts)
    for i, (title, text) in enumerate(unique_texts.items()):
        chunks = vs.chunk_text(text, CHUNK_CHARS, OVERLAP_CHARS)
        contract_chunks[title] = chunks
        vs.add_chunks(collection, chunks, doc_id=title)
        if (i + 1) % 20 == 0 or (i + 1) == total:
            print(f"  embedded {i + 1}/{total} unique contracts...")

    return collection, contract_chunks


def evaluate_clause_type(slug, examples, query, collection, contract_chunks,
                          k_values=K_VALUES):
    hits = {k: 0 for k in k_values}
    total = 0
    skipped = 0

    for ex in examples:
        if ex["contract"] not in contract_chunks:
            continue  # excluded by MAX_UNIQUE_CONTRACTS sampling
        chunks = contract_chunks[ex["contract"]]

        gold_indices = set()
        for answer in ex["answers"]:
            gold_indices |= set(find_gold_chunk_indices(
                chunks, answer["answer_start"], answer["text"]))

        if not gold_indices:
            skipped += 1
            continue

        if USE_RERANK:
            reranked = vs.query_with_rerank(
                collection, query, doc_id=ex["contract"],
                candidate_pool=RERANK_CANDIDATE_POOL, n_results=max(k_values),
            )
            retrieved_starts_ends = [(c["start"], c["end"]) for c in reranked]
        else:
            results = vs.query(collection, query, doc_id=ex["contract"],
                                n_results=max(k_values))
            retrieved_starts_ends = [(m["start"], m["end"]) for m in results["metadatas"][0]]

        retrieved_indices = []
        for start, end in retrieved_starts_ends:
            for i, c in enumerate(chunks):
                if c["start"] == start and c["end"] == end:
                    retrieved_indices.append(i)
                    break

        total += 1
        for k in k_values:
            if set(retrieved_indices[:k]) & gold_indices:
                hits[k] += 1

    result = {"clause_type": slug, "n": total, "skipped": skipped}
    for k in k_values:
        result[f"recall@{k}"] = round(hits[k] / total, 3) if total else 0.0
    return result


def main():
    print(f"USE_RERANK = {USE_RERANK}" + (f" (candidate_pool={RERANK_CANDIDATE_POOL})" if USE_RERANK else ""))
    print("Loading clause-type data...")
    all_data = load_all_examples()
    if not all_data:
        return

    unique_texts = build_unique_contract_texts(all_data)
    total_slots = sum(len(v) for v in all_data.values())
    print(f"\n{len(unique_texts)} unique contracts across all clause types "
          f"(vs {total_slots} total contract-slots if embedded separately "
          f"per clause type -- that's the redundant work we're now skipping)")

    if MAX_UNIQUE_CONTRACTS is not None and len(unique_texts) > MAX_UNIQUE_CONTRACTS:
        import random
        random.seed(42)
        keep_titles = set(random.sample(list(unique_texts), MAX_UNIQUE_CONTRACTS))
        unique_texts = {t: unique_texts[t] for t in keep_titles}
        print(f"MAX_UNIQUE_CONTRACTS set -- sampled down to {len(unique_texts)} "
              f"unique contracts (results will be noisier, not your reported number)")

    print(f"\nEmbedding {len(unique_texts)} unique contracts (once each)...")
    collection, contract_chunks = embed_all_contracts_once(unique_texts)

    print()
    all_results = []
    for slug, examples in all_data.items():
        print(f"Evaluating: {slug} ...")
        result = evaluate_clause_type(slug, examples, CLAUSE_QUERIES[slug],
                                       collection, contract_chunks)
        all_results.append(result)
        print(f"  {result}\n")

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    header = f"{'clause_type':32s} {'n':>5s}  " + "  ".join(f"recall@{k}" for k in K_VALUES)
    print(header)
    for r in all_results:
        row = f"{r['clause_type']:32s} {r['n']:5d}  " + \
              "  ".join(f"{r[f'recall@{k}']:8.3f}" for k in K_VALUES)
        print(row)

    print()
    for k in K_VALUES:
        avg = sum(r[f"recall@{k}"] for r in all_results) / len(all_results)
        print(f"Overall average recall@{k}: {avg:.3f}")


if __name__ == "__main__":
    main()