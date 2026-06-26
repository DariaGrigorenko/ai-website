import json
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "projects.json"


def load_projects() -> list[dict[str, Any]]:
    if not DATA_FILE.exists():
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            if isinstance(data, list):
                return data
            return []
    except json.JSONDecodeError:
        return []


def save_projects(projects: list[dict[str, Any]]) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(projects, file, ensure_ascii=False, indent=2)


def find_project_by_slug(slug: str) -> dict[str, Any] | None:
    projects = load_projects()
    for project in projects:
        if project.get("publicSlug") == slug:
            return project
    return None
