from datetime import datetime, timedelta
from html import escape
from uuid import uuid4
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from slugify import slugify

from ai_generator import generate_site
from storage import load_projects, save_projects, find_project_by_slug

app = FastAPI(title="HGGps Backend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://dariagrigorenko.github.io",
        "https://dariagrigorenko.github.io/ai-website",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateProjectRequest(BaseModel):
    description: str = Field(..., min_length=10)
    companyName: str = Field(default="")
    siteType: str = Field(default="Лендинг")
    goal: str = Field(default="Создать сайт")
    designPreferences: str = Field(default="")
    desiredInfo: str = Field(default="")
    contactEmail: str = Field(default="")
    contactPhone: str = Field(default="")
    buttonCount: int = Field(default=1, ge=1, le=5)
    previousSiteJson: dict[str, Any] | None = None
    regenerationNote: str = Field(default="")


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


def css_color(site_json: dict[str, Any], key: str, fallback: str) -> str:
    design = site_json.get("design", {})
    value = str(design.get(key, fallback))
    if value.startswith("#") and len(value) == 7:
        return value
    return fallback


def render_buttons(buttons: list[dict[str, Any]]) -> str:
    html = ""
    for index, button in enumerate(buttons):
        text = escape(str(button.get("text") or f"Кнопка {index + 1}"))
        raw_target = str(button.get("target") or "#contacts").strip()
        if raw_target.startswith("tel:") or raw_target.startswith("mailto:") or raw_target.startswith("http://") or raw_target.startswith("https://"):
            target = escape(raw_target)
        else:
            target = "#contacts"
        class_name = "site-btn" if index == 0 else "site-btn site-btn-outline"
        html += f'<a class="{class_name}" href="{target}">{text}</a>'
    return html


def render_section(section: dict[str, Any], page_index: int) -> str:
    section_type = section.get("type")

    if section_type == "hero":
        title = escape(str(section.get("title") or ""))
        subtitle = escape(str(section.get("subtitle") or ""))
        buttons = section.get("buttons")
        if not isinstance(buttons, list):
            button_text = section.get("buttonText", "Подробнее")
            buttons = [{"text": button_text, "target": "#contacts"}]
        return f"""
        <section class="hero-block">
            <div class="hero-content">
                <h1>{title}</h1>
                <p>{subtitle}</p>
                <div class="button-row">{render_buttons(buttons)}</div>
            </div>
            <div class="hero-visual">
                <div class="visual-card big"></div>
                <div class="visual-card small"></div>
                <div class="visual-card line"></div>
            </div>
        </section>
        """

    if section_type == "features":
        title = escape(str(section.get("title") or "Преимущества"))
        items = section.get("items")
        if not isinstance(items, list):
            items = []
        items_html = ""
        for item in items:
            if isinstance(item, dict):
                item_title = escape(str(item.get("title") or "Преимущество"))
                item_description = escape(str(item.get("description") or ""))
                items_html += f'<div class="feature-item"><strong>{item_title}</strong><p>{item_description}</p></div>'
            else:
                items_html += f'<div class="feature-item"><strong>{escape(str(item))}</strong></div>'
        return f"""
        <section class="content-section">
            <h2>{title}</h2>
            <div class="features-grid">{items_html}</div>
        </section>
        """

    if section_type == "text":
        title = escape(str(section.get("title") or "О проекте"))
        description = escape(str(section.get("description") or ""))
        return f"""
        <section class="content-section card-section">
            <h2>{title}</h2>
            <p>{description}</p>
        </section>
        """

    if section_type == "contact":
        title = escape(str(section.get("title") or "Контакты"))
        phone = escape(str(section.get("phone") or ""))
        email = escape(str(section.get("email") or ""))
        address = escape(str(section.get("address") or ""))
        anchor_id = "contacts" if page_index == 0 else "contacts-page"
        return f"""
        <section class="content-section contact-section" id="{anchor_id}">
            <h2>{title}</h2>
            <div class="contact-grid">
                <div><strong>Телефон</strong><p>{phone}</p></div>
                <div><strong>Email</strong><p>{email}</p></div>
                <div><strong>Адрес</strong><p>{address}</p></div>
            </div>
        </section>
        """

    title = escape(str(section.get("title") or "Блок"))
    description = escape(str(section.get("description") or ""))
    return f"""
    <section class="content-section card-section">
        <h2>{title}</h2>
        <p>{description}</p>
    </section>
    """


def render_site_html(site_json: dict[str, Any]) -> str:
    site_name = escape(str(site_json.get("siteName") or "Сайт"))
    pages = site_json.get("pages") if isinstance(site_json.get("pages"), list) else []
    design = site_json.get("design", {}) if isinstance(site_json.get("design"), dict) else {}

    primary = css_color(site_json, "primaryColor", "#0b0b10")
    secondary = css_color(site_json, "secondaryColor", "#151827")
    accent = css_color(site_json, "accentColor", "#e11d2e")
    text = css_color(site_json, "textColor", "#ffffff")
    surface = css_color(site_json, "surfaceColor", "#12121a")

    menu_html = ""
    content_html = ""

    for page_index, page in enumerate(pages):
        page_title = escape(str(page.get("title") or "Страница"))
        page_slug = str(page.get("slug") or "/")
        anchor = "home" if page_index == 0 else slugify(page_title) or f"page-{page_index}"
        menu_html += f'<a href="#{escape(anchor)}">{page_title}</a>'

        content_html += f'<main id="{escape(anchor)}" class="page-wrapper">'
        if page_index > 0:
            content_html += f'<section class="page-heading"><h1>{page_title}</h1></section>'
        for section in page.get("sections", []):
            if isinstance(section, dict):
                content_html += render_section(section, page_index)
        content_html += '</main>'

    if not content_html:
        content_html = '<main class="page-wrapper"><section class="content-section"><h1>Сайт</h1><p>Контент не найден.</p></section></main>'

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{site_name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        html {{ scroll-behavior: smooth; }}
        body {{
            font-family: Arial, sans-serif;
            background:
              radial-gradient(circle at top left, {accent}44, transparent 34%),
              linear-gradient(135deg, {primary}, {secondary});
            color: {text};
            min-height: 100vh;
        }}
        .site-header {{
            position: sticky; top: 0; z-index: 20;
            padding: 18px 8%;
            background: rgba(10, 10, 16, 0.82);
            backdrop-filter: blur(14px);
            border-bottom: 1px solid rgba(255,255,255,0.12);
            display: flex; justify-content: space-between; align-items: center; gap: 18px;
        }}
        .brand {{ color: {accent}; font-size: 24px; font-weight: 800; text-decoration: none; }}
        nav {{ display: flex; gap: 16px; flex-wrap: wrap; }}
        nav a {{ color: {text}; opacity: .78; text-decoration: none; font-size: 15px; }}
        nav a:hover {{ color: {accent}; opacity: 1; }}
        .page-wrapper {{ width: 84%; max-width: 1180px; margin: 0 auto; padding: 42px 0; }}
        .hero-block {{ min-height: 520px; display: grid; grid-template-columns: 1.15fr .85fr; gap: 34px; align-items: center; }}
        .badge {{ display: inline-block; padding: 8px 14px; border-radius: 999px; background: {accent}24; color: {accent}; font-weight: 700; margin-bottom: 20px; }}
        h1 {{ font-size: clamp(38px, 7vw, 76px); line-height: .98; margin-bottom: 20px; letter-spacing: -0.04em; }}
        h2 {{ font-size: clamp(28px, 4vw, 44px); margin-bottom: 20px; }}
        p {{ font-size: 17px; line-height: 1.7; opacity: .86; }}
        .button-row {{ display: flex; gap: 12px; flex-wrap: wrap; margin-top: 28px; }}
        .site-btn {{ display: inline-block; padding: 14px 20px; border-radius: 14px; background: {accent}; color: #fff; text-decoration: none; font-weight: 800; }}
        .site-btn-outline {{ background: transparent; border: 1px solid rgba(255,255,255,.26); color: {text}; }}
        .hero-visual {{ min-height: 360px; position: relative; background: {surface}; border: 1px solid rgba(255,255,255,.16); border-radius: 30px; box-shadow: 0 28px 70px rgba(0,0,0,.35); overflow: hidden; }}
        .visual-card {{ position: absolute; border-radius: 22px; background: linear-gradient(135deg, {accent}, {secondary}); }}
        .visual-card.big {{ width: 72%; height: 52%; left: 9%; top: 12%; }}
        .visual-card.small {{ width: 42%; height: 28%; right: 8%; bottom: 12%; background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.18); }}
        .visual-card.line {{ width: 62%; height: 14px; left: 12%; bottom: 28%; border-radius: 999px; background: rgba(255,255,255,.18); }}
        .content-section {{ margin: 26px 0; padding: 34px; background: {surface}; border: 1px solid rgba(255,255,255,.14); border-radius: 26px; box-shadow: 0 20px 50px rgba(0,0,0,.25); }}
        .features-grid, .contact-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }}
        .feature-item, .contact-grid div {{ padding: 22px; background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.12); border-radius: 20px; }}
        .feature-item strong, .contact-grid strong {{ display: block; font-size: 18px; margin-bottom: 8px; }}
        .page-heading {{ padding: 44px 0 12px; }}
        @media (max-width: 850px) {{
            .site-header {{ flex-direction: column; align-items: flex-start; }}
            .page-wrapper {{ width: 90%; }}
            .hero-block, .features-grid, .contact-grid {{ grid-template-columns: 1fr; }}
            .hero-visual {{ min-height: 260px; }}
        }}
    </style>
</head>
<body>
    <header class="site-header">
        <a class="brand" href="#home">{site_name}</a>
        <nav>{menu_html}</nav>
    </header>
    {content_html}
</body>
</html>"""


@app.get("/")
def health_check():
    return {
        "status": "ok",
        "service": "HGGps Backend API",
        "aiProvider": "Gemini",
        "message": "Backend работает",
    }


@app.post("/api/projects/generate")
def generate_project(data: GenerateProjectRequest, request: Request):
    site_json = generate_site(
        description=data.description,
        site_type=data.siteType,
        goal=data.goal,
        company_name=data.companyName,
        design_preferences=data.designPreferences,
        desired_info=data.desiredInfo,
        contact_email=data.contactEmail,
        contact_phone=data.contactPhone,
        button_count=data.buttonCount,
        previous_site_json=data.previousSiteJson,
        regeneration_note=data.regenerationNote,
    )

    project_id = str(uuid4())
    slug = make_unique_slug(site_json.get("siteName", "site"))
    expires_at = datetime.now() + timedelta(days=7)
    base_url = str(request.base_url).rstrip("/")
    full_public_url = f"{base_url}/s/{slug}"

    project = {
        "id": project_id,
        "name": site_json.get("siteName", "Сайт"),
        "description": data.description,
        "companyName": data.companyName,
        "siteType": data.siteType,
        "goal": data.goal,
        "designPreferences": data.designPreferences,
        "desiredInfo": data.desiredInfo,
        "contactEmail": data.contactEmail,
        "contactPhone": data.contactPhone,
        "buttonCount": data.buttonCount,
        "siteJson": site_json,
        "generatedBy": site_json.get("_generatedBy", "unknown"),
        "aiModel": site_json.get("_aiModel"),
        "aiError": site_json.get("_aiError"),
        "status": "temporary",
        "publicSlug": slug,
        "publicUrl": f"/s/{slug}",
        "fullPublicUrl": full_public_url,
        "createdAt": datetime.now().isoformat(),
        "expiresAt": expires_at.isoformat(),
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
        "generatedBy": project.get("generatedBy"),
        "aiModel": project.get("aiModel"),
        "aiError": project.get("aiError"),
        "expiresAt": project["expiresAt"],
    }


@app.get("/s/{slug}", response_class=HTMLResponse)
def open_public_site(slug: str):
    project = find_project_by_slug(slug)
    if not project:
        raise HTTPException(status_code=404, detail="Сайт не найден")

    expires_at = datetime.fromisoformat(project["expiresAt"])
    if datetime.now() > expires_at:
        return HTMLResponse(content="<h1>Срок действия временной ссылки истёк</h1>", status_code=410)

    html = render_site_html(project["siteJson"])
    return HTMLResponse(content=html)
