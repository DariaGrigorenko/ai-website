import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "projects.json"


def load_projects():
    if not DATA_FILE.exists():
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        return []


def save_projects(projects):
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(projects, file, ensure_ascii=False, indent=4)


def find_project_by_slug(slug):
    projects = load_projects()

    for project in projects:
        if project.get("publicSlug") == slug:
            return project

    return None
