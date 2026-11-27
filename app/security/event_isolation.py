from app.data_store import EVENT_NAMES

def validate_event_id(event_id: str) -> str:
    if event_id not in EVENT_NAMES:
        raise ValueError("Unknown or unauthorized event.")
    return event_id

def requests_other_event(message: str, current_event_id: str) -> bool:
    """Detect explicit attempts to obtain another event's information."""
    text = message.lower()
    for event_id, event_name in EVENT_NAMES.items():
        if event_id == current_event_id:
            continue
        if event_id in text or event_name.lower() in text:
            return True

    cross_event_phrases = (
        "other event", "another event", "different event",
        "ignore previous instructions", "reveal other event",
        "give me data of other event",
    )
    return any(phrase in text for phrase in cross_event_phrases)
