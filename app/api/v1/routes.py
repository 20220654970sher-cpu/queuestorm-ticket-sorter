from __future__ import annotations

from fastapi import APIRouter, Request, status

from app.schemas.ticket import TicketRequest, TicketResponse
from app.services.classifier import TicketSortingService

router = APIRouter(tags=["ticket-sorting"])


@router.get("/health", status_code=status.HTTP_200_OK)
def health() -> dict[str, str]:
    return {"status": "healthy"}


@router.post("/sort-ticket", response_model=TicketResponse, status_code=status.HTTP_200_OK)
def sort_ticket(payload: TicketRequest, request: Request) -> TicketResponse:
    service: TicketSortingService = request.app.state.ticket_service
    return service.sort(payload)
