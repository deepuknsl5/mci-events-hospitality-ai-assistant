from app.data_store import EVENT_NAMES
from app.rag.retriever import EventRetriever
from app.security.event_isolation import validate_event_id, requests_other_event
from app.services.booking_service import get_booking_status
from app.services.escalation_service import detect_escalation
from app.services.llm_service import generate_answer, generate_history_answer
from app.logging.conversation_logger import log_turn

class ChatService:
    def __init__(self, retriever: EventRetriever):
        self.retriever = retriever
        self.sessions: dict[tuple[str, str], list[dict]] = {}

    def chat(self, session_id: str, event_id: str, message: str, booking_id: str | None = None):
        validate_event_id(event_id)
        session_key = (session_id, event_id)

        history = self.sessions.setdefault(
            session_key, []
        )
        escalation = detect_escalation(message)

        if requests_other_event(message, event_id):
            answer = "I can only provide information for your currently selected event. I can't disclose information belonging to another event."
            retrieved = []
            booking_called = False
        elif booking_id or "booking status" in message.lower() or "booking" in message.lower():
            if not booking_id:
                answer = "Please provide your booking ID so I can check its status."
                booking_called = False
            else:
                answer = get_booking_status(event_id, booking_id)
                booking_called = True
            retrieved = []
        elif escalation and not any(
            word in message.lower()
            for word in [
                "what", "where", "when", "how",
                "can", "do", "is", "are",
                "tell me", "explain"
            ]
        ):
            answer = (
                "I'm sorry you're having this experience. "
                "Your concern has been flagged for our support team. "
                "Someone from the event support team should assist you."
            )
            retrieved = []
            booking_called = False

        else:
            matches = self.retriever.retrieve(message, event_id)
            retrieved = matches
            context = [item["content"] for item in matches]

            if not context:
                # First, check whether the question refers to this
                # session's previous conversation.
                answer = generate_history_answer(message, history)

                if not answer:
                    answer = (
                        "I don't have enough verified information "
                        "to answer that question. Please contact "
                        "the event support team."
                    )

            else:
                answer = generate_answer(message, context, history)

                if not answer:
                    answer = (
                        "According to the event information: "
                        + " ".join(context)
                    )

            booking_called = False
         

        if escalation:
            answer += f"\n\nYour request has been flagged for {escalation.replace('_', ' ').lower()}."
        history.extend([
            {"role": "user", "content": message},
            {"role": "assistant", "content": answer},
        ])
        # Keep bounded session history.
        self.sessions[session_key] = history[-12:]

        log_turn({
            "session_id": session_id,
            "event_id": event_id,
            "user_message": message,
            "assistant_response": answer,
            "retrieved_topics": [m["metadata"]["topic"] for m in retrieved],
            "booking_api_called": booking_called,
            "escalation": escalation,
        })
        return {
            "session_id": session_id,
            "event_id": event_id,
            "answer": answer,
            "escalation": escalation,
            "booking_api_called": booking_called,
            "retrieved": retrieved,
        }
