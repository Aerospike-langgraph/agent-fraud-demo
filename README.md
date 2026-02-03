# Agentic Fraud Investigation Demo

A LangGraph-based fraud investigation workflow that demonstrates adaptive graph expansion using Aerospike Graph, with real-time streaming UI and AI-powered reasoning via Mistral/Ollama.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Frontend (React/Next.js)                         │
│  ┌──────────────┐  ┌──────────────────────┐  ┌───────────────────────┐  │
│  │   Stepper    │  │   Graph Explorer     │  │  Trace/Evidence/Report│  │
│  │  (Workflow)  │  │   (Force Graph)      │  │      (Tabs)           │  │
│  └──────────────┘  └──────────────────────┘  └───────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                              SSE Events
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                         Backend (FastAPI + LangGraph)                    │
│                                                                          │
│  LoadContext → TraverseGraph → ScoreNeighbors → SelectCandidates        │
│                      ↑                               │                   │
│                      │                               ▼                   │
│                      └────────────────────── DecideExpand (LLM)         │
│                                                      │                   │
│                                                      ▼                   │
│  BuildSubgraph → BuildEvidence → GenerateReport (LLM) → END             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
              ┌─────▼─────┐                 ┌───────▼───────┐
              │ Aerospike │                 │   Ollama      │
              │   Graph   │                 │  (Mistral)    │
              └───────────┘                 └───────────────┘
```

## Key Features

- **LangGraph Workflow**: Multi-step investigation with conditional loops
- **Adaptive Expansion**: LLM decides when to stop based on cost/benefit
- **Real-time Streaming**: SSE events for live UI updates
- **Graph Visualization**: Interactive force-directed graph
- **AI Reports**: Mistral-generated investigation reports

## Prerequisites

- Docker & Docker Compose
- Ollama with Mistral model (for LLM features)
- Synthetic fraud data (included in parent `data/` directory)

## Quick Start

### 1. Start Ollama with Mistral

```bash
# Install Ollama if not already installed
# https://ollama.ai/download

# Pull and run Mistral
ollama pull mistral
ollama serve
```

### 2. Start the Services

```bash
cd agentic-fraud-demo
docker-compose up -d
```

### 3. Load Graph Data

After services are healthy, load the synthetic fraud data into the graph:

```bash
# The data loader endpoint will bulk load CSV data
curl -X POST "http://localhost:4000/api/bulk-load-csv" \
  -H "Content-Type: application/json"
```

### 4. Access the UI

Open http://localhost:3010 in your browser.

## API Endpoints

### Alerts
- `GET /api/alerts` - List all fraud alerts
- `GET /api/alerts/{alert_id}` - Get specific alert

### Cases
- `POST /api/case/start` - Create new investigation case
- `GET /api/case/{case_id}` - Get case status and results
- `POST /api/case/{case_id}/run` - Start workflow execution
- `GET /api/case/{case_id}/stream` - SSE stream of workflow events

### Utilities
- `GET /api/workflow/structure` - Get workflow node/edge structure
- `GET /api/manifest` - Get ground truth data

## Workflow Nodes

1. **LoadContext**: Initialize with alert and suspect data
2. **TraverseGraph**: Expand graph via device/IP/transaction edges
3. **ScoreNeighbors**: Calculate risk scores for discovered accounts
4. **SelectCandidates**: Choose high-risk candidates
5. **DecideExpand**: LLM decides whether to continue expansion
6. **BuildSubgraph**: Construct final fraud ring
7. **BuildEvidence**: Generate proof metrics
8. **GenerateReport**: AI-powered report synthesis

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `GRAPH_HOST_ADDRESS` | `localhost` | Aerospike Graph host |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API URL |
| `OLLAMA_MODEL` | `mistral` | LLM model to use |
| `DATA_DIR` | `/data/synthetic_fraud_data` | Path to CSV data |

## Development

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 4000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## License

MIT
