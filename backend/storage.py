import json
import os

DATA_FILE = "projects.json"


def load_projects():
    if not os.path.exists(DATA_FILE):
        return []

    with open(DATA_FILE, "r", encoding="utf8") as f:
        return json.load(f)


def save_projects(projects):
    with open(DATA_FILE, "w", encoding="utf8") as f:
        json.dump(projects, f, ensure_ascii=False, indent=4)


def find_project_by_slug(slug):
    projects = load_projects()

    for project in projects:
        if project["publicSlug"] == slug:
            return project

    return None
