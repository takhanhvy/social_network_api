"""Pydantic schemas for request and response payloads."""

from datetime import datetime
from typing import List, Optional

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    ConfigDict,
    constr,
    model_validator,
)

from app.models import GroupType, ThreadContext


# Authentication -----------------------------------------------------------------


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    exp: int


# Users ----------------------------------------------------------------------------


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)


class UserCreate(UserBase):
    password: constr(min_length=8)  # type: ignore[valid-type]


class UserRead(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Groups --------------------------------------------------------------------------


class GroupBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    icon: Optional[str] = Field(default=None, max_length=255)
    cover_photo: Optional[str] = Field(default=None, max_length=255)
    type: GroupType
    allow_member_posts: bool = True
    allow_member_events: bool = True


class GroupCreate(GroupBase):
    pass


class GroupRead(GroupBase):
    id: int
    created_at: datetime
    created_by_id: int

    class Config:
        from_attributes = True


class GroupMembershipCreate(BaseModel):
    user_id: int
    is_admin: bool = False
    can_create_events: bool = False


class GroupMembershipRead(BaseModel):
    user_id: int
    group_id: int
    is_admin: bool
    can_create_events: bool
    created_at: datetime

    class Config:
        from_attributes = True


class GroupMembershipUpdate(BaseModel):
    is_admin: Optional[bool] = None
    can_create_events: Optional[bool] = None


class GroupDetail(GroupRead):
    members: List[GroupMembershipRead]


# Events --------------------------------------------------------------------------


class EventBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    start_date: datetime
    end_date: datetime
    location: str = Field(min_length=1, max_length=255)
    cover_photo: Optional[str] = Field(default=None, max_length=255)
    is_private: bool = False
    group_id: Optional[int] = None
    carpool_enabled: bool = False
    shopping_list_enabled: bool = False
    billetterie_enabled: bool = False
    polls_enabled: bool = True

    @model_validator(mode="after")
    def validate_dates(cls, data: "EventBase") -> "EventBase":
        if data.end_date <= data.start_date:
            raise ValueError("end_date must be after start_date")
        return data


class EventCreate(EventBase):
    organizer_ids: List[int] = Field(default_factory=list)


class EventRead(EventBase):
    id: int
    created_by_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class EventParticipantCreate(BaseModel):
    user_id: int


class EventOrganizerCreate(BaseModel):
    user_id: int


class EventOrganizerRead(BaseModel):
    event_id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class EventParticipantRead(BaseModel):
    event_id: int
    user_id: int
    joined_at: datetime

    class Config:
        from_attributes = True


class EventDetail(EventRead):
    organizers: List[EventOrganizerRead]
    participants: List[EventParticipantRead]


# Discussion threads --------------------------------------------------------------


class DiscussionThreadCreate(BaseModel):
    title: str
    context: ThreadContext
    group_id: Optional[int] = None
    event_id: Optional[int] = None

    @model_validator(mode="after")
    def validate_context(cls, data: "DiscussionThreadCreate") -> "DiscussionThreadCreate":
        if data.context == ThreadContext.group and not data.group_id:
            raise ValueError("group_id is required when context = group")
        if data.context == ThreadContext.event and not data.event_id:
            raise ValueError("event_id is required when context = event")
        return data


class DiscussionThreadRead(BaseModel):
    id: int
    title: str
    context: ThreadContext
    group_id: Optional[int]
    event_id: Optional[int]
    created_at: datetime
    created_by_id: int

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    parent_id: Optional[int] = None


class MessageRead(BaseModel):
    id: int
    content: str
    parent_id: Optional[int]
    author_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class DiscussionThreadDetail(DiscussionThreadRead):
    messages: List[MessageRead]


# Albums & photos -----------------------------------------------------------------


class PhotoAlbumCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class PhotoAlbumRead(BaseModel):
    id: int
    name: str
    event_id: int
    created_by_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class PhotoCreate(BaseModel):
    url: str
    caption: Optional[str] = None


class PhotoRead(BaseModel):
    id: int
    album_id: int
    uploaded_by_id: int
    url: str
    caption: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class PhotoCommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=1000)


class PhotoCommentRead(BaseModel):
    id: int
    photo_id: int
    author_id: int
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# Polls ----------------------------------------------------------------------------


class PollOptionCreate(BaseModel):
    label: str = Field(min_length=1, max_length=255)


class PollQuestionCreate(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    options: List[PollOptionCreate]


class PollCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    questions: List[PollQuestionCreate]


class PollRead(BaseModel):
    id: int
    title: str
    event_id: int
    created_by_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PollVoteItem(BaseModel):
    question_id: int
    option_id: int


class PollOptionRead(BaseModel):
    id: int
    question_id: int
    label: str
    votes: int

    class Config:
        from_attributes = True


class PollQuestionRead(BaseModel):
    id: int
    poll_id: int
    question: str
    options: List[PollOptionRead]

    class Config:
        from_attributes = True


class PollDetail(PollRead):
    questions: List[PollQuestionRead]


# Tickets -------------------------------------------------------------------------


class TicketTypeCreate(BaseModel):
    name: str
    price: float = Field(ge=0)
    quantity: int = Field(ge=0)


class TicketTypeRead(BaseModel):
    id: int
    event_id: int
    name: str
    price: float
    quantity: int
    created_at: datetime

    class Config:
        from_attributes = True


class TicketPurchase(BaseModel):
    purchaser_first_name: str
    purchaser_last_name: str
    purchaser_email: EmailStr
    purchaser_address: Optional[str] = None


class TicketRead(BaseModel):
    id: int
    ticket_type_id: int
    purchaser_first_name: str
    purchaser_last_name: str
    purchaser_email: EmailStr
    purchaser_address: Optional[str]
    purchased_at: datetime

    class Config:
        from_attributes = True


# Shopping list -------------------------------------------------------------------


class ShoppingItemCreate(BaseModel):
    name: str
    quantity: int = Field(ge=1)
    arrival_time: datetime


class ShoppingItemRead(BaseModel):
    id: int
    name: str
    quantity: int
    arrival_time: datetime
    owner_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Carpool -------------------------------------------------------------------------


class CarpoolOfferCreate(BaseModel):
    departure_location: str
    departure_time: datetime
    price: float = Field(ge=0)
    available_seats: int = Field(ge=1)
    max_detour_minutes: int = Field(ge=0)


class CarpoolOfferRead(BaseModel):
    id: int
    event_id: int
    driver_id: int
    departure_location: str
    departure_time: datetime
    price: float
    available_seats: int
    max_detour_minutes: int
    created_at: datetime

    class Config:
        from_attributes = True
