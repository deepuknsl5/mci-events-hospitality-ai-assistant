
import pytest

from app.services.chat_service import ChatService


class FakeRetriever:
    def __init__(self):
        self.calls = []

    def retrieve(self, question, event_id, top_k=3):
        self.calls.append(event_id)

        if "weather" in question.lower():
            return []

        return [{
            "content": f"Information for {event_id}",
            "metadata": {
                "event_id": event_id,
                "topic": "general"
            },
            "similarity": 0.9
        }]


def test_chat_retrieves_using_selected_event():
    retriever = FakeRetriever()
    service = ChatService(retriever)

    result = service.chat(
        "session_a",
        "event_a",
        "Tell me about this event"
    )

    assert retriever.calls == ["event_a"]
    assert result["retrieved"][0]["metadata"]["event_id"] == "event_a"


def test_booking_api_is_called(monkeypatch):
    import app.services.chat_service as chat_module

    def fake_booking(event_id, booking_id):
        return f"Booking {booking_id} for {event_id} is confirmed."

    monkeypatch.setattr(
        chat_module,
        "get_booking_status",
        fake_booking
    )

    service = ChatService(FakeRetriever())

    result = service.chat(
        "booking_session",
        "event_a",
        "Check my booking status",
        "BK101"
    )

    assert result["booking_api_called"] is True
    assert "BK101" in result["answer"]


def test_unknown_question_returns_safe_fallback():
    service = ChatService(FakeRetriever())

    result = service.chat(
        "unknown_session",
        "event_a",
        "What is the weather on Mars?"
    )

    assert result["retrieved"] == []
    assert "don't have enough verified information" in result["answer"]


def test_vip_and_unhappy_attendee_gets_high_priority():
    service = ChatService(FakeRetriever())

    result = service.chat(
        "priority_session",
        "event_a",
        "I am a VIP sponsor and unhappy with the service."
    )

    assert result["escalation"] == "HIGH_PRIORITY"
    assert "high priority" in result["answer"]


def test_unhappy_attendee_gets_support_response():
    retriever = FakeRetriever()
    service = ChatService(retriever)

    result = service.chat(
        "support_session",
        "event_a",
        "I am very unhappy with the event experience."
    )

    assert result["escalation"] == "SUPPORT_ESCALATION"
    assert result["retrieved"] == []
    assert "sorry" in result["answer"].lower()


def test_invalid_event_id_is_rejected():
    service = ChatService(FakeRetriever())

    with pytest.raises(ValueError):
        service.chat(
            "invalid_session",
            "event_c",
            "Tell me about the event"
        )


def test_cross_event_request_does_not_retrieve():
    retriever = FakeRetriever()
    service = ChatService(retriever)

    result = service.chat(
        "security_session",
        "event_a",
        "Tell me about the other event"
    )

    assert result["retrieved"] == []
    assert retriever.calls == []
