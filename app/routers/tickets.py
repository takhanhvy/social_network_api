"""Ticketing endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.dependencies import get_current_active_user, get_db_session
from app.models import Event, EventOrganizer, Ticket, TicketType, User
from app.schemas import TicketPurchase, TicketRead, TicketTypeCreate, TicketTypeRead

router = APIRouter(prefix="/tickets", tags=["tickets"])


async def _get_event(session: AsyncSession, event_id: int) -> Event:
    result = await session.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )
    if not event.billetterie_enabled:
        # Protect against ticket sales when the feature is toggled off.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ticketing not enabled for this event",
        )
    return event


async def _ensure_organizer(
    session: AsyncSession, event_id: int, user_id: int
) -> None:
    result = await session.execute(
        select(EventOrganizer).where(
            EventOrganizer.event_id == event_id,
            EventOrganizer.user_id == user_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organizer privileges required",
        )


@router.post(
    "/events/{event_id}/types",
    response_model=TicketTypeRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_ticket_type(
    event_id: int,
    payload: TicketTypeCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> TicketTypeRead:
    await _get_event(session, event_id)
    await _ensure_organizer(session, event_id, current_user.id)

    ticket_type = TicketType(
        event_id=event_id,
        name=payload.name,
        price=payload.price,
        quantity=payload.quantity,
    )
    session.add(ticket_type)
    await session.flush()
    await session.refresh(ticket_type)
    return TicketTypeRead.from_orm(ticket_type)


@router.get(
    "/events/{event_id}/types",
    response_model=List[TicketTypeRead],
)
async def list_ticket_types(
    event_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> List[TicketTypeRead]:
    await _get_event(session, event_id)
    result = await session.execute(
        select(TicketType).where(TicketType.event_id == event_id)
    )
    types = result.scalars().all()
    return [TicketTypeRead.from_orm(ticket_type) for ticket_type in types]


async def _get_ticket_type(session: AsyncSession, ticket_type_id: int) -> TicketType:
    result = await session.execute(
        select(TicketType).where(TicketType.id == ticket_type_id)
    )
    ticket_type = result.scalar_one_or_none()
    if not ticket_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket type not found"
        )
    await _get_event(session, ticket_type.event_id)
    return ticket_type


@router.post(
    "/types/{ticket_type_id}/purchase",
    response_model=TicketRead,
    status_code=status.HTTP_201_CREATED,
)
async def purchase_ticket(
    ticket_type_id: int,
    payload: TicketPurchase,
    session: AsyncSession = Depends(get_db_session),
) -> TicketRead:
    ticket_type = await _get_ticket_type(session, ticket_type_id)

    # Check availability
    sold_count_query = await session.execute(
        select(func.count(Ticket.id)).where(Ticket.ticket_type_id == ticket_type_id)
    )
    sold_count = sold_count_query.scalar_one()
    if sold_count >= ticket_type.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No more tickets available",
        )

    # Ensure single ticket per person for this type
    existing_ticket = await session.execute(
        select(Ticket).where(
            Ticket.ticket_type_id == ticket_type_id,
            Ticket.purchaser_email == payload.purchaser_email,
        )
    )
    if existing_ticket.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This attendee already has a ticket",
        )

    ticket = Ticket(
        ticket_type_id=ticket_type_id,
        purchaser_first_name=payload.purchaser_first_name,
        purchaser_last_name=payload.purchaser_last_name,
        purchaser_email=payload.purchaser_email,
        purchaser_address=payload.purchaser_address,
    )
    session.add(ticket)
    await session.flush()
    await session.refresh(ticket)
    return TicketRead.from_orm(ticket)
