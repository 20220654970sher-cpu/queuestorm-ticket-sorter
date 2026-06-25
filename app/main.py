from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from app.api.v1.routes import router as v1_router
from app.config.settings import get_settings
from app.middleware.request_id import RequestIDMiddleware
from app.schemas.error import ErrorResponse
from app.services.classifier import TicketSortingService
from app.utils.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    service = TicketSortingService(settings)
    app.state.ticket_service = service
    service.warmup()
    logger.info("application_started", extra={"environment": settings.environment})
    yield
    logger.info("application_stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="CPU-friendly fintech support ticket classifier for QueueStorm.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # Compatibility for tests that instantiate TestClient without lifespan context.
    app.state.ticket_service = TicketSortingService(settings)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        error = ErrorResponse(
            error="validation_error",
            detail=exc.errors(),
            request_id=request_id,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error.model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.exception("unhandled_exception", extra={"request_id": request_id})
        error = ErrorResponse(
            error="internal_server_error",
            detail="Unexpected server error",
            request_id=request_id,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error.model_dump(),
        )

    @app.get("/", response_class=HTMLResponse, tags=["service"])
    def root() -> HTMLResponse:
        return HTMLResponse(
            """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>QueueStorm Ticket Sorter</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f8fb;
      --panel: #ffffff;
      --text: #172033;
      --muted: #5d6980;
      --line: #d8deea;
      --accent: #1769e0;
      --accent-dark: #0f4fb0;
      --danger: #b42318;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    header {
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }
    .wrap {
      width: min(1120px, calc(100% - 32px));
      margin: 0 auto;
    }
    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 18px 0;
    }
    h1 {
      margin: 0;
      font-size: clamp(24px, 4vw, 38px);
      line-height: 1.1;
    }
    .status {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border: 1px solid #b7e2c5;
      border-radius: 999px;
      padding: 8px 12px;
      background: #edf9f1;
      color: #146c2e;
      font-weight: 700;
      white-space: nowrap;
    }
    main { padding: 28px 0 40px; }
    .intro {
      display: grid;
      grid-template-columns: 1.2fr .8fr;
      gap: 20px;
      align-items: stretch;
      margin-bottom: 20px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 20px;
    }
    .lead {
      margin: 12px 0 0;
      color: var(--muted);
      font-size: 17px;
      line-height: 1.6;
      max-width: 760px;
    }
    .metrics {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      background: #fbfcff;
    }
    .metric strong {
      display: block;
      font-size: 20px;
      margin-bottom: 4px;
    }
    .metric span {
      color: var(--muted);
      font-size: 13px;
    }
    .workspace {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(320px, .9fr);
      gap: 20px;
    }
    label {
      display: block;
      margin: 14px 0 7px;
      font-weight: 700;
    }
    input, select, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 11px 12px;
      font: inherit;
      color: var(--text);
      background: #fff;
    }
    textarea {
      min-height: 170px;
      resize: vertical;
      line-height: 1.5;
    }
    .row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    button {
      width: 100%;
      margin-top: 16px;
      border: 0;
      border-radius: 8px;
      padding: 12px 16px;
      background: var(--accent);
      color: white;
      font-weight: 800;
      cursor: pointer;
    }
    button:hover { background: var(--accent-dark); }
    button:disabled { opacity: .65; cursor: wait; }
    .quick {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 12px;
    }
    .quick button {
      width: auto;
      margin: 0;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--text);
      font-weight: 700;
      padding: 8px 10px;
    }
    .result {
      min-height: 310px;
      display: grid;
      align-content: start;
      gap: 12px;
    }
    .empty {
      color: var(--muted);
      line-height: 1.6;
    }
    .result-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    .field {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      background: #fbfcff;
      overflow-wrap: anywhere;
    }
    .field span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      font-weight: 800;
      margin-bottom: 6px;
    }
    .summary { grid-column: 1 / -1; }
    .error {
      color: var(--danger);
      font-weight: 700;
    }
    footer {
      color: var(--muted);
      padding: 8px 0 32px;
      font-size: 14px;
    }
    footer a { color: var(--accent); font-weight: 700; }
    @media (max-width: 820px) {
      .intro, .workspace, .row, .result-grid { grid-template-columns: 1fr; }
      .topbar { align-items: flex-start; flex-direction: column; }
    }
  </style>
</head>
<body>
  <header>
    <div class="wrap topbar">
      <h1>QueueStorm Ticket Sorter</h1>
      <div class="status">Online</div>
    </div>
  </header>
  <main class="wrap">
    <section class="intro">
      <div class="panel">
        <h2>Classify fintech support tickets instantly</h2>
        <p class="lead">
          Enter a customer ticket to predict the case type, severity, department,
          agent summary, review requirement, and model confidence.
        </p>
      </div>
      <div class="panel metrics" aria-label="Service capabilities">
        <div class="metric"><strong>Hybrid</strong><span>Rules + TF-IDF Logistic Regression</span></div>
        <div class="metric"><strong>CPU</strong><span>No GPU or external LLM needed</span></div>
        <div class="metric"><strong>Safe</strong><span>Fraud and credential-risk handling</span></div>
        <div class="metric"><strong>FastAPI</strong><span>Docs available at /docs</span></div>
      </div>
    </section>

    <section class="workspace">
      <form class="panel" id="ticket-form">
        <div class="row">
          <div>
            <label for="ticket-id">Ticket ID</label>
            <input id="ticket-id" value="T-WEB-001" required>
          </div>
          <div>
            <label for="channel">Channel</label>
            <select id="channel">
              <option value="app">App</option>
              <option value="sms">SMS</option>
              <option value="email">Email</option>
              <option value="call_center">Call Center</option>
            </select>
          </div>
        </div>
        <label for="locale">Locale</label>
        <select id="locale">
          <option value="en">English</option>
          <option value="bn">Bangla</option>
        </select>
        <label for="message">Customer Message</label>
        <textarea id="message" required>I sent 5000 taka to a wrong number this morning, please help me get it back</textarea>
        <div class="quick" aria-label="Example tickets">
          <button type="button" data-example="wrong">Wrong transfer</button>
          <button type="button" data-example="payment">Payment failed</button>
          <button type="button" data-example="fraud">Fraud risk</button>
        </div>
        <button id="submit-button" type="submit">Sort Ticket</button>
      </form>

      <section class="panel result" aria-live="polite">
        <h2>Classification Result</h2>
        <div id="result" class="empty">
          Submit a ticket to see the predicted routing decision here.
        </div>
      </section>
    </section>
  </main>
  <footer class="wrap">
    API docs: <a href="/docs">/docs</a> | Health: <a href="/health">/health</a>
  </footer>

  <script>
    const examples = {
      wrong: "I sent 5000 taka to a wrong number this morning, please help me get it back",
      payment: "My payment failed but money was deducted from my wallet",
      fraud: "Someone called me and asked for my OTP and PIN. After that money was taken from my account."
    };

    document.querySelectorAll("[data-example]").forEach((button) => {
      button.addEventListener("click", () => {
        document.getElementById("message").value = examples[button.dataset.example];
      });
    });

    function renderResult(data) {
      const result = document.getElementById("result");
      result.className = "result-grid";
      result.innerHTML = `
        <div class="field"><span>Ticket ID</span>${data.ticket_id}</div>
        <div class="field"><span>Confidence</span>${Math.round(data.confidence * 100)}%</div>
        <div class="field"><span>Case Type</span>${data.case_type}</div>
        <div class="field"><span>Severity</span>${data.severity}</div>
        <div class="field"><span>Department</span>${data.department}</div>
        <div class="field"><span>Human Review</span>${data.human_review_required ? "Required" : "Not required"}</div>
        <div class="field summary"><span>Agent Summary</span>${data.agent_summary}</div>
      `;
    }

    document.getElementById("ticket-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = document.getElementById("submit-button");
      const result = document.getElementById("result");
      button.disabled = true;
      button.textContent = "Sorting...";
      result.className = "empty";
      result.textContent = "Classifying ticket...";

      const payload = {
        ticket_id: document.getElementById("ticket-id").value,
        channel: document.getElementById("channel").value,
        locale: document.getElementById("locale").value,
        message: document.getElementById("message").value
      };

      try {
        const response = await fetch("/sort-ticket", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || data.error || "Request failed");
        }
        renderResult(data);
      } catch (error) {
        result.className = "error";
        result.textContent = `Unable to classify ticket: ${error.message}`;
      } finally {
        button.disabled = false;
        button.textContent = "Sort Ticket";
      }
    });
  </script>
</body>
</html>
            """
        )

    app.include_router(v1_router, prefix=settings.api_prefix)
    # Root compatibility endpoints for hackathon judges that call exact paths.
    app.include_router(v1_router)
    return app


app = create_app()
