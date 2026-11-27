import re

UNHAPPY_TERMS = {
    "unhappy",
    "dissatisfied",
    "frustrated",
    "angry",
    "complaint",
    "complain",
    "disappointed",
    "disappointing",
    "unacceptable",
    "terrible",
    "poor service",
    "bad experience",
    "not satisfied",
    "very upset",
    "extremely upset",
    "not happy"
}


def detect_escalation(message: str) -> str | None:
    text = message.lower()

    is_vip = bool(re.search(r"\bvip\b", text))
    is_unhappy = any(term in text for term in UNHAPPY_TERMS)

    if is_vip and is_unhappy:
        return "HIGH_PRIORITY"

    if is_vip:
        return "VIP_ESCALATION"

    if is_unhappy:
        return "SUPPORT_ESCALATION"

    return None