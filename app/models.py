"""Database models for the My Social Networks API."""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import Enum as SAEnum, UniqueConstraint
from sqlmodel import Column, Field, Relationship, SQLModel


class GroupType(str, Enum):
    public = "public"
    private = "private"
    secret = "secret"


class ThreadContext(str, Enum):
    group = "group"
    event = "event"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True, max_length=255)
    full_name: str = Field(max_length=255)
    hashed_password: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    group_memberships: List["GroupMembership"] = Relationship(back_populates="user")
    organized_events: List["EventOrganizer"] = Relationship(back_populates="user")
    event_participations: List["EventParticipant"] = Relationship(
        back_populates="user"
    )
    messages: List["Message"] = Relationship(back_populates="author")
    photo_comments: List["PhotoComment"] = Relationship(back_populates="author")
    poll_votes: List["PollVote"] = Relationship(back_populates="voter")
    shopping_list_items: List["ShoppingListItem"] = Relationship(back_populates="owner")
    carpool_offers: List["CarpoolOffer"] = Relationship(back_populates="driver")


class GroupMembership(SQLModel, table=True):
    __tablename__ = "group_memberships"
    __table_args__ = (UniqueConstraint("group_id", "user_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="groups.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    is_admin: bool = Field(default=False)
    can_create_events: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    group: "Group" = Relationship(back_populates="memberships")
    user: User = Relationship(back_populates="group_memberships")


class Group(SQLModel, table=True):
    __tablename__ = "groups"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255)
    description: Optional[str] = None
    icon: Optional[str] = Field(default=None, max_length=255)
    cover_photo: Optional[str] = Field(default=None, max_length=255)
    type: GroupType = Field(sa_column=Column(SAEnum(GroupType, name="group_type"), nullable=False))
    allow_member_posts: bool = Field(default=True)
    allow_member_events: bool = Field(default=True)
    created_by_id: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    memberships: List[GroupMembership] = Relationship(back_populates="group")
    discussion_threads: List["DiscussionThread"] = Relationship(back_populates="group")
    events: List["Event"] = Relationship(back_populates="group")


class EventOrganizer(SQLModel, table=True):
    __tablename__ = "event_organizers"
    __table_args__ = (UniqueConstraint("event_id", "user_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="events.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    event: "Event" = Relationship(back_populates="organizers")
    user: User = Relationship(back_populates="organized_events")


class EventParticipant(SQLModel, table=True):
    __tablename__ = "event_participants"
    __table_args__ = (UniqueConstraint("event_id", "user_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="events.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    joined_at: datetime = Field(default_factory=datetime.utcnow)

    event: "Event" = Relationship(back_populates="participants")
    user: User = Relationship(back_populates="event_participations")


class Event(SQLModel, table=True):
    __tablename__ = "events"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255)
    description: Optional[str] = None
    start_date: datetime = Field(nullable=False)
    end_date: datetime = Field(nullable=False)
    location: str = Field(max_length=255)
    cover_photo: Optional[str] = Field(default=None, max_length=255)
    is_private: bool = Field(default=False)
    created_by_id: int = Field(foreign_key="users.id")
    group_id: Optional[int] = Field(default=None, foreign_key="groups.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    carpool_enabled: bool = Field(default=False)
    shopping_list_enabled: bool = Field(default=False)
    billetterie_enabled: bool = Field(default=False)
    polls_enabled: bool = Field(default=True)

    group: Optional[Group] = Relationship(back_populates="events")
    organizers: List[EventOrganizer] = Relationship(back_populates="event")
    participants: List[EventParticipant] = Relationship(back_populates="event")
    discussion_threads: List["DiscussionThread"] = Relationship(back_populates="event")
    albums: List["PhotoAlbum"] = Relationship(back_populates="event")
    polls: List["Poll"] = Relationship(back_populates="event")
    ticket_types: List["TicketType"] = Relationship(back_populates="event")
    shopping_items: List["ShoppingListItem"] = Relationship(back_populates="event")
    carpool_offers: List["CarpoolOffer"] = Relationship(back_populates="event")


class DiscussionThread(SQLModel, table=True):
    __tablename__ = "discussion_threads"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=255)
    context: ThreadContext = Field(
        sa_column=Column(SAEnum(ThreadContext, name="thread_context"), nullable=False)
    )
    group_id: Optional[int] = Field(default=None, foreign_key="groups.id")
    event_id: Optional[int] = Field(default=None, foreign_key="events.id")
    created_by_id: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    group: Optional[Group] = Relationship(back_populates="discussion_threads")
    event: Optional[Event] = Relationship(back_populates="discussion_threads")
    messages: List["Message"] = Relationship(back_populates="thread")


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    thread_id: int = Field(foreign_key="discussion_threads.id", index=True)
    author_id: int = Field(foreign_key="users.id")
    content: str
    parent_id: Optional[int] = Field(default=None, foreign_key="messages.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    thread: DiscussionThread = Relationship(back_populates="messages")
    author: User = Relationship(back_populates="messages")


class PhotoAlbum(SQLModel, table=True):
    __tablename__ = "photo_albums"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255)
    event_id: int = Field(foreign_key="events.id")
    created_by_id: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    event: Event = Relationship(back_populates="albums")
    photos: List["Photo"] = Relationship(back_populates="album")


class Photo(SQLModel, table=True):
    __tablename__ = "photos"

    id: Optional[int] = Field(default=None, primary_key=True)
    album_id: int = Field(foreign_key="photo_albums.id")
    uploaded_by_id: int = Field(foreign_key="users.id")
    url: str = Field(max_length=255)
    caption: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    album: PhotoAlbum = Relationship(back_populates="photos")
    comments: List["PhotoComment"] = Relationship(back_populates="photo")


class PhotoComment(SQLModel, table=True):
    __tablename__ = "photo_comments"

    id: Optional[int] = Field(default=None, primary_key=True)
    photo_id: int = Field(foreign_key="photos.id")
    author_id: int = Field(foreign_key="users.id")
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    photo: Photo = Relationship(back_populates="comments")
    author: User = Relationship(back_populates="photo_comments")


class Poll(SQLModel, table=True):
    __tablename__ = "polls"

    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="events.id")
    title: str = Field(max_length=255)
    created_by_id: int = Field(foreign_key="users.id")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    event: Event = Relationship(back_populates="polls")
    questions: List["PollQuestion"] = Relationship(back_populates="poll")


class PollQuestion(SQLModel, table=True):
    __tablename__ = "poll_questions"

    id: Optional[int] = Field(default=None, primary_key=True)
    poll_id: int = Field(foreign_key="polls.id")
    question: str

    poll: Poll = Relationship(back_populates="questions")
    options: List["PollOption"] = Relationship(back_populates="question")
    votes: List["PollVote"] = Relationship(back_populates="question")


class PollOption(SQLModel, table=True):
    __tablename__ = "poll_options"

    id: Optional[int] = Field(default=None, primary_key=True)
    question_id: int = Field(foreign_key="poll_questions.id")
    label: str

    question: PollQuestion = Relationship(back_populates="options")
    votes: List["PollVote"] = Relationship(back_populates="option")


class PollVote(SQLModel, table=True):
    __tablename__ = "poll_votes"
    __table_args__ = (UniqueConstraint("question_id", "voter_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    question_id: int = Field(foreign_key="poll_questions.id")
    option_id: int = Field(foreign_key="poll_options.id")
    voter_id: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    question: PollQuestion = Relationship(back_populates="votes")
    option: PollOption = Relationship(back_populates="votes")
    voter: User = Relationship(back_populates="poll_votes")


class TicketType(SQLModel, table=True):
    __tablename__ = "ticket_types"

    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="events.id")
    name: str
    price: float = Field(ge=0)
    quantity: int = Field(ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    event: Event = Relationship(back_populates="ticket_types")
    tickets: List["Ticket"] = Relationship(back_populates="ticket_type")


class Ticket(SQLModel, table=True):
    __tablename__ = "tickets"

    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_type_id: int = Field(foreign_key="ticket_types.id")
    purchaser_first_name: str
    purchaser_last_name: str
    purchaser_email: str
    purchaser_address: Optional[str] = None
    purchased_at: datetime = Field(default_factory=datetime.utcnow)

    ticket_type: TicketType = Relationship(back_populates="tickets")


class ShoppingListItem(SQLModel, table=True):
    __tablename__ = "shopping_list_items"
    __table_args__ = (UniqueConstraint("event_id", "name"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="events.id")
    owner_id: int = Field(foreign_key="users.id")
    name: str
    quantity: int = Field(ge=1)
    arrival_time: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)

    event: Event = Relationship(back_populates="shopping_items")
    owner: User = Relationship(back_populates="shopping_list_items")


class CarpoolOffer(SQLModel, table=True):
    __tablename__ = "carpool_offers"

    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="events.id")
    driver_id: int = Field(foreign_key="users.id")
    departure_location: str
    departure_time: datetime
    price: float = Field(ge=0)
    available_seats: int = Field(ge=1)
    max_detour_minutes: int = Field(ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    event: Event = Relationship(back_populates="carpool_offers")
    driver: User = Relationship(back_populates="carpool_offers")
