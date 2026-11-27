import json
from datetime import datetime, timezone
from app.config import LOG_DIR

def log_turn(payload: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    with (LOG_DIR / "conversations.jsonl").open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")
