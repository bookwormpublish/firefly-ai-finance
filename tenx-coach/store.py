import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path.home() / ".tenx-coach"
IDEAS_FILE = DATA_DIR / "ideas.json"


def _load() -> dict:
    if not IDEAS_FILE.exists():
        return {"ideas": {}}
    return json.loads(IDEAS_FILE.read_text())


def _save(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IDEAS_FILE.write_text(json.dumps(data, indent=2))


def add_idea(text: str) -> str:
    data = _load()
    idea_id = uuid.uuid4().hex[:8]
    data["ideas"][idea_id] = {
        "id": idea_id,
        "text": text,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "validations": [],
    }
    _save(data)
    return idea_id


def list_ideas() -> list[dict]:
    return list(_load()["ideas"].values())


def get_idea(idea_id: str) -> dict | None:
    return _load()["ideas"].get(idea_id)


def save_validation(idea_id: str, validation: dict) -> None:
    data = _load()
    if idea_id not in data["ideas"]:
        raise KeyError(f"Idea {idea_id} not found")
    validation["saved_at"] = datetime.now(timezone.utc).isoformat()
    data["ideas"][idea_id]["validations"].append(validation)
    _save(data)
