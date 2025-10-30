"""Shopping list and carpooling endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.dependencies import get_current_active_user, get_db_session
from app.models import (
    CarpoolOffer,
    Event,
    EventOrganizer,
    EventParticipant,
    ShoppingListItem,
    User,
)
from app.schemas import (
    CarpoolOfferCreate,
    CarpoolOfferRead,
    ShoppingItemCreate,
    ShoppingItemRead,
)

router = APIRouter(prefix="/addons", tags=["addons"])


async def _get_event(session: AsyncSession, event_id: int) -> Event:
    result = await session.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )
    return event


async def _ensure_event_member(
    session: AsyncSession, event_id: int, user_id: int
) -> None:
    # Shopping/carpool features are reserved to event participants or organizers.
    participant = await session.execute(
        select(EventParticipant).where(
            EventParticipant.event_id == event_id,
            EventParticipant.user_id == user_id,
        )
    )
    if participant.scalar_one_or_none():
        return
    organizer = await session.execute(
        select(EventOrganizer).where(
            EventOrganizer.event_id == event_id,
            EventOrganizer.user_id == user_id,
        )
    )
    if organizer.scalar_one_or_none():
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Event membership required",
    )


@router.post(
    "/events/{event_id}/shopping-items",
    response_model=ShoppingItemRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_shopping_item(
    event_id: int,
    payload: ShoppingItemCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> ShoppingItemRead:
    event = await _get_event(session, event_id)
    if not event.shopping_list_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shopping list is not enabled for this event",
        )
    await _ensure_event_member(session, event_id, current_user.id)

    existing = await session.execute(
        select(ShoppingListItem).where(
            ShoppingListItem.event_id == event_id,
            ShoppingListItem.name == payload.name,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item already registered for this event",
        )

    item = ShoppingListItem(
        event_id=event_id,
        owner_id=current_user.id,
        name=payload.name,
        quantity=payload.quantity,
        arrival_time=payload.arrival_time,
    )
    session.add(item)
    await session.flush()
    await session.refresh(item)
    return ShoppingItemRead.from_orm(item)


@router.get(
    "/events/{event_id}/shopping-items",
    response_model=List[ShoppingItemRead],
)
async def list_shopping_items(
    event_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> List[ShoppingItemRead]:
    event = await _get_event(session, event_id)
    if not event.shopping_list_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shopping list is not enabled for this event",
        )
    await _ensure_event_member(session, event_id, current_user.id)
    result = await session.execute(
        select(ShoppingListItem).where(ShoppingListItem.event_id == event_id)
    )
    items = result.scalars().all()
    return [ShoppingItemRead.from_orm(item) for item in items]


@router.post(
    "/events/{event_id}/carpools",
    response_model=CarpoolOfferRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_carpool_offer(
    event_id: int,
    payload: CarpoolOfferCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> CarpoolOfferRead:
    event = await _get_event(session, event_id)
    if not event.carpool_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Carpooling is not enabled for this event",
        )
    await _ensure_event_member(session, event_id, current_user.id)
    offer = CarpoolOffer(
        event_id=event_id,
        driver_id=current_user.id,
        departure_location=payload.departure_location,
        departure_time=payload.departure_time,
        price=payload.price,
        available_seats=payload.available_seats,
        max_detour_minutes=payload.max_detour_minutes,
    )
    session.add(offer)
    await session.flush()
    await session.refresh(offer)
    return CarpoolOfferRead.from_orm(offer)


@router.get(
    "/events/{event_id}/carpools",
    response_model=List[CarpoolOfferRead],
)
async def list_carpool_offers(
    event_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> List[CarpoolOfferRead]:
    event = await _get_event(session, event_id)
    if not event.carpool_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Carpooling is not enabled for this event",
        )
    await _ensure_event_member(session, event_id, current_user.id)
    result = await session.execute(
        select(CarpoolOffer).where(CarpoolOffer.event_id == event_id)
    )
    offers = result.scalars().all()
    return [CarpoolOfferRead.from_orm(offer) for offer in offers]
