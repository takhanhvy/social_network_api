"""Discussion threads and messaging endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.dependencies import get_current_active_user, get_db_session
from app.models import (
    DiscussionThread,
    EventOrganizer,
    EventParticipant,
    GroupMembership,
    Message,
    ThreadContext,
    User,
)
from app.schemas import (
    DiscussionThreadCreate,
    DiscussionThreadDetail,
    DiscussionThreadRead,
    MessageCreate,
    MessageRead,
)

router = APIRouter(prefix="/discussions", tags=["discussions"])


async def _ensure_group_member(
    session: AsyncSession, group_id: int, user_id: int
) -> None:
    # Discussion access relies on group membership for confidentiality.
    result = await session.execute(
        select(GroupMembership).where(
            GroupMembership.group_id == group_id,
            GroupMembership.user_id == user_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to group discussion denied",
        )


async def _ensure_event_participant(
    session: AsyncSession, event_id: int, user_id: int
) -> None:
    # Event threads are accessible to participants and organizers.
    result = await session.execute(
        select(EventParticipant).where(
            EventParticipant.event_id == event_id,
            EventParticipant.user_id == user_id,
        )
    )
    if result.scalar_one_or_none():
        return
    organizer = await session.execute(
        select(EventOrganizer).where(
            EventOrganizer.event_id == event_id,
            EventOrganizer.user_id == user_id,
        )
    )
    if not organizer.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to event discussion denied",
        )


async def _get_thread_with_messages(
    session: AsyncSession, thread_id: int
) -> DiscussionThread:
    result = await session.execute(
        select(DiscussionThread)
        .where(DiscussionThread.id == thread_id)
        .options(selectinload(DiscussionThread.messages))
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found"
        )
    return thread


@router.post("", response_model=DiscussionThreadRead, status_code=201)
async def create_thread(
    payload: DiscussionThreadCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> DiscussionThreadRead:
    if payload.context == ThreadContext.group:
        await _ensure_group_member(session, payload.group_id, current_user.id)  # type: ignore[arg-type]
    elif payload.context == ThreadContext.event:
        await _ensure_event_participant(session, payload.event_id, current_user.id)  # type: ignore[arg-type]

    thread = DiscussionThread(
        title=payload.title,
        context=payload.context,
        group_id=payload.group_id,
        event_id=payload.event_id,
        created_by_id=current_user.id,
    )
    session.add(thread)
    await session.flush()
    await session.refresh(thread)
    return DiscussionThreadRead.from_orm(thread)


@router.get("/{thread_id}", response_model=DiscussionThreadDetail)
async def get_thread(
    thread_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> DiscussionThreadDetail:
    thread = await _get_thread_with_messages(session, thread_id)
    if thread.context == ThreadContext.group and thread.group_id:
        await _ensure_group_member(session, thread.group_id, current_user.id)
    elif thread.context == ThreadContext.event and thread.event_id:
        await _ensure_event_participant(session, thread.event_id, current_user.id)
    messages = [MessageRead.from_orm(message) for message in thread.messages]
    return DiscussionThreadDetail(
        **DiscussionThreadRead.from_orm(thread).model_dump(),
        messages=messages,
    )


@router.post(
    "/{thread_id}/messages",
    response_model=MessageRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_message(
    thread_id: int,
    payload: MessageCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> MessageRead:
    thread = await _get_thread_with_messages(session, thread_id)
    if thread.context == ThreadContext.group and thread.group_id:
        await _ensure_group_member(session, thread.group_id, current_user.id)
    elif thread.context == ThreadContext.event and thread.event_id:
        await _ensure_event_participant(session, thread.event_id, current_user.id)

    if payload.parent_id:
        result = await session.execute(
            select(Message).where(
                Message.id == payload.parent_id,
                Message.thread_id == thread_id,
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent message not found in this thread",
            )

    message = Message(
        thread_id=thread_id,
        author_id=current_user.id,
        content=payload.content,
        parent_id=payload.parent_id,
    )
    session.add(message)
    await session.flush()
    await session.refresh(message)
    return MessageRead.from_orm(message)


@router.get(
    "/{thread_id}/messages",
    response_model=List[MessageRead],
)
async def list_messages(
    thread_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> List[MessageRead]:
    thread = await _get_thread_with_messages(session, thread_id)
    if thread.context == ThreadContext.group and thread.group_id:
        await _ensure_group_member(session, thread.group_id, current_user.id)
    elif thread.context == ThreadContext.event and thread.event_id:
        await _ensure_event_participant(session, thread.event_id, current_user.id)
    return [MessageRead.from_orm(message) for message in thread.messages]
