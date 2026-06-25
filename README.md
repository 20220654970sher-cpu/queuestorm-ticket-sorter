# QueueStorm Ticket Sorter

Production-grade CPU-friendly FastAPI service for the SUST CSE Carnival 2026 Codex Community Hackathon – QueueStorm Warmup Mock Preliminary Round.

The service accepts a customer support ticket and returns:

- `case_type`
- `severity`
- `department`
- `agent_summary`
- `human_review_required`
- `confidence`

## Recommended Approach

This project uses a **Hybrid Rule + TF-IDF Logistic Regression** system.

| Approach | Accuracy | CPU | RAM | Latency | Deployment | Maintainability | Hackathon Fit |
|---|---:|---:|---:|---:|---|---|---|
| Pure Rule-Based | High on obvious cases, weak on typos | Very low | Very low | Excellent | Very easy | Medium as rules grow | Good baseline |
| TF-IDF + Logistic Regression | Good with seed data | Low | Low | Excellent | Easy | High | Strong |
| MiniLM Embeddings | Better semantic matching | Medium | Medium | Good | Heavier | Medium | Good but risky on 8GB |
| Hybrid Rule + ML | Best balance | Low | Low | Excellent | Easy | High | **Best** |

Why hybrid wins:

- Rules guarantee fintech-critical mappings such as phishing → fraud_risk.
- TF-IDF Logistic Regression improves typo and phrasing tolerance.
- No GPU required.
- Startup and inference are lightweight enough for an 8GB Windows laptop.

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for Mermaid diagrams:

- Request Flow Diagram
- System Architecture Diagram
- Component Diagram
- Deployment Diagram

## Folder Structure

```text
queuestorm-ticket-sorter/
├── app/
│   ├── api/v1/routes.py
│   ├── config/settings.py
│   ├── middleware/request_id.py
│   ├── models/domain.py
│   ├── schemas/
│   ├── services/
│   ├── utils/
│   └── main.py
├── data/training_seed.csv
├── docs/architecture.md
├── notebooks/
├── scripts/
├── tests/
├── .github/workflows/ci.yml
├── Dockerfile
├── docker-compose.yml
├── render.yaml
├── railway.json
├── requirements.txt
├── pyproject.toml
├── .flake8
├── .env.example
└── .gitignore
```

## Local Setup on Windows

### 1. Create virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Train model artifact

```bash
python scripts/train_model.py
```

The app can also train automatically on first startup if the artifact does not exist.

### 3. Run API

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

## API Examples

### Health

```bash
curl http://127.0.0.1:8000/health
```

Expected:

```json
{
  "status": "healthy"
}
```

### Sort Ticket

```bash
curl -X POST http://127.0.0.1:8000/sort-ticket \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "T-001",
    "channel": "app",
    "locale": "en",
    "message": "I sent 5000 taka to a wrong number this morning, please help me get it back"
  }'
```

Expected shape:

```json
{
  "ticket_id": "T-001",
  "case_type": "wrong_transfer",
  "severity": "high",
  "department": "dispute_resolution",
  "agent_summary": "Customer reports sending money to an incorrect recipient involving approximately 5,000 BDT and requests recovery assistance.",
  "human_review_required": false,
  "confidence": 0.98
}
```

## Docker

### Build

```bash
docker build -t queuestorm-ticket-sorter:latest .
```

### Run

```bash
docker run --rm -p 8000:8000 --env-file .env.example queuestorm-ticket-sorter:latest
```

### Docker Compose

```bash
docker compose up --build
```

## Testing

```bash
pytest
```

Format/lint:

```bash
black app tests scripts
isort app tests scripts
flake8 app tests scripts
```

Smoke test after server is running:

```bash
python scripts/smoke_test.py
```

Simple load test:

```bash
python scripts/load_test.py --requests 200 --workers 20
```

## Render Deployment

1. Push this repository to GitHub.
2. In Render, create a new Web Service from the repo.
3. Choose Docker runtime or use `render.yaml` blueprint.
4. Set health check path to `/health`.
5. Environment variables:

```text
APP_ENV=production
LOG_LEVEL=INFO
APP_ENABLE_AUDIT=false
CONFIDENCE_THRESHOLD=0.62
```

## Railway Deployment

Option A — GitHub:

1. Create a Railway project.
2. Connect the GitHub repository.
3. Railway will use the Dockerfile/`railway.json`.
4. Set the health check path to `/health`.

Option B — CLI:

```bash
railway login
railway init
railway up
```

## Production Commands

Local production-style run:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

On cloud platforms that expose `$PORT`:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1
```

Use `--workers 1` for the target 8GB laptop. For cloud CPU instances, benchmark before increasing workers.

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `APP_ENV` | `development` | Runtime environment |
| `LOG_LEVEL` | `INFO` | JSON log verbosity |
| `MODEL_PATH` | `artifacts/ticket_classifier.joblib` | Model artifact path |
| `TRAINING_DATA_PATH` | `data/training_seed.csv` | Seed training data |
| `CONFIDENCE_THRESHOLD` | `0.62` | ML fallback threshold |
| `APP_ENABLE_AUDIT` | `true` | SQLite request/response audit toggle |
| `SQLITE_PATH` | `data/tickets.db` | SQLite audit database path |

## Submission Checklist

- [ ] `/health` returns `{"status":"healthy"}`.
- [ ] `/sort-ticket` returns all required fields.
- [ ] Phishing cases always route to `fraud_risk`.
- [ ] Payment failed cases route to `payments_ops`.
- [ ] Wrong transfers route to `dispute_resolution`.
- [ ] Critical or phishing cases set `human_review_required=true`.
- [ ] Summaries never ask for OTP, PIN, passwords, or card numbers.
- [ ] Docker image builds successfully.
- [ ] Tests pass.
- [ ] README contains run commands and examples.
- [ ] Deployed URL is included in final submission.

## Final Score Maximization Tips

- Demo with the Swagger UI at `/docs` and show both root and `/api/v1` routes.
- Keep examples ready for wrong transfer, failed payment, refund, phishing, Bangla, and typo cases.
- Show the architecture diagrams in `docs/architecture.md`.
- Mention that the classifier is CPU-only and avoids GPU LLM dependency.
- Mention that the safety filter prevents credential collection in summaries.
- Run tests live before submission if possible.
