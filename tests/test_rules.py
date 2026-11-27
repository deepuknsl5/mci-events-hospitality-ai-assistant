from app.services.escalation_service import detect_escalation
from app.security.event_isolation import requests_other_event, validate_event_id
from app.services.chat_service import ChatService
def test_vip_and_unhappy_escalates_high_priority():
    assert detect_escalation("I am a VIP sponsor and unhappy") == "HIGH_PRIORITY"

def test_vip_escalates():
    assert detect_escalation("I am a VIP sponsor") == "VIP_ESCALATION"

def test_dissatisfaction_escalates():
    assert detect_escalation("I am dissatisfied") == "SUPPORT_ESCALATION"

def test_other_event_is_blocked():
    assert requests_other_event("Tell me about the other event", "event_a")

def test_explicit_other_event_name_is_blocked():
    assert requests_other_event("Tell me about Hospitality Leadership Forum", "event_a")

def test_current_event_is_valid():
    assert validate_event_id("event_a") == "event_a"
    
class FakeRetriever:
    def retrieve(self, question, event_id, top_k=3):
        return [{
            "content": f"Information for {event_id}",
            "metadata": {
                "event_id": event_id,
                "topic": "general"
            },
            "similarity": 0.9
        }]


def test_session_history_isolated_by_event():
    service = ChatService(FakeRetriever())

    service.chat(
        session_id="shared_session",
        event_id="event_a",
        message="Tell me about Event A"
    )

    service.chat(
        session_id="shared_session",
        event_id="event_b",
        message="Tell me about Event B"
    )

    event_a_history = service.sessions[
        ("shared_session", "event_a")
    ]

    event_b_history = service.sessions[
        ("shared_session", "event_b")
    ]

    assert len(event_a_history) == 2
    assert len(event_b_history) == 2
    
    assert "Event A" in event_a_history[0]["content"]
    assert "Event B" in event_b_history[0]["content"]
