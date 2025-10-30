"""Group management endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.dependencies import get_current_active_user, get_db_session
from app.models import Group, GroupMembership, GroupType, User
from app.schemas import (
    GroupCreate,
    GroupDetail,
    GroupMembershipCreate,
    GroupMembershipRead,
    GroupMembershipUpdate,
    GroupRead,
)

router = APIRouter(prefix="/groups", tags=["groups"])


@router.post("", response_model=GroupRead, status_code=status.HTTP_201_CREATED)
async def create_group(
    group_in: GroupCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> GroupRead:
    if group_in.type not in {GroupType.public, GroupType.private, GroupType.secret}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid group type"
        )
    group = Group(
        name=group_in.name,
        description=group_in.description,
        icon=group_in.icon,
        cover_photo=group_in.cover_photo,
        type=group_in.type,
        allow_member_posts=group_in.allow_member_posts,
        allow_member_events=group_in.allow_member_events,
        created_by_id=current_user.id,
    )
    session.add(group)
    await session.flush()
    membership = GroupMembership(
        group_id=group.id,
        user_id=current_user.id,
        is_admin=True,
        can_create_events=True,
    )
    session.add(membership)
    await session.flush()
    await session.refresh(group)
    return GroupRead.from_orm(group)


@router.get("", response_model=List[GroupRead])
async def list_groups(
    _: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> List[GroupRead]:
    result = await session.execute(select(Group))
    groups = result.scalars().all()
    return [GroupRead.from_orm(group) for group in groups]


async def _get_group_with_members(session: AsyncSession, group_id: int) -> Group:
    result = await session.execute(
        select(Group)
        .where(Group.id == group_id)
        .options(selectinload(Group.memberships))
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Group not found"
        )
    return group


@router.get("/{group_id}", response_model=GroupDetail)
async def get_group(
    group_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> GroupDetail:
    group = await _get_group_with_members(session, group_id)
    members = [
        GroupMembershipRead.from_orm(membership) for membership in group.memberships
    ]
    return GroupDetail(
        **GroupRead.from_orm(group).model_dump(),
        members=members,
    )


async def _ensure_group_admin(
    session: AsyncSession, group_id: int, user_id: int
) -> GroupMembership:
    result = await session.execute(
        select(GroupMembership).where(
            GroupMembership.group_id == group_id, GroupMembership.user_id == user_id
        )
    )
    membership = result.scalar_one_or_none()
    if not membership or not membership.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )
    return membership


@router.post(
    "/{group_id}/members", response_model=GroupMembershipRead, status_code=201
)
async def add_group_member(
    group_id: int,
    membership_in: GroupMembershipCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> GroupMembershipRead:
    await _ensure_group_admin(session, group_id, current_user.id)

    existing = await session.execute(
        select(GroupMembership).where(
            GroupMembership.group_id == group_id,
            GroupMembership.user_id == membership_in.user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User already member"
        )

    result_user = await session.execute(
        select(User).where(User.id == membership_in.user_id)
    )
    if not result_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    membership = GroupMembership(
        group_id=group_id,
        user_id=membership_in.user_id,
        is_admin=membership_in.is_admin,
        can_create_events=membership_in.can_create_events,
    )
    session.add(membership)
    await session.flush()
    await session.refresh(membership)
    return GroupMembershipRead.from_orm(membership)


@router.patch(
    "/{group_id}/members/{user_id}", response_model=GroupMembershipRead
)
async def update_group_member(
    group_id: int,
    user_id: int,
    payload: GroupMembershipUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> GroupMembershipRead:
    await _ensure_group_admin(session, group_id, current_user.id)
    result = await session.execute(
        select(GroupMembership).where(
            GroupMembership.group_id == group_id,
            GroupMembership.user_id == user_id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found"
        )

    if payload.is_admin is not None:
        membership.is_admin = payload.is_admin
    if payload.can_create_events is not None:
        membership.can_create_events = payload.can_create_events
    session.add(membership)
    await session.flush()
    await session.refresh(membership)
    return GroupMembershipRead.from_orm(membership)


@router.delete(
    "/{group_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_group_member(
    group_id: int,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await _ensure_group_admin(session, group_id, current_user.id)
    result = await session.execute(
        select(GroupMembership).where(
            GroupMembership.group_id == group_id,
            GroupMembership.user_id == user_id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found"
        )
    await session.delete(membership)
