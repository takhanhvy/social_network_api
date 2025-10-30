"""Poll creation and voting endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.dependencies import get_current_active_user, get_db_session
from app.models import (
    EventOrganizer,
    EventParticipant,
    Poll,
    PollOption,
    PollQuestion,
    PollVote,
    User,
)
from app.schemas import (
    PollCreate,
    PollDetail,
    PollOptionRead,
    PollQuestionRead,
    PollRead,
    PollVoteItem,
)

router = APIRouter(prefix="/polls", tags=["polls"])


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


async def _ensure_event_participant(
    session: AsyncSession, event_id: int, user_id: int
) -> None:
    result = await session.execute(
        select(EventParticipant).where(
            EventParticipant.event_id == event_id,
            EventParticipant.user_id == user_id,
        )
    )
    if result.scalar_one_or_none():
        return
    await _ensure_event_organizer(session, event_id, user_id)


async def _get_poll_with_questions(
    session: AsyncSession, poll_id: int
) -> Poll:
    result = await session.execute(
        select(Poll)
        .where(Poll.id == poll_id)
        .options(
            selectinload(Poll.questions)
            .selectinload(PollQuestion.options)
            .selectinload(PollOption.votes),
        )
    )
    poll = result.scalar_one_or_none()
    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Poll not found"
        )
    return poll


@router.post(
    "/events/{event_id}",
    response_model=PollRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_poll(
    event_id: int,
    payload: PollCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> PollRead:
    await _ensure_event_organizer(session, event_id, current_user.id)

    if not payload.questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Poll must contain questions",
        )
    poll = Poll(
        event_id=event_id,
        title=payload.title,
        created_by_id=current_user.id,
    )
    session.add(poll)
    await session.flush()

    for question_payload in payload.questions:
        if not question_payload.options or len(question_payload.options) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Each question needs at least two options",
            )
        question = PollQuestion(
            poll_id=poll.id,
            question=question_payload.question,
        )
        session.add(question)
        await session.flush()
        for option_payload in question_payload.options:
            option = PollOption(
                question_id=question.id,
                label=option_payload.label,
            )
            session.add(option)
    await session.flush()
    await session.refresh(poll)
    return PollRead.from_orm(poll)


@router.get(
    "/events/{event_id}",
    response_model=List[PollRead],
)
async def list_polls(
    event_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> List[PollRead]:
    await _ensure_event_participant(session, event_id, current_user.id)
    result = await session.execute(select(Poll).where(Poll.event_id == event_id))
    polls = result.scalars().all()
    return [PollRead.from_orm(poll) for poll in polls]


def _serialize_poll(poll: Poll) -> PollDetail:
    questions: List[PollQuestionRead] = []
    for question in poll.questions:
        options = [
            PollOptionRead(
                id=option.id,
                question_id=option.question_id,
                label=option.label,
                votes=len(option.votes),
            )
            for option in question.options
        ]
        questions.append(
            PollQuestionRead(
                id=question.id,
                poll_id=question.poll_id,
                question=question.question,
                options=options,
            )
        )
    return PollDetail(
        **PollRead.from_orm(poll).model_dump(),
        questions=questions,
    )


@router.get("/{poll_id}", response_model=PollDetail)
async def get_poll(
    poll_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> PollDetail:
    poll = await _get_poll_with_questions(session, poll_id)
    await _ensure_event_participant(session, poll.event_id, current_user.id)
    return _serialize_poll(poll)


@router.post("/{poll_id}/votes", response_model=PollDetail)
async def submit_poll_votes(
    poll_id: int,
    votes: List[PollVoteItem],
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> PollDetail:
    poll = await _get_poll_with_questions(session, poll_id)
    if not poll.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Poll is closed"
        )
    await _ensure_event_participant(session, poll.event_id, current_user.id)

    question_map = {question.id: question for question in poll.questions}

    for vote in votes:
        question = question_map.get(vote.question_id)
        if not question:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Question {vote.question_id} not part of this poll",
            )
        option = next(
            (opt for opt in question.options if opt.id == vote.option_id), None
        )
        if not option:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Option {vote.option_id} invalid for question {vote.question_id}",
            )
        existing_vote = await session.execute(
            select(PollVote).where(
                PollVote.question_id == vote.question_id,
                PollVote.voter_id == current_user.id,
            )
        )
        existing = existing_vote.scalar_one_or_none()
        if existing:
            existing.option_id = vote.option_id
            session.add(existing)
        else:
            session.add(
                PollVote(
                    question_id=vote.question_id,
                    option_id=vote.option_id,
                    voter_id=current_user.id,
                )
            )
    await session.flush()
    updated_poll = await _get_poll_with_questions(session, poll_id)
    return _serialize_poll(updated_poll)
