from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient


async def register_user(client: AsyncClient, email: str, password: str, full_name: str) -> dict:
    response = await client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def login_user(client: AsyncClient, email: str, password: str) -> str:
    response = await client.post(
        "/api/auth/token",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_end_to_end_social_network_flow(client: AsyncClient) -> None:
    """Covers the main happy path from onboarding to optional addons."""
    # Create two users and authenticate
    owner = await register_user(client, "owner@example.com", "StrongPass!1", "Owner One")
    owner_token = await login_user(client, owner["email"], "StrongPass!1")

    attendee = await register_user(client, "attendee@example.com", "StrongPass!1", "Attendee Two")
    attendee_token = await login_user(client, attendee["email"], "StrongPass!1")

    # Owner creates a group
    group_response = await client.post(
        "/api/groups",
        json={
            "name": "Master API Group",
            "description": "Group for API project",
            "icon": "https://example.com/icon.png",
            "cover_photo": "https://example.com/cover.png",
            "type": "public",
            "allow_member_posts": True,
            "allow_member_events": True,
        },
        headers=auth_header(owner_token),
    )
    assert group_response.status_code == 201, group_response.text
    group = group_response.json()

    # Add attendee to the group
    add_member_resp = await client.post(
        f"/api/groups/{group['id']}/members",
        json={
            "user_id": attendee["id"],
            "is_admin": False,
            "can_create_events": True,
        },
        headers=auth_header(owner_token),
    )
    assert add_member_resp.status_code == 201, add_member_resp.text

    # Owner creates an event with extended features
    start = datetime.now(timezone.utc) + timedelta(days=5)
    end = start + timedelta(hours=4)
    event_payload = {
        "name": "Launch Event",
        "description": "Product launch with networking",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "location": "Paris HQ",
        "cover_photo": "https://example.com/event.png",
        "is_private": False,
        "group_id": group["id"],
        "organizer_ids": [attendee["id"]],
        "carpool_enabled": True,
        "shopping_list_enabled": True,
        "billetterie_enabled": True,
        "polls_enabled": True,
    }
    event_response = await client.post(
        "/api/events",
        json=event_payload,
        headers=auth_header(owner_token),
    )
    assert event_response.status_code == 201, event_response.text
    event = event_response.json()

    # Attendee joins the event
    join_resp = await client.post(
        f"/api/events/{event['id']}/participants",
        json={"user_id": attendee["id"]},
        headers=auth_header(attendee_token),
    )
    assert join_resp.status_code == 201, join_resp.text

    # Owner creates a discussion thread for the event
    thread_resp = await client.post(
        "/api/discussions",
        json={
            "title": "Welcome thread",
            "context": "event",
            "event_id": event["id"],
        },
        headers=auth_header(owner_token),
    )
    assert thread_resp.status_code == 201, thread_resp.text
    thread = thread_resp.json()

    # Attendee posts a message
    message_resp = await client.post(
        f"/api/discussions/{thread['id']}/messages",
        json={"content": "Looking forward to it!"},
        headers=auth_header(attendee_token),
    )
    assert message_resp.status_code == 201, message_resp.text

    # Owner creates an album
    album_resp = await client.post(
        f"/api/media/events/{event['id']}/albums",
        json={"name": "Event Memories"},
        headers=auth_header(owner_token),
    )
    assert album_resp.status_code == 201, album_resp.text
    album = album_resp.json()

    # Attendee uploads a photo
    photo_resp = await client.post(
        f"/api/media/albums/{album['id']}/photos",
        json={"url": "https://example.com/photo.jpg", "caption": "Venue preview"},
        headers=auth_header(attendee_token),
    )
    assert photo_resp.status_code == 201, photo_resp.text
    photo = photo_resp.json()

    # Owner comments on the photo
    comment_resp = await client.post(
        f"/api/media/photos/{photo['id']}/comments",
        json={"content": "Great shot!"},
        headers=auth_header(owner_token),
    )
    assert comment_resp.status_code == 201, comment_resp.text

    # Owner creates a poll
    poll_resp = await client.post(
        f"/api/polls/events/{event['id']}",
        json={
            "title": "Dinner preferences",
            "questions": [
                {
                    "question": "What cuisine?",
                    "options": [
                        {"label": "Italian"},
                        {"label": "Japanese"},
                        {"label": "French"},
                    ],
                }
            ],
        },
        headers=auth_header(owner_token),
    )
    assert poll_resp.status_code == 201, poll_resp.text
    poll_id = poll_resp.json()["id"]

    poll_detail = await client.get(
        f"/api/polls/{poll_id}",
        headers=auth_header(attendee_token),
    )
    assert poll_detail.status_code == 200, poll_detail.text
    question = poll_detail.json()["questions"][0]
    option_id = question["options"][0]["id"]

    vote_resp = await client.post(
        f"/api/polls/{poll_id}/votes",
        json=[{"question_id": question["id"], "option_id": option_id}],
        headers=auth_header(attendee_token),
    )
    assert vote_resp.status_code == 200, vote_resp.text

    # Owner configures ticketing
    ticket_type_resp = await client.post(
        f"/api/tickets/events/{event['id']}/types",
        json={"name": "VIP", "price": 49.0, "quantity": 10},
        headers=auth_header(owner_token),
    )
    assert ticket_type_resp.status_code == 201, ticket_type_resp.text
    ticket_type = ticket_type_resp.json()

    ticket_purchase_resp = await client.post(
        f"/api/tickets/types/{ticket_type['id']}/purchase",
        json={
            "purchaser_first_name": "Guest",
            "purchaser_last_name": "One",
            "purchaser_email": "guest@example.com",
            "purchaser_address": "1 rue de Paris",
        },
    )
    assert ticket_purchase_resp.status_code == 201, ticket_purchase_resp.text

    # Attendee adds an item to the shopping list
    shopping_resp = await client.post(
        f"/api/addons/events/{event['id']}/shopping-items",
        json={
            "name": "Soft drinks",
            "quantity": 3,
            "arrival_time": (start - timedelta(hours=1)).isoformat(),
        },
        headers=auth_header(attendee_token),
    )
    assert shopping_resp.status_code == 201, shopping_resp.text

    # Attendee offers carpool
    carpool_resp = await client.post(
        f"/api/addons/events/{event['id']}/carpools",
        json={
            "departure_location": "Lyon",
            "departure_time": (start - timedelta(hours=5)).isoformat(),
            "price": 15.0,
            "available_seats": 3,
            "max_detour_minutes": 30,
        },
        headers=auth_header(attendee_token),
    )
    assert carpool_resp.status_code == 201, carpool_resp.text

    # Check event details reflect organizers and participants
    event_detail = await client.get(
        f"/api/events/{event['id']}",
        headers=auth_header(owner_token),
    )
    assert event_detail.status_code == 200, event_detail.text
    detail_json = event_detail.json()
    organizer_ids = {item["user_id"] for item in detail_json["organizers"]}
    participant_ids = {item["user_id"] for item in detail_json["participants"]}
    assert owner["id"] in organizer_ids
    assert attendee["id"] in organizer_ids
    assert attendee["id"] in participant_ids

    # Current user endpoint
    me_resp = await client.get("/api/users/me", headers=auth_header(owner_token))
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == owner["email"]
