import json
import os
from typing import Any

DATA_FILE = "projects.json"


def load_projects() -> list[dict[str, Any]]:
    if not os.path.exists(DATA_FILE):
        return []

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_projects(projects: list[dict[str, Any]]) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(projects, file, ensure_ascii=False, indent=2)


def find_project_by_slug(slug: str) -> dict[str, Any] | None:
    projects = load_projects()

    for project in projects:
        if project.get("publicSlug") == slug:
            return project

    return None
