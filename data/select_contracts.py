"""
Select 10-15 contracts for the hand-labeled playbook-compliance eval set.

Strategy:
  1. Load all 7 clause-type files, build a per-contract coverage map
     (which of the 7 clause types each contract actually has present).
  2. Report the REAL coverage distribution -- don't assume "has all 7"
     contracts exist; find out.
  3. Pick the highest-coverage contracts as the core set (more clause
     types present per contract = more labeled verdicts per contract =
     better use of your labeling time).
  4. Separately pick a few contracts that are missing DIFFERENT clause
     types from each other, so the eval set also tests "correctly says
     not present" across a spread of clause types, not just one.

Run from the project root:
    python data/select_eval_contracts.py
"""

import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(PROJECT_ROOT) == "data":
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")

CLAUSE_SLUGS = [
    "renewal_term",
    "termination_for_convenience",
    "cap_on_liability",
    "uncapped_liability",
    "minimum_commitment",
    "audit_rights",
    "governing_law",
]

CORE_SET_SIZE = 11   # high-coverage contracts
EDGE_CASE_SIZE = 3    # deliberately-missing-clauses contracts

# Domain-fit filter: CUAD spans 41 clause categories across ALL kinds of
# commercial contracts (distributor, franchise, pharma collaboration,
# manufacturing/supply, sponsorship, etc). Our playbook (data/playbook/
# vendor_playbook.md) is written for a vendor/SaaS procurement deal --
# scoring a franchise or pharma collaboration agreement against it is
# apples-to-oranges. These keyword lists narrow the candidate pool to
# contracts whose title suggests a software/services vendor relationship
# before ranking by clause coverage. Title-matching is a blunt instrument
# (some hits will still be a bad fit, e.g. finance-industry "maintenance"
# agreements) -- treat this as a first pass, then skim survivors' actual
# clause text before finalizing the eval set.
DOMAIN_ALLOW_KEYWORDS = [
    "SERVICES AGREEMENT", "SERVICE AGREEMENT", "HOSTING AGREEMENT",
    "MAINTENANCE AGREEMENT", "SOFTWARE", "MASTER SERVICE",
    "LICENSE AGREEMENT", "OUTSOURCING AGREEMENT", "SUBSCRIPTION",
]
DOMAIN_DENY_KEYWORDS = [
    # non-vendor contract types that happen to share a keyword above
    "CONTENT LICENSE", "TRADEMARK LICENSE", "FRANCHISE", "SPONSORSHIP",
    "ENDORSEMENT", "MANUFACTURING", "SUPPLY", "TRANSPORTATION",
    "AGENCY AGREEMENT", "JOINT VENTURE", "COLLABORATION",
    "DEVELOPMENT AGREEMENT", "STRATEGIC ALLIANCE", "PROMOTION",
    "CO-BRANDING", "AFFILIATE", "DISTRIBUTOR", "RESELLER", "CONSULTING",
    "JOINT FILING", "MARKETING AGREEMENT", "COOPERATION AGREEMENT",
    # finance/insurance/construction "maintenance" agreements that are
    # not about software/IT (capital maintenance, fund servicing, etc)
    "CAPITAL MAINTENANCE", "YIELD MAINTENANCE", "NET INVESTMENT INCOME",
    "FLEET MAINTENANCE", "OPERATIONS AND MAINTENANCE",
    "OPERATION AND MAINTENANCE", "CONSTRUCTION AND MAINTENANCE",
    "COMPLETION AND LIQUIDITY", "MANAGEMENT AND MAINTENANCE",
    "SEPARATE ACCOUNT", "VARIABLE ANNUITY", "MORTGAGE BACKED",
]


def passes_domain_filter(title):
    upper = title.upper()
    if not any(kw in upper for kw in DOMAIN_ALLOW_KEYWORDS):
        return False
    if any(kw in upper for kw in DOMAIN_DENY_KEYWORDS):
        return False
    return True


# CUAD's "contract" title field is often just a generic exhibit label
# (e.g. "_Maintenance Agreement") that gives no hint of the real subject
# matter -- an aircraft maintenance contract and a software maintenance
# contract look identical by title. Confirmed by manually reading the
# selected set: title filtering alone let through pharma manufacturing
# outsourcing, a drug licensing deal, aircraft maintenance, power-plant
# O&M, and a notes financing arrangement. This scans the actual contract
# body for unambiguous non-software industry markers as a second gate.
BODY_DENY_KEYWORDS = [
    "PHARMACEUTICAL", "DRUG PRODUCT", "CLINICAL TRIAL", "BIOLOGIC",
    "AIRCRAFT", "AVIATION", "POWER PLANT", "GENERATION FACILITY",
    "RENEWABLE ENERGY", "SUBORDINATED NOTES", "PROMISSORY NOTE",
    "BROADCAST", "TELEVISION STATION", "FEDERAL COMMUNICATIONS COMMISSION",
    "MANUFACTURING OUTSOURCING", "CONTRACT MANUFACTURING",
]


def passes_body_filter(context_text):
    upper = context_text.upper()
    return not any(kw in upper for kw in BODY_DENY_KEYWORDS)


def load_all():
    """slug -> {contract_title: is_present_bool}"""
    presence = {}
    for slug in CLAUSE_SLUGS:
        path = os.path.join(DATA_DIR, f"{slug}.json")
        if not os.path.exists(path):
            print(f"SKIPPING {slug}: {path} not found")
            continue
        with open(path) as f:
            data = json.load(f)
        presence[slug] = {ex["contract"]: (not ex["is_impossible"]) for ex in data}
    return presence


def load_contexts():
    """contract_title -> full contract text (context field), deduped --
    used for the body-text domain filter, not just coverage counting."""
    contexts = {}
    for slug in CLAUSE_SLUGS:
        path = os.path.join(DATA_DIR, f"{slug}.json")
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for ex in data:
            contexts.setdefault(ex["contract"], ex["context"])
    return contexts


def build_coverage_table(presence):
    """contract_title -> {slug: bool, ..., 'coverage_count': int}"""
    all_contracts = set()
    for slug_map in presence.values():
        all_contracts.update(slug_map.keys())

    table = {}
    for contract in all_contracts:
        row = {}
        count = 0
        for slug in CLAUSE_SLUGS:
            has_it = presence.get(slug, {}).get(contract, False)
            row[slug] = has_it
            count += has_it
        row["coverage_count"] = count
        table[contract] = row
    return table


def print_distribution(table):
    from collections import Counter
    counts = Counter(row["coverage_count"] for row in table.values())
    print("Coverage distribution (how many of the 7 clause types per contract):")
    for n in range(7, -1, -1):
        print(f"  {n}/7 clause types present: {counts.get(n, 0)} contracts")
    print()


def pick_core_set(table, n):
    # Secondary sort key (title) makes tie-breaking deterministic --
    # table's own key order depends on set() iteration, which is
    # randomized per-process, so without this the picks among
    # equal-coverage contracts would change on every run.
    ranked = sorted(table.items(), key=lambda kv: (-kv[1]["coverage_count"], kv[0]))
    return [title for title, row in ranked[:n]]


def pick_edge_cases(table, core_titles, n):
    """Pick contracts that are each missing a DIFFERENT clause type.
    Iterates clause-type-first (not contract-first) so variety is
    guaranteed rather than hoped for: for each clause type not yet
    covered by an existing pick, find the highest-coverage remaining
    contract that's missing exactly that clause type."""
    candidates = sorted(
        [(title, row) for title, row in table.items() if title not in core_titles],
        key=lambda kv: (-kv[1]["coverage_count"], kv[0]),
    )

    picked = []
    picked_titles = set()
    targeted_slugs = set()

    for slug in CLAUSE_SLUGS:
        if len(picked) >= n:
            break
        if slug in targeted_slugs:
            continue  # already have a pick covering this missing-clause case

        for title, row in candidates:
            if title in picked_titles or row[slug]:
                continue  # already picked, or this contract HAS this clause
            picked.append(title)
            picked_titles.add(title)
            # this contract may miss other slugs too -- credit those as
            # covered so we don't waste a later pick chasing the same gap
            targeted_slugs |= {s for s in CLAUSE_SLUGS if not row[s]}
            break

    return picked


def main():
    presence = load_all()
    if not presence:
        return

    table = build_coverage_table(presence)
    print(f"Total unique contracts across all 7 clause files: {len(table)}\n")
    print_distribution(table)

    fit_table = {t: row for t, row in table.items() if passes_domain_filter(t)}
    print(f"Domain-fit filter (vendor/software/services-shaped titles): "
          f"{len(fit_table)}/{len(table)} contracts pass\n")

    contexts = load_contexts()
    before = len(fit_table)
    fit_table = {t: row for t, row in fit_table.items()
                 if passes_body_filter(contexts.get(t, ""))}
    print(f"Body-text filter (rejects pharma/aircraft/power-plant/notes "
          f"deals that slipped past the title filter): "
          f"{len(fit_table)}/{before} contracts pass\n")
    print_distribution(fit_table)

    core = pick_core_set(fit_table, CORE_SET_SIZE)
    edge_cases = pick_edge_cases(fit_table, set(core), EDGE_CASE_SIZE)

    selection = {}
    for title in core:
        selection[title] = {"role": "core", **table[title]}
    for title in edge_cases:
        selection[title] = {"role": "edge_case", **table[title]}

    print(f"CORE SET ({len(core)} contracts, ranked by coverage):")
    for title in core:
        row = table[title]
        present = [s for s in CLAUSE_SLUGS if row[s]]
        print(f"  [{row['coverage_count']}/7] {title}")
        print(f"          has: {', '.join(present)}")

    print(f"\nEDGE-CASE SET ({len(edge_cases)} contracts, deliberately missing varied clauses):")
    for title in edge_cases:
        row = table[title]
        missing = [s for s in CLAUSE_SLUGS if not row[s]]
        print(f"  [{row['coverage_count']}/7] {title}")
        print(f"          missing: {', '.join(missing)}")

    out_path = os.path.join(DATA_DIR, "eval_contracts_selection.json")
    with open(out_path, "w") as f:
        json.dump(selection, f, indent=2)
    print(f"\nSaved selection ({len(selection)} contracts total) -> {out_path}")
    print("Use this as the seed list for data/eval_contracts/ hand-labeling.")


if __name__ == "__main__":
    main()