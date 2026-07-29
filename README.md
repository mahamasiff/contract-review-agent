# Vendor Contract Intelligence Platform 

## Project Layout

phase3/
├── backend/
│   ├── main.py                  # FastAPI endpoints 
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── loader.py            # PDF -> raw text
│   │   └── segment.py           # Legal clause-aware chunking
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── runner.py            # Plan-and-Execute / ReAct loop
│   │   └── verification.py      # Second-pass verification step
│   ├── mcp_server/
│   │   ├── __init__.py
│   │   └── tools.py             # MCP playbook & precedent tools
│   ├── memory/
│   │   ├── __init__.py
│   │   └── store.py             # User override memory / state persistence
│   └── models/
│       ├── __init__.py
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