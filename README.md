# Vendor Contract Intelligence Platform

An AI-powered system that reviews vendor/procurement contracts against a
company's internal playbook, flags deviations, and surfaces missing or
non-standard clauses — automating the first-pass review that procurement
and legal-ops teams currently do manually.

---

## Table of Contents

- [Overview](#overview)
- [Clause Types Covered](#clause-types-covered)
- [Architecture](#architecture)
- [Project Layout](#project-layout)
- [Evaluation Methodology](#evaluation-methodology)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Data Sources & Attribution](#data-sources--attribution)
- [Roadmap](#roadmap)
- [Tech Stack](#tech-stack)
- [License](#license)

---

## Overview

core workflow: upload a
contract → segment into clauses → compare against internal playbook →
receive a report of violations, missing clauses, and suggested wording etc.

## Clause Types Covered

This project focuses on 7 clause types, chosen to be commercially
significant for vendor/procurement risk review while spanning a range of
extraction difficulty (from formulaic/easy to semantically hard):

| Clause Type | What it governs |
|---|---|
| **Renewal Term** | Whether the agreement auto-renews, and under what notice |
| **Termination For Convenience** | Whether either party can exit without cause |
| **Cap On Liability** | The maximum liability either party can owe |
| **Uncapped Liability** | Carve-outs where liability isn't subject to any cap |
| **Minimum Commitment** | Required minimum spend, volume, or purchase commitment |
| **Audit Rights** | Whether either party can audit the other's compliance/records |
| **Governing Law** | Which jurisdiction's law governs the agreement |


## Architecture

*(Elaborate: short description + diagram of the pipeline — PDF ingestion
→ clause-aware segmentation → retrieval (ChromaDB) → extraction/
verification (Claude) → playbook compliance check via MCP → agent loop
→ frontend. Can link to `prompts.md` for prompt-level detail.)*

## Project Layout

```text
phase3/
├── backend/
│   ├── main.py                  # FastAPI endpoints
│   ├── vectorstore.py           # Chunking + ChromaDB embed/store/query (shared by eval + MCP server)
│   ├── ingestion/
│   │   ├── loader.py            # PDF -> raw text
│   │   └── segment.py           # Legal clause-aware chunking
│   ├── agent/
│   │   ├── runner.py            # Plan-and-Execute / ReAct loop
│   │   └── verification.py      # Second-pass verification step
│   ├── mcp_server/
│   │   └── tools.py             # MCP playbook & precedent tools
│   ├── memory/
│   │   └── store.py             # User override memory / state persistence
│   └── models/
│       └── clients.py           # Claude & Ollama SDK wrappers
├── frontend/
│   └── app.py                   # Gradio app calling FastAPI endpoints via HTTP
├── data/
│   ├── prepare_cuad_data.py     # Fetches + filters CUAD into per-clause JSON files
│   ├── renewal_term.json        # CUAD subset: contract text + ground truth, per clause type
│   ├── termination_for_convenience.json
│   ├── cap_on_liability.json
│   ├── uncapped_liability.json
│   ├── minimum_commitment.json
│   ├── audit_rights.json
│   ├── governing_law.json
│   ├── playbook/
│   │   └── vendor_playbook.md   # Default/fallback/escalation rules, all 7 clause types
│   └── eval_contracts/          # Hand-labeled contracts for playbook-compliance eval (10-15)
├── eval/
│   ├── run_retrieval_eval.py    # Retrieval eval: recall@k per clause type (CUAD-grounded)
│   ├── debug_retrieval_misses.py # Inspect individual retrieval misses (gold vs. retrieved)
│   └── run_compliance_eval.py   # Compliance eval against hand-labeled set (TODO)
├── chroma_store/                # Persisted embeddings (gitignored, regenerable)
├── .env.example
├── prompts.md
├── README.md
├── requirements.txt
├── pyproject.toml
└── .gitignore
```

## Evaluation Methodology

This project uses two distinct evaluation layers, since they answer
different questions and draw on different ground truth:

### 1. Extraction & Retrieval Eval (CUAD-grounded)

Uses the [CUAD dataset](#data-sources--attribution) for free, pre-labeled
ground truth on *where* each clause type appears in a contract.

- **Retrieval eval** (`eval/run_retrieval_eval.py`): for each clause
  type, chunks + embeds contracts, queries with a clause-specific
  description, and checks whether the correct chunk is retrieved.
  Reported as recall@1 / @3 / @5 per clause type.
- **Extraction eval** : given a retrieved chunk, does an LLM
  correctly confirm/extract the actual clause text (or correctly say
  "not present")?

### 2. Playbook Compliance Eval (hand-labeled)

CUAD has no concept of "compliant with our company's playbook" — that
judgment only exists relative to the specific rules in
`data/playbook/vendor_playbook.md`. This layer uses a held-out set of
10-15 hand-labeled contracts (`data/eval_contracts/`), split into a dev
set (for iterating) and a held-out test set (touched only for the final
reported number), scored on accuracy/precision/recall of
violation-detection against the playbook.


## Getting Started

```bash
# install dependencies
uv sync   # or: pip install -r requirements.txt

# fetch + filter CUAD into per-clause JSON files
python data/prepare_cuad_data.py

# run the retrieval eval
python eval/run_retrieval_eval.py
```

*(Elaborate: `.env` setup / required API keys once agent + MCP server
are wired in.)*

## Usage

*(TODO once `backend/main.py` + `frontend/app.py` exist — how to run the
full app, upload a contract, and read the output report.)*

## Data Sources & Attribution

- **[CUAD (Contract Understanding Atticus Dataset)](https://github.com/TheAtticusProject/cuad)**
  — 510 real commercial contracts, human-labeled across 41 clause
  categories. Used here for extraction/retrieval ground truth. CC BY 4.0.
- **[Common Paper, "What goes into a SaaS contract playbook"](https://commonpaper.com/blog/contract-playbook-template/)**
  — structural inspiration for `playbook`'s default/fallback/
  escalation format; several positions adapted (and inverted, since
  Common Paper's playbook is vendor-side and this project's playbook is
  buyer-side) from their published template.
- **[Contract Nerds, "The Great 8" SaaS playbook webinar](https://contractnerds.com/how-to-build-and-use-a-saas-agreement-playbook-8-common-issues-and-fallback-positions/)**
  — additional market-standard detail on liability cap structures.

## Roadmap

- [ ] Week 1: Retrieval pipeline + eval (recall@k across 7 clause types)
- [ ] Week 1: Playbook rules (all 7 clause types, sourced + adapted)
- [ ] Week 1: Hand-labeled compliance eval set (10-15 contracts)
- [ ] Week 1: Extraction eval (LLM reads retrieved chunk, confirms clause)
- [ ] Week 1: PDF ingestion (`ingestion/loader.py`)
- [ ] Week 2: MCP server (playbook + precedent retrieval tools)
- [ ] Week 2: Agent loop (Plan-and-Execute / ReAct, `agent/runner.py`)
- [ ] Week 3: Verification pass (`agent/verification.py`)
- [ ] Week 3: Override memory (`memory/store.py`)
- [ ] Week 3.5: Frontend (Gradio) + end-to-end integration + demo

## Tech Stack

