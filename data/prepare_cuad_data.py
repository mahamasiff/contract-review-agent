"""
Fetch CUADv1.json from the official CUAD GitHub repo and filter it down to
just the 7 clause types this project covers. Writes one JSON file per
clause type into data/ (this file's own directory).

Run once, from anywhere:
    python data/prepare_cuad_data.py

Each output file (e.g. data/renewal_term.json) is a list of dicts:
    {
        "contract": <contract title>,
        "context": <full contract text>,
        "is_impossible": <bool -- True means this contract has NO such clause>,
        "answers": [{"text": <clause text>, "answer_start": <char offset>}]
                   (empty list if is_impossible is True)
    }
"""

import json
import zipfile
import io
import os
import sys
import requests

CUAD_ZIP_URL = "https://github.com/TheAtticusProject/cuad/raw/main/data.zip"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))  # data/
PROJECT_ROOT = os.path.dirname(OUTPUT_DIR)
sys.path.insert(0, PROJECT_ROOT)

from backend.clause_types import CLAUSE_TYPES as _CANONICAL_CLAUSE_TYPES

# CUAD's category names are display names (e.g. "Renewal Term"), matched
# verbatim against the dataset's question text below -- derived from
# backend/clause_types.py rather than a separate hardcoded copy.
CLAUSE_TYPES = [c["display_name"] for c in _CANONICAL_CLAUSE_TYPES]


def download_cuad_json():
    print("Downloading CUAD dataset from GitHub...")
    resp = requests.get(CUAD_ZIP_URL)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        with z.open("CUADv1.json") as f:
            data = json.load(f)
    print(f"Loaded {len(data['data'])} contracts.")
    return data


def filter_category(data, category_name):
    """Pull out every contract's context + ground truth for one clause type."""
    results = []
    for contract in data["data"]:
        title = contract["title"]
        for para in contract["paragraphs"]:
            for qa in para["qas"]:
                # question format: Highlight the parts (if any) of this
                # contract related to "CATEGORY" that should be reviewed...
                qa_category = qa["question"].split('"')[1]
                if qa_category == category_name:
                    results.append({
                        "contract": title,
                        "context": para["context"],
                        "is_impossible": qa["is_impossible"],
                        "answers": qa["answers"],
                    })
    return results


def slugify(name):
    return name.lower().replace(" ", "_").replace("/", "-")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    data = download_cuad_json()

    print()
    for category in CLAUSE_TYPES:
        results = filter_category(data, category)
        n_positive = sum(not r["is_impossible"] for r in results)

        if n_positive == 0:
            print(f'WARNING: "{category}" matched 0 contracts -- check the '
                  f'exact spelling against CUAD\'s category list.')
            continue

        out_path = os.path.join(OUTPUT_DIR, f"{slugify(category)}.json")
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2)

        print(f"{category}: {len(results)} contracts total, "
              f"{n_positive} contain this clause -> {out_path}")


if __name__ == "__main__":
    main()