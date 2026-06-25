# Architecture

## Request Flow Diagram

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI API
    participant Validator as Pydantic Schemas
    participant Pre as Preprocessor
    participant Rules as Rule Engine
    participant ML as TF-IDF LR Model
    participant Policy as Review + Safety Policy
    participant Audit as SQLite Audit Log

    Client->>API: POST /sort-ticket
    API->>Validator: Validate request
    Validator->>Pre: Clean + normalize text
    Pre->>Rules: Detect high-precision fintech patterns
    Pre->>ML: Predict fallback intent/severity
    Rules->>Policy: Rule decision + reasons
    ML->>Policy: Probabilities
    Policy->>Policy: Combine, calibrate confidence, review flag
    Policy->>Audit: Optional request/response audit
    Policy-->>API: TicketResponse
    API-->>Client: JSON response
```

## System Architecture Diagram

```mermaid
flowchart LR
    User[Client / Judge Script] -->|HTTP JSON| LB[FastAPI + Uvicorn]
    LB --> MW[Middleware\nRequest ID, CORS, Trusted Host]
    MW --> API[API v1 Router\n/health, /sort-ticket]
    API --> Service[TicketSortingService]
    Service --> Pre[Preprocessing Pipeline]
    Service --> Rules[Keyword Rule Engine]
    Service --> ML[TF-IDF + Logistic Regression]
    Service --> Summary[Template Summary Generator]
    Service --> Safety[Safety Filter]
    Service --> Review[Human Review Policy]
    Service --> DB[(SQLite Local Audit)]
```

## Component Diagram

```mermaid
classDiagram
    class TicketRequest {
      ticket_id: str
      channel: str
      locale: str
      message: str
    }
    class TicketResponse {
      case_type: CaseType
      severity: Severity
      department: Department
      agent_summary: str
      human_review_required: bool
      confidence: float
    }
    class TicketSortingService
    class TicketPreprocessor
    class KeywordRuleEngine
    class TfidfLogisticTicketClassifier
    class AgentSummaryGenerator
    class SummarySafetyFilter
    class HumanReviewPolicy

    TicketSortingService --> TicketPreprocessor
    TicketSortingService --> KeywordRuleEngine
    TicketSortingService --> TfidfLogisticTicketClassifier
    TicketSortingService --> AgentSummaryGenerator
    TicketSortingService --> SummarySafetyFilter
    TicketSortingService --> HumanReviewPolicy
    TicketRequest --> TicketSortingService
    TicketSortingService --> TicketResponse
```

## Deployment Diagram

```mermaid
flowchart TB
    Dev[Developer Laptop\nWindows + Docker Desktop] --> GitHub[GitHub Repository]
    GitHub --> CI[GitHub Actions\nFormat, Lint, Test, Docker Build]
    GitHub --> Render[Render Web Service\nDocker Runtime]
    GitHub --> Railway[Railway Service\nDockerfile Builder]
    Render --> Health1[/health]
    Railway --> Health2[/health]
```

## Why Components Exist

- **FastAPI API layer:** Strict request/response schemas, auto docs, high-performance ASGI serving.
- **Pydantic schemas:** Prevent malformed payloads and guarantee the output contract.
- **Preprocessor:** Normalizes Bangla digits, mixed language text, punctuation, URLs, and typo-prone inputs.
- **Rule engine:** Handles high-risk fintech intents deterministically, especially phishing and wrong transfers.
- **TF-IDF Logistic Regression:** Lightweight ML fallback for natural language variation and typos.
- **Combiner:** Gives priority to security and money-movement rules while using ML probabilities for confidence.
- **Summary generator:** Template-based safe summaries without GPU or LLM dependency.
- **Safety filter:** Prevents unsafe summaries that ask for OTP, PIN, passwords, or card details.
- **Human review policy:** Enforces critical and phishing review rules.
- **SQLite audit log:** Local traceability for demos; replaceable with PostgreSQL/event logging in production.

## Scalability

- Keep one worker on 8GB laptop; use 2 workers only if CPU has spare capacity.
- Model is loaded once at startup and reused in memory.
- Rule matching is O(number of patterns), TF-IDF inference is fast for short support messages.
- For production traffic, run multiple container replicas behind a managed load balancer.
- Replace SQLite with PostgreSQL when multiple replicas need centralized audit storage.

## Error Handling

- Invalid JSON/schema errors return structured `422` responses with request ID.
- Unhandled exceptions return structured `500` without leaking internals.
- Audit-log failures are isolated and do not block ticket sorting.

## Logging Strategy

- JSON logs to stdout for Docker/Render/Railway collection.
- Request IDs are returned via `X-Request-ID` and included in error responses.
- Classification events log ticket ID, class, severity, and confidence.

## Performance Optimization

- Use TF-IDF + Logistic Regression instead of transformer inference by default.
- Character n-grams improve typo robustness without heavy embeddings.
- Cache/load model once during startup.
- Keep generated summaries template-based.
- Set Docker/Uvicorn workers to `1` for an 8GB laptop; scale horizontally in cloud.

## Security Considerations

- No OTP/PIN/password/card-number requests in generated summaries.
- Extra JSON fields are rejected.
- TrustedHost middleware is enabled.
- Secrets and environment config are kept out of Git via `.env`.
- Disable audit logging in public demo deployments if payload retention is not required.
