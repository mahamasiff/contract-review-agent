# Vendor Contract Intelligence Platform 

## Project Layout

```text
phase3/
├── backend/
│   ├── main.py                  # FastAPI endpoints 
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
│   ├── playbook/                # Rule definitions (JSON/YAML)
│   └── eval_contracts/          # evaluation dataset
├── eval/
│   └── run_eval.py              # Evaluation harness
├── .env.example
├── prompts.md
├── README.md
├── requirements.txt
└── .gitignore