from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from slugify import slugify

from storage import load_projects, save_projects, find_project_by_slug

app = FastAPI(title="HGGps Backend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateProjectRequest(BaseModel):
    description: str
    siteType: str
    goal: str
    style: str


def create_mock_site(description: str, site_type: str, goal: str, style: str) -> dict:
    return {
        "siteName": "Сайт для вашего проекта",
        "siteType": site_type,
        "goal": goal,
        "style": style,
        "pages": [
            {
                "title": "Главная",
                "slug": "/",
                "type": "home",
                "sections": [
                    {
                        "type": "hero",
                        "title": "Сайт для вашего проекта",
                        "subtitle": description,
                        "buttonText": "Оставить заявку"
                    },
                    {
                        "type": "features",
                        "title": "Преимущества",
                        "items": [
                            "Быстрое создание сайта",
                            "Понятная структура",
                            "Готовые тексты"
                        ]
                    }
                ]
            },
            {
                "title": "О проекте",
                "slug": "/about",
                "type": "about",
                "sections": [
                    {
                        "type": "text",
                        "title": "О проекте",
                        "description": "Этот сайт был создан с помощью HGGps на основе описания пользователя."
                    }
                ]
            },
            {
                "title": "Контакты",
                "slug": "/contact",
                "type": "contact",
                "sections": [
                    {
                        "type": "contact",
                        "title": "Контакты",
                        "phone": "+7 000 000-00-00",
                        "email": "example@email.com",
                        "address": "Адрес будет добавлен позже"
                    }
                ]
            }
        ]
    }


def make_unique_slug(site_name: str) -> str:
    projects = load_projects()

    base_slug = slugify(site_name) or "site"
    slug = base_slug
    counter = 1

    existing_slugs = {project.get("publicSlug") for project in projects}

    while slug in existing_slugs:
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug


def render_site_html(site_json: dict) -> str:
    site_name = site_json.get("siteName", "Сайт")
    pages = site_json.get("pages", [])

    menu_html = ""
    content_html = ""

    for page in pages:
        title = page.get("title", "Страница")
        slug = page.get("slug", "/")
        anchor = slug.replace("/", "") or "home"

        menu_html += f'<a href="#{anchor}">{title}</a>'

        content_html += f'<section id="{anchor}" class="page-section">'
        content_html += f"<h2>{title}</h2>"

        for section in page.get("sections", []):
            section_type = section.get("type")

            if section_type == "hero":
                content_html += f"""
                <div class="hero">
                    <h1>{section.get("title", "")}</h1>
                    <p>{section.get("subtitle", "")}</p>
                    <button>{section.get("buttonText", "Подробнее")}</button>
                </div>
                """

            elif section_type == "features":
                items = section.get("items", [])
                content_html += f"<div class='card'><h3>{section.get('title', 'Преимущества')}</h3><ul>"
                for item in items:
                    content_html += f"<li>{item}</li>"
                content_html += "</ul></div>"

            elif section_type == "text":
                content_html += f"""
                <div class="card">
                    <h3>{section.get("title", "")}</h3>
                    <p>{section.get("description", "")}</p>
                </div>
                """

            elif section_type == "contact":
                content_html += f"""
                <div class="card">
                    <h3>{section.get("title", "Контакты")}</h3>
                    <p>Телефон: {section.get("phone", "")}</p>
                    <p>Email: {section.get("email", "")}</p>
                    <p>Адрес: {section.get("address", "")}</p>
                </div>
                """

        content_html += "</section>"

    return f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>{site_name}</title>
        <style>
            body {{
                margin: 0;
                font-family: Arial, sans-serif;
                background: #0b0b0f;
                color: #f5f5f5;
            }}

            header {{
                padding: 24px 8%;
                background: #111116;
                color: white;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid #2a2a32;
            }}

            nav a {{
                color: #d1d5db;
                margin-left: 20px;
                text-decoration: none;
            }}

            nav a:hover {{
                color: #ef233c;
            }}

            .page-section {{
                padding: 60px 8%;
                max-width: 1100px;
                margin: 0 auto;
            }}

            .hero, .card {{
                background: #111116;
                padding: 40px;
                border-radius: 24px;
                border: 1px solid #2a2a32;
                box-shadow: 0 20px 50px rgba(0,0,0,0.35);
                margin-bottom: 24px;
            }}

            h1 {{
                font-size: 42px;
                margin-bottom: 16px;
            }}

            h2 {{
                font-size: 32px;
                margin-bottom: 24px;
            }}

            p, li {{
                color: #a1a1aa;
                line-height: 1.6;
            }}

            button {{
                margin-top: 20px;
                padding: 14px 24px;
                border: none;
                border-radius: 12px;
                background: #ef233c;
                color: white;
                font-size: 16px;
                cursor: pointer;
            }}

            button:hover {{
                background: #c9182b;
            }}
        </style>
    </head>
    <body>
        <header>
            <strong>{site_name}</strong>
            <nav>{menu_html}</nav>
        </header>

        {content_html}
    </body>
    </html>
    """


@app.get("/")
def health_check():
    return {
        "status": "ok",
        "service": "HGGps Backend API"
    }


@app.post("/api/projects/generate")
def generate_project(data: GenerateProjectRequest, request: Request):
    if len(data.description) < 10:
        raise HTTPException(
            status_code=400,
            detail="Описание проекта слишком короткое"
        )

    project_id = str(uuid4())

    site_json = create_mock_site(
        description=data.description,
        site_type=data.siteType,
        goal=data.goal,
        style=data.style
    )

    slug = make_unique_slug(site_json["siteName"])
    expires_at = datetime.now() + timedelta(days=7)

    base_url = str(request.base_url).rstrip("/")
    full_public_url = f"{base_url}/s/{slug}"

    project = {
        "id": project_id,
        "name": site_json["siteName"],
        "description": data.description,
        "siteType": data.siteType,
        "goal": data.goal,
        "style": data.style,
        "siteJson": site_json,
        "status": "temporary",
        "publicSlug": slug,
        "publicUrl": f"/s/{slug}",
        "fullPublicUrl": full_public_url,
        "createdAt": datetime.now().isoformat(),
        "expiresAt": expires_at.isoformat()
    }

    projects = load_projects()
    projects.append(project)
    save_projects(projects)

    return project


@app.get("/api/public/{slug}")
def get_public_site_json(slug: str):
    project = find_project_by_slug(slug)

    if not project:
        raise HTTPException(status_code=404, detail="Сайт не найден")

    expires_at = datetime.fromisoformat(project["expiresAt"])

    if datetime.now() > expires_at:
        raise HTTPException(status_code=410, detail="Временная ссылка истекла")

    return {
        "siteJson": project["siteJson"],
        "expiresAt": project["expiresAt"]
    }


@app.get("/s/{slug}", response_class=HTMLResponse)
def open_public_site(slug: str):
    project = find_project_by_slug(slug)

    if not project:
        raise HTTPException(status_code=404, detail="Сайт не найден")

    expires_at = datetime.fromisoformat(project["expiresAt"])

    if datetime.now() > expires_at:
        return HTMLResponse(
            content="<h1>Срок действия временной ссылки истёк</h1>",
            status_code=410
        )

    html = render_site_html(project["siteJson"])

    return HTMLResponse(content=html)
