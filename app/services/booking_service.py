def get_booking_status(event_id: str, booking_id: str) -> str:
    """Mock API supplied by the assignment. Replace with authenticated HTTP API in production."""
    return f"Booking {booking_id} for {event_id} is confirmed."
