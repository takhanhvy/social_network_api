"""Albums, photos, and comments endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.dependencies import get_current_active_user, get_db_session
from app.models import (
    Event,
    EventOrganizer,
    EventParticipant,
    Photo,
    PhotoAlbum,
    PhotoComment,
    User,
)
from app.schemas import (
    PhotoAlbumCreate,
    PhotoAlbumRead,
    PhotoCommentCreate,
    PhotoCommentRead,
    PhotoCreate,
    PhotoRead,
)

router = APIRouter(prefix="/media", tags=["media"])


async def _ensure_event_access(
    session: AsyncSession, event_id: int, user_id: int
) -> None:
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
        detail="Event access required",
    )


async def _get_event(session: AsyncSession, event_id: int) -> Event:
    result = await session.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )
    return event


@router.post(
    "/events/{event_id}/albums",
    response_model=PhotoAlbumRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_album(
    event_id: int,
    payload: PhotoAlbumCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> PhotoAlbumRead:
    event = await _get_event(session, event_id)
    await _ensure_event_access(session, event.id, current_user.id)

    album = PhotoAlbum(
        event_id=event.id,
        name=payload.name,
        created_by_id=current_user.id,
    )
    session.add(album)
    await session.flush()
    await session.refresh(album)
    return PhotoAlbumRead.from_orm(album)


@router.get(
    "/events/{event_id}/albums",
    response_model=List[PhotoAlbumRead],
)
async def list_albums(
    event_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> List[PhotoAlbumRead]:
    await _get_event(session, event_id)
    await _ensure_event_access(session, event_id, current_user.id)
    result = await session.execute(
        select(PhotoAlbum).where(PhotoAlbum.event_id == event_id)
    )
    albums = result.scalars().all()
    return [PhotoAlbumRead.from_orm(album) for album in albums]


async def _get_album(session: AsyncSession, album_id: int) -> PhotoAlbum:
    result = await session.execute(
        select(PhotoAlbum)
        .where(PhotoAlbum.id == album_id)
        .options(selectinload(PhotoAlbum.event))
    )
    album = result.scalar_one_or_none()
    if not album:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Album not found"
        )
    return album


@router.post(
    "/albums/{album_id}/photos",
    response_model=PhotoRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_photo(
    album_id: int,
    payload: PhotoCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> PhotoRead:
    album = await _get_album(session, album_id)
    await _ensure_event_access(session, album.event_id, current_user.id)

    photo = Photo(
        album_id=album.id,
        uploaded_by_id=current_user.id,
        url=payload.url,
        caption=payload.caption,
    )
    session.add(photo)
    await session.flush()
    await session.refresh(photo)
    return PhotoRead.from_orm(photo)


@router.get(
    "/albums/{album_id}/photos",
    response_model=List[PhotoRead],
)
async def list_photos(
    album_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> List[PhotoRead]:
    album = await _get_album(session, album_id)
    await _ensure_event_access(session, album.event_id, current_user.id)
    result = await session.execute(select(Photo).where(Photo.album_id == album_id))
    photos = result.scalars().all()
    return [PhotoRead.from_orm(photo) for photo in photos]


async def _get_photo(session: AsyncSession, photo_id: int) -> Photo:
    result = await session.execute(
        select(Photo)
        .where(Photo.id == photo_id)
        .options(selectinload(Photo.album))
    )
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found"
        )
    return photo


@router.post(
    "/photos/{photo_id}/comments",
    response_model=PhotoCommentRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_photo_comment(
    photo_id: int,
    payload: PhotoCommentCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> PhotoCommentRead:
    photo = await _get_photo(session, photo_id)
    album = await _get_album(session, photo.album_id)
    await _ensure_event_access(session, album.event_id, current_user.id)

    comment = PhotoComment(
        photo_id=photo.id,
        author_id=current_user.id,
        content=payload.content,
    )
    session.add(comment)
    await session.flush()
    await session.refresh(comment)
    return PhotoCommentRead.from_orm(comment)


@router.get(
    "/photos/{photo_id}/comments",
    response_model=List[PhotoCommentRead],
)
async def list_photo_comments(
    photo_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> List[PhotoCommentRead]:
    photo = await _get_photo(session, photo_id)
    album = await _get_album(session, photo.album_id)
    await _ensure_event_access(session, album.event_id, current_user.id)
    result = await session.execute(
        select(PhotoComment).where(PhotoComment.photo_id == photo_id)
    )
    comments = result.scalars().all()
    return [PhotoCommentRead.from_orm(comment) for comment in comments]

