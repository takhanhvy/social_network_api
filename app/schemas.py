"""Pydantic schemas for request and response payloads."""

from datetime import datetime
import re
from typing import List, Optional

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    FieldValidationInfo,
    constr,
    field_validator,
    model_validator,
)

from app.models import GroupType, ThreadContext

PASSWORD_REGEX = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$"
)


def _normalize_optional_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return value


def _normalize_required_text(value: str, field_name: str) -> str:
    cleaned = _normalize_optional_text(value)
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty or blank")
    return cleaned


# Authentication -----------------------------------------------------------------


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., ge=1)


class TokenPayload(BaseModel):
    sub: str
    exp: int
    iat: int
    iss: Optional[str] = None
    aud: Optional[str] = None


# Users ----------------------------------------------------------------------------


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)

    @field_validator("full_name", mode="before")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        return _normalize_required_text(value, "full_name")


class UserCreate(UserBase):
    password: constr(min_length=8)  # type: ignore[valid-type]

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not PASSWORD_REGEX.match(value):
            raise ValueError(
                "Password must contain uppercase, lowercase, digit, and special character"
            )
        return value


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
    icon: Optional[AnyHttpUrl] = None
    cover_photo: Optional[AnyHttpUrl] = None
    type: GroupType
    allow_member_posts: bool = True
    allow_member_events: bool = True

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return _normalize_required_text(value, "name")

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_optional_text(value)


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
    cover_photo: Optional[AnyHttpUrl] = None
    is_private: bool = False
    group_id: Optional[int] = None
    carpool_enabled: bool = False
    shopping_list_enabled: bool = False
    billetterie_enabled: bool = False
    polls_enabled: bool = True

    @field_validator("name", "location", mode="before")
    @classmethod
    def normalize_event_text(
        cls, value: str, info: FieldValidationInfo
    ) -> str:
        return _normalize_required_text(value, info.field_name or "value")

    @field_validator("description", mode="before")
    @classmethod
    def normalize_event_description(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_optional_text(value)

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

    @field_validator("title", mode="before")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        return _normalize_required_text(value, "title")

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

    @field_validator("content", mode="before")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        return _normalize_required_text(value, "content")


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

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return _normalize_required_text(value, "name")


class PhotoAlbumRead(BaseModel):
    id: int
    name: str
    event_id: int
    created_by_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class PhotoCreate(BaseModel):
    url: AnyHttpUrl
    caption: Optional[str] = None

    @field_validator("caption", mode="before")
    @classmethod
    def normalize_caption(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_optional_text(value)


class PhotoRead(BaseModel):
    id: int
    album_id: int
    uploaded_by_id: int
    url: AnyHttpUrl
    caption: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class PhotoCommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=1000)

    @field_validator("content", mode="before")
    @classmethod
    def normalize_comment(cls, value: str) -> str:
        return _normalize_required_text(value, "content")


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

    @field_validator("label", mode="before")
    @classmethod
    def normalize_label(cls, value: str) -> str:
        return _normalize_required_text(value, "label")


class PollQuestionCreate(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    options: List[PollOptionCreate]

    @field_validator("question", mode="before")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        return _normalize_required_text(value, "question")


class PollCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    questions: List[PollQuestionCreate]

    @field_validator("title", mode="before")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        return _normalize_required_text(value, "title")


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

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return _normalize_required_text(value, "name")


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

    @field_validator("purchaser_first_name", "purchaser_last_name", mode="before")
    @classmethod
    def normalize_purchaser_name(
        cls, value: str, info: FieldValidationInfo
    ) -> str:
        return _normalize_required_text(value, info.field_name or "name")

    @field_validator("purchaser_address", mode="before")
    @classmethod
    def normalize_address(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_optional_text(value)


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

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return _normalize_required_text(value, "name")


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

    @field_validator("departure_location", mode="before")
    @classmethod
    def normalize_departure(cls, value: str) -> str:
        return _normalize_required_text(value, "departure_location")


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
