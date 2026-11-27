import json
from app.config import DATA_DIR

_records = json.loads((DATA_DIR / "events.json").read_text(encoding="utf-8"))
EVENT_NAMES = {r["event_id"]: r["event_name"] for r in _records}
