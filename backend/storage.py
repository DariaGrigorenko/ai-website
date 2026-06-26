import json
from pathlib import Path


BASE_DIR = Path(file).resolve().parent
PROJECTS_FILE = BASE_DIR / "projects.json"


def load_projects():
    if not PROJECTS_FILE.exists():
        return []

    try:
        with open(PROJECTS_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        return []


def save_projects(projects):
    with open(PROJECTS_FILE, "w", encoding="utf-8") as file:
        json.dump(projects, file, ensure_ascii=False, indent=2)


def find_project_by_slug(slug):
    projects = load_projects()

    for project in projects:
        if project.get("publicSlug") == slug:
            return project

    return None
