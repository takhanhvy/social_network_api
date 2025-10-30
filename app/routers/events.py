"""Event management endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.dependencies import get_current_active_user, get_db_session
from app.models import Event, EventOrganizer, EventParticipant, GroupMembership, User
from app.schemas import (
    EventCreate,
    EventDetail,
    EventOrganizerCreate,
    EventOrganizerRead,
    EventParticipantCreate,
    EventParticipantRead,
    EventRead,
)

router = APIRouter(prefix="/events", tags=["events"])


async def _ensure_can_manage_group_event(
    session: AsyncSession, group_id: int, user_id: int
) -> None:
    # Group admins or members allowed to create events must be verified server-side.
    result = await session.execute(
        select(GroupMembership).where(
            GroupMembership.group_id == group_id,
            GroupMembership.user_id == user_id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership or not (
        membership.is_admin or membership.can_create_events
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User cannot create or manage events for this group",
        )


async def _get_event_with_relations(
    session: AsyncSession, event_id: int
) -> Event:
    # Load organizers/participants eagerly to avoid async lazy-load issues.
    result = await session.execute(
        select(Event)
        .where(Event.id == event_id)
        .options(
            selectinload(Event.organizers),
            selectinload(Event.participants),
        )
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )
    return event


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: EventCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> EventRead:
    if payload.group_id:
        await _ensure_can_manage_group_event(session, payload.group_id, current_user.id)

    event = Event(
        name=payload.name,
        description=payload.description,
        start_date=payload.start_date,
        end_date=payload.end_date,
        location=payload.location,
        cover_photo=payload.cover_photo,
        is_private=payload.is_private,
        group_id=payload.group_id,
        created_by_id=current_user.id,
        carpool_enabled=payload.carpool_enabled,
        shopping_list_enabled=payload.shopping_list_enabled,
        billetterie_enabled=payload.billetterie_enabled,
        polls_enabled=payload.polls_enabled,
    )
    session.add(event)
    await session.flush()

    organizer_ids = set(payload.organizer_ids or [])
    organizer_ids.add(current_user.id)

    for organizer_id in organizer_ids:
        result = await session.execute(select(User).where(User.id == organizer_id))
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organizer {organizer_id} not found",
            )
        session.add(
            EventOrganizer(event_id=event.id, user_id=organizer_id)
        )
    await session.flush()
    await session.refresh(event)
    return EventRead.from_orm(event)


@router.get("", response_model=List[EventRead])
async def list_events(
    _: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> List[EventRead]:
    result = await session.execute(select(Event))
    events = result.scalars().all()
    return [EventRead.from_orm(event) for event in events]


@router.get("/{event_id}", response_model=EventDetail)
async def get_event(
    event_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> EventDetail:
    event = await _get_event_with_relations(session, event_id)
    organizers = [
        EventOrganizerRead.from_orm(org) for org in event.organizers
    ]
    participants = [
        EventParticipantRead.from_orm(part) for part in event.participants
    ]
    return EventDetail(
        **EventRead.from_orm(event).model_dump(),
        organizers=organizers,
        participants=participants,
    )


async def _ensure_event_organizer(
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
    "/{event_id}/organizers",
    response_model=EventOrganizerRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_event_organizer(
    event_id: int,
    payload: EventOrganizerCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> EventOrganizerRead:
    await _ensure_event_organizer(session, event_id, current_user.id)

    existing = await session.execute(
        select(EventOrganizer).where(
            EventOrganizer.event_id == event_id,
            EventOrganizer.user_id == payload.user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already organizer",
        )
    result_user = await session.execute(
        select(User).where(User.id == payload.user_id)
    )
    if not result_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    organizer = EventOrganizer(event_id=event_id, user_id=payload.user_id)
    session.add(organizer)
    await session.flush()
    await session.refresh(organizer)
    return EventOrganizerRead.from_orm(organizer)


@router.post(
    "/{event_id}/participants",
    response_model=EventParticipantRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_event_participant(
    event_id: int,
    payload: EventParticipantCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> EventParticipantRead:
    # Organizer or the user themself can add participant entry
    if payload.user_id != current_user.id:
        await _ensure_event_organizer(session, event_id, current_user.id)

    existing = await session.execute(
        select(EventParticipant).where(
            EventParticipant.event_id == event_id,
            EventParticipant.user_id == payload.user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already participant",
        )

    result_user = await session.execute(
        select(User).where(User.id == payload.user_id)
    )
    if not result_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    participant = EventParticipant(event_id=event_id, user_id=payload.user_id)
    session.add(participant)
    await session.flush()
    await session.refresh(participant)
    return EventParticipantRead.from_orm(participant)


@router.delete(
    "/{event_id}/participants/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_event_participant(
    event_id: int,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await _ensure_event_organizer(session, event_id, current_user.id)
    result = await session.execute(
        select(EventParticipant).where(
            EventParticipant.event_id == event_id,
            EventParticipant.user_id == user_id,
        )
    )
    participant = result.scalar_one_or_none()
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found"
        )
    await session.delete(participant)
