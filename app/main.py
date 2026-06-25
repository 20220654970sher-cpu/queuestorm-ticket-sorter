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
      --bg: #eef4fb;
      --panel: #ffffff;
      --panel-soft: #f8fbff;
      --text: #102033;
      --muted: #5f6f84;
      --line: #d7e1ee;
      --accent: #0b72e7;
      --accent-dark: #0758b5;
      --accent-soft: #e6f1ff;
      --success: #168a4a;
      --success-soft: #e8f8ef;
      --warning: #a65f00;
      --warning-soft: #fff5df;
      --danger: #b42318;
      --danger-soft: #fff0ee;
      --shadow: 0 18px 45px rgba(18, 44, 78, .12);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(11, 114, 231, .14), transparent 30%),
        linear-gradient(180deg, #f7fbff 0%, var(--bg) 44%, #f9fbfe 100%);
      color: var(--text);
    }
    a { color: inherit; }
    header {
      border-bottom: 1px solid rgba(215, 225, 238, .9);
      background: rgba(255, 255, 255, .86);
      backdrop-filter: blur(12px);
      position: sticky;
      top: 0;
      z-index: 10;
    }
    .wrap {
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
    }
    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 14px 0;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }
    .logo {
      display: grid;
      place-items: center;
      width: 42px;
      height: 42px;
      border-radius: 8px;
      color: #fff;
      background: linear-gradient(135deg, #0b72e7, #12a166);
      font-weight: 900;
      box-shadow: 0 10px 24px rgba(11, 114, 231, .22);
    }
    .brand strong {
      display: block;
      font-size: 18px;
    }
    .brand span {
      display: block;
      color: var(--muted);
      font-size: 13px;
    }
    h1 {
      margin: 0;
      font-size: clamp(34px, 6vw, 68px);
      line-height: 1.1;
    }
    h2 {
      margin: 0;
      font-size: 22px;
    }
    .status {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border: 1px solid #b8e4c9;
      border-radius: 999px;
      padding: 8px 12px;
      background: var(--success-soft);
      color: #146c3c;
      font-weight: 700;
      white-space: nowrap;
    }
    .navlinks {
      display: flex;
      gap: 10px;
      align-items: center;
    }
    .navlinks a {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 8px 12px;
      background: #fff;
      color: var(--muted);
      text-decoration: none;
      font-weight: 800;
      font-size: 13px;
    }
    main { padding: 32px 0 44px; }
    .hero {
      display: grid;
      grid-template-columns: minmax(0, 1.15fr) minmax(320px, .85fr);
      gap: 22px;
      align-items: stretch;
      margin-bottom: 22px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 20px;
      box-shadow: var(--shadow);
    }
    .hero-card {
      min-height: 330px;
      display: grid;
      align-content: center;
      padding: 34px;
      background:
        linear-gradient(135deg, rgba(11, 114, 231, .12), rgba(22, 138, 74, .12)),
        #ffffff;
    }
    .eyebrow {
      display: inline-flex;
      width: fit-content;
      border: 1px solid #bfd8f4;
      border-radius: 999px;
      padding: 8px 12px;
      color: #0758b5;
      background: var(--accent-soft);
      font-size: 13px;
      font-weight: 900;
      margin-bottom: 18px;
    }
    .lead {
      margin: 16px 0 0;
      color: var(--muted);
      font-size: 18px;
      line-height: 1.6;
      max-width: 760px;
    }
    .hero-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 24px;
    }
    .hero-actions a, .secondary-action {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 42px;
      border-radius: 8px;
      padding: 0 14px;
      text-decoration: none;
      font-weight: 900;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--text);
    }
    .hero-actions a:first-child {
      border-color: var(--accent);
      background: var(--accent);
      color: #fff;
    }
    .metrics {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      background: var(--panel-soft);
    }
    .metric strong {
      display: block;
      font-size: 24px;
      margin-bottom: 4px;
    }
    .metric span {
      color: var(--muted);
      font-size: 13px;
    }
    .submission-strip {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 22px;
    }
    .submission-item {
      display: flex;
      gap: 12px;
      align-items: center;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      background: rgba(255, 255, 255, .9);
      box-shadow: 0 10px 30px rgba(18, 44, 78, .08);
    }
    .submission-item .dot {
      display: grid;
      place-items: center;
      flex: 0 0 34px;
      width: 34px;
      height: 34px;
      border-radius: 8px;
      background: var(--accent-soft);
      color: var(--accent-dark);
      font-weight: 900;
    }
    .submission-item span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      font-weight: 900;
      text-transform: uppercase;
    }
    .submission-item strong {
      display: block;
      margin-top: 2px;
      overflow-wrap: anywhere;
    }
    .workspace {
      display: grid;
      grid-template-columns: minmax(0, .95fr) minmax(360px, 1.05fr);
      gap: 22px;
      align-items: start;
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
    input:focus, select:focus, textarea:focus {
      outline: 3px solid rgba(11, 114, 231, .16);
      border-color: var(--accent);
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
    .button-row {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      align-items: center;
    }
    .back-button {
      width: auto;
      min-width: 110px;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--text);
    }
    .back-button:hover { background: var(--panel-soft); }
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
    .hint {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
      margin: 12px 0 0;
    }
    .result {
      min-height: 450px;
      display: grid;
      align-content: start;
      gap: 14px;
      position: sticky;
      top: 92px;
      overflow: hidden;
    }
    .result::before {
      content: "";
      position: absolute;
      inset: 0 0 auto;
      height: 6px;
      background: linear-gradient(90deg, var(--accent), #16a166);
    }
    .empty {
      color: var(--muted);
      line-height: 1.6;
    }
    .empty-state {
      display: grid;
      place-items: center;
      min-height: 270px;
      border: 1px dashed #bfd0e2;
      border-radius: 8px;
      background: var(--panel-soft);
      text-align: center;
      padding: 22px;
    }
    .empty-state strong {
      display: block;
      color: var(--text);
      margin-bottom: 8px;
      font-size: 18px;
    }
    .result-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      margin-top: 6px;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 999px;
      padding: 8px 10px;
      font-size: 12px;
      font-weight: 900;
      text-transform: uppercase;
      background: var(--accent-soft);
      color: var(--accent-dark);
      white-space: nowrap;
    }
    .badge.critical { background: var(--danger-soft); color: var(--danger); }
    .badge.high { background: var(--warning-soft); color: var(--warning); }
    .badge.low, .badge.medium { background: var(--success-soft); color: var(--success); }
    .confidence-card {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      background: linear-gradient(180deg, #fff, var(--panel-soft));
    }
    .confidence-top {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: baseline;
      margin-bottom: 10px;
    }
    .confidence-top strong {
      font-size: 30px;
      color: var(--accent-dark);
    }
    .bar {
      height: 10px;
      background: #dfe8f3;
      border-radius: 999px;
      overflow: hidden;
    }
    .bar span {
      display: block;
      height: 100%;
      width: var(--confidence);
      border-radius: 999px;
      background: linear-gradient(90deg, var(--accent), #16a166);
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
    .json-box {
      grid-column: 1 / -1;
      margin: 0;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      max-height: 220px;
      overflow: auto;
      background: #0f1e2f;
      color: #e8f2ff;
      font-size: 13px;
      line-height: 1.5;
      white-space: pre-wrap;
    }
    .error {
      color: var(--danger);
      font-weight: 700;
      border: 1px solid #ffc8c1;
      background: var(--danger-soft);
      border-radius: 8px;
      padding: 14px;
    }
    footer {
      color: var(--muted);
      padding: 8px 0 32px;
      font-size: 14px;
    }
    footer a { color: var(--accent); font-weight: 700; }
    @media (max-width: 820px) {
      .hero, .workspace, .row, .result-grid, .submission-strip { grid-template-columns: 1fr; }
      .topbar { align-items: flex-start; flex-direction: column; }
      .navlinks { flex-wrap: wrap; }
      .hero-card { padding: 22px; min-height: auto; }
      .result { position: static; }
      .button-row { grid-template-columns: 1fr; }
      .back-button { width: 100%; }
    }
  </style>
</head>
<body>
  <header>
    <div class="wrap topbar">
      <div class="brand">
        <div class="logo">QS</div>
        <div>
          <strong>QueueStorm Ticket Sorter</strong>
          <span>Full-stack fintech support classifier</span>
        </div>
      </div>
      <div class="navlinks">
        <a href="/docs">API Docs</a>
        <a href="/health">Health</a>
        <div class="status">Online</div>
      </div>
    </div>
  </header>
  <main class="wrap">
    <section class="hero">
      <div class="panel hero-card">
        <div class="eyebrow">SUST CSE Carnival 2026 - QueueStorm</div>
        <h1>Smart support routing for fintech tickets</h1>
        <p class="lead">
          A complete web interface backed by a CPU-friendly hybrid classifier.
          Submit a support ticket and get a routing-ready decision in one click.
        </p>
        <div class="hero-actions">
          <a href="#sorter">Try the sorter</a>
          <a href="/docs">View API</a>
        </div>
      </div>
      <div class="panel metrics" aria-label="Service capabilities">
        <div class="metric"><strong>Hybrid</strong><span>Rules + TF-IDF Logistic Regression</span></div>
        <div class="metric"><strong>CPU</strong><span>No GPU or external LLM needed</span></div>
        <div class="metric"><strong>Safe</strong><span>Fraud and credential-risk handling</span></div>
        <div class="metric"><strong>Live</strong><span>Interactive UI plus REST API</span></div>
      </div>
    </section>

    <section class="submission-strip" aria-label="Submission format">
      <div class="submission-item">
        <div class="dot">ID</div>
        <div><span>Ticket ID</span><strong id="preview-ticket-id">T-WEB-001</strong></div>
      </div>
      <div class="submission-item">
        <div class="dot">CH</div>
        <div><span>Channel</span><strong id="preview-channel">app</strong></div>
      </div>
      <div class="submission-item">
        <div class="dot">LC</div>
        <div><span>Locale</span><strong id="preview-locale">en</strong></div>
      </div>
    </section>

    <section class="workspace" id="sorter">
      <form class="panel" id="ticket-form">
        <h2>Ticket Submission</h2>
        <p class="hint">The fields below match the request payload sent to <strong>POST /sort-ticket</strong>.</p>
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
        <div class="button-row">
          <button id="submit-button" type="submit">Sort Ticket</button>
          <button class="back-button" id="back-button" type="button">Back</button>
        </div>
      </form>

      <section class="panel result" aria-live="polite">
        <div class="result-head">
          <h2>Decision Board</h2>
          <span class="badge" id="result-status">Waiting</span>
        </div>
        <div id="result" class="empty-state">
          <div>
            <strong>Ready for classification</strong>
            Submit a ticket to see the predicted department, severity, confidence, and agent summary.
          </div>
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

    const fields = {
      ticketId: document.getElementById("ticket-id"),
      channel: document.getElementById("channel"),
      locale: document.getElementById("locale"),
      message: document.getElementById("message")
    };

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function syncSubmissionPreview() {
      document.getElementById("preview-ticket-id").textContent = fields.ticketId.value || "T-WEB-001";
      document.getElementById("preview-channel").textContent = fields.channel.value;
      document.getElementById("preview-locale").textContent = fields.locale.value;
    }

    Object.values(fields).forEach((field) => {
      field.addEventListener("input", syncSubmissionPreview);
      field.addEventListener("change", syncSubmissionPreview);
    });

    document.querySelectorAll("[data-example]").forEach((button) => {
      button.addEventListener("click", () => {
        fields.message.value = examples[button.dataset.example];
        if (button.dataset.example === "fraud") {
          fields.channel.value = "sms";
        }
        syncSubmissionPreview();
      });
    });

    document.getElementById("back-button").addEventListener("click", () => {
      document.getElementById("sorter").scrollIntoView({behavior: "smooth", block: "start"});
      fields.message.focus();
    });

    function renderResult(data) {
      const result = document.getElementById("result");
      const confidence = Math.round(data.confidence * 100);
      const severity = escapeHtml(data.severity);
      const status = document.getElementById("result-status");
      status.textContent = severity;
      status.className = `badge ${severity}`;
      result.className = "result-grid";
      result.innerHTML = `
        <div class="confidence-card summary">
          <div class="confidence-top">
            <span>Model confidence</span>
            <strong>${confidence}%</strong>
          </div>
          <div class="bar" style="--confidence: ${confidence}%"><span></span></div>
        </div>
        <div class="field"><span>Ticket ID</span>${escapeHtml(data.ticket_id)}</div>
        <div class="field"><span>Case Type</span>${escapeHtml(data.case_type)}</div>
        <div class="field"><span>Severity</span>${severity}</div>
        <div class="field"><span>Department</span>${escapeHtml(data.department)}</div>
        <div class="field"><span>Human Review</span>${data.human_review_required ? "Required" : "Not required"}</div>
        <div class="field"><span>Submission Format</span>${escapeHtml(fields.channel.value)} / ${escapeHtml(fields.locale.value)}</div>
        <div class="field summary"><span>Agent Summary</span>${escapeHtml(data.agent_summary)}</div>
        <pre class="json-box">${escapeHtml(JSON.stringify(data, null, 2))}</pre>
      `;
    }

    document.getElementById("ticket-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = document.getElementById("submit-button");
      const result = document.getElementById("result");
      const status = document.getElementById("result-status");
      button.disabled = true;
      button.textContent = "Sorting...";
      status.textContent = "Sorting";
      status.className = "badge";
      result.className = "empty-state";
      result.textContent = "Classifying ticket...";

      const payload = {
        ticket_id: fields.ticketId.value,
        channel: fields.channel.value,
        locale: fields.locale.value,
        message: fields.message.value
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
        status.textContent = "Error";
        status.className = "badge critical";
        result.className = "error";
        result.textContent = `Unable to classify ticket: ${error.message}`;
      } finally {
        button.disabled = false;
        button.textContent = "Sort Ticket";
      }
    });

    syncSubmissionPreview();
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
