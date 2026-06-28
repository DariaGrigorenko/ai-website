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



IMAGE_LIBRARY = {
    "coffee": "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?auto=format&fit=crop&w=1200&q=80",
    "food": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1200&q=80",
    "beauty": "https://images.unsplash.com/photo-1560066984-138dadb4c0356?auto=format&fit=crop&w=1200&q=80",
    "fitness": "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?auto=format&fit=crop&w=1200&q=80",
    "yoga": "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?auto=format&fit=crop&w=1200&q=80",
    "education": "https://images.unsplash.com/photo-1523580846011-d3a5bc25702b?auto=format&fit=crop&w=1200&q=80",
    "business": "https://images.unsplash.com/photo-1497366811353-6870744d04b2?auto=format&fit=crop&w=1200&q=80",
    "portfolio": "https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=1200&q=80",
    "event": "https://images.unsplash.com/photo-1511795409834-ef04bbd61622?auto=format&fit=crop&w=1200&q=80",
    "technology": "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&q=80",
    "interior": "https://images.unsplash.com/photo-1518005020951-eccb494ad742?auto=format&fit=crop&w=1200&q=80",
    "travel": "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=80",
    "health": "https://images.unsplash.com/photo-1505751172876-fa1923c5c528?auto=format&fit=crop&w=1200&q=80",
    "creative": "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=80",
    "default": "https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1200&q=80",
}


def get_image_url(category: Any) -> str:
    key = str(category or "").strip().lower()
    return IMAGE_LIBRARY.get(key, IMAGE_LIBRARY["default"])


def get_section_image(section: dict[str, Any], site_json: dict[str, Any]) -> tuple[str, str]:
    image = section.get("image") if isinstance(section.get("image"), dict) else {}
    design = site_json.get("design", {}) if isinstance(site_json.get("design"), dict) else {}
    category = image.get("category") or section.get("imageCategory") or design.get("imageCategory") or "default"
    alt = image.get("alt") or section.get("imageAlt") or f"Изображение для сайта {site_json.get('siteName', '')}"
    return get_image_url(category), escape(str(alt))

def normalize_button_target(raw_target: Any, site_json: dict[str, Any]) -> str:
    contact = site_json.get("contact", {}) if isinstance(site_json.get("contact"), dict) else {}
    phone = str(contact.get("phone") or "").strip()
    email = str(contact.get("email") or "").strip()
    value = str(raw_target or "").strip()
    low = value.lower()

    if value.startswith("#"):
        if low in {"#contact", "#contacts", "#kontakt", "#контакты", "#zayavka", "#request"}:
            return "#contacts"
        return value

    if low.startswith(("http://", "https://", "tel:", "mailto:")):
        return value

    if "тел" in low or "звон" in low or "phone" in low or "call" in low:
        return f"tel:{phone}" if phone else "#contacts"

    if "mail" in low or "поч" in low or "email" in low:
        return f"mailto:{email}" if email else "#contacts"

    return "#contacts"


def render_buttons(buttons: list[dict[str, Any]], site_json: dict[str, Any]) -> str:
    html = ""
    if not buttons:
        buttons = [{"text": "Связаться", "target": "#contacts"}]

    for index, button in enumerate(buttons):
        text = escape(str(button.get("text") or f"Кнопка {index + 1}"))
        target = escape(normalize_button_target(button.get("target"), site_json))
        class_name = "site-btn" if index == 0 else "site-btn site-btn-outline"
        html += f'<a class="{class_name}" href="{target}">{text}</a>'
    return html


def render_section(section: dict[str, Any], page_index: int, site_json: dict[str, Any]) -> str:
    section_type = section.get("type")

    if section_type == "hero":
        title = escape(str(section.get("title") or ""))
        subtitle = escape(str(section.get("subtitle") or ""))
        image_url, image_alt = get_section_image(section, site_json)
        buttons = section.get("buttons")
        if not isinstance(buttons, list):
            button_text = section.get("buttonText", "Подробнее")
            buttons = [{"text": button_text, "target": "#contacts"}]
        return f"""
        <section class="hero-block">
            <div class="hero-content">
                <h1>{title}</h1>
                <p>{subtitle}</p>
                <div class="button-row">{render_buttons(buttons, site_json)}</div>
            </div>
            <div class="hero-visual">
                <img class="hero-image" src="{image_url}" alt="{image_alt}" loading="lazy">
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


def ensure_contact_section(site_json: dict[str, Any]) -> str:
    contact = site_json.get("contact", {}) if isinstance(site_json.get("contact"), dict) else {}
    phone = escape(str(contact.get("phone") or "+7 900 123-45-67"))
    email = escape(str(contact.get("email") or "hello@example.ru"))
    return f"""
    <section class="content-section contact-section" id="contacts">
        <h2>Контакты</h2>
        <div class="contact-grid">
            <div><strong>Телефон</strong><p>{phone}</p></div>
            <div><strong>Email</strong><p>{email}</p></div>
            <div><strong>Заявка</strong><p>Оставьте сообщение удобным способом, и мы свяжемся с вами.</p></div>
        </div>
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
    has_contacts = False

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
                if section.get("type") == "contact" and page_index == 0:
                    has_contacts = True
                content_html += render_section(section, page_index, site_json)
        if page_index == 0 and not has_contacts:
            content_html += ensure_contact_section(site_json)
            has_contacts = True
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
            font-family: Georgia, "Times New Roman", serif;
            background:
              linear-gradient(160deg, {primary} 0%, {secondary} 54%, {surface} 100%);
            color: {text};
            min-height: 100vh;
        }}
        .site-header {{
            position: sticky; top: 0; z-index: 20;
            width: min(1120px, 92%);
            margin: 22px auto 0;
            padding: 16px 22px;
            background: rgba(255,255,255,0.10);
            backdrop-filter: blur(18px);
            border: 1px solid rgba(255,255,255,0.18);
            border-radius: 999px;
            display: flex; justify-content: space-between; align-items: center; gap: 18px;
            box-shadow: 0 18px 55px rgba(0,0,0,.22);
        }}
        .brand {{ color: {text}; font-size: 22px; font-weight: 700; text-decoration: none; letter-spacing: -0.03em; }}
        nav {{ display: flex; gap: 10px; flex-wrap: wrap; }}
        nav a {{ color: {text}; opacity: .88; text-decoration: none; font-size: 14px; padding: 9px 13px; border-radius: 999px; background: rgba(255,255,255,.08); }}
        nav a:hover {{ background: {accent}; color: #fff; opacity: 1; }}
        .page-wrapper {{ width: 84%; max-width: 1160px; margin: 0 auto; padding: 54px 0; }}
        .hero-block {{ min-height: 560px; display: grid; grid-template-columns: 0.95fr 1.05fr; gap: 42px; align-items: center; }}
        h1 {{ font-size: clamp(42px, 8vw, 88px); line-height: .93; margin-bottom: 24px; letter-spacing: -0.065em; font-weight: 700; }}
        h2 {{ font-size: clamp(30px, 5vw, 54px); line-height: 1; margin-bottom: 22px; letter-spacing: -0.04em; }}
        p {{ font-family: Arial, sans-serif; font-size: 18px; line-height: 1.75; opacity: .88; }}
        .button-row {{ display: flex; gap: 13px; flex-wrap: wrap; margin-top: 30px; }}
        .site-btn {{ display: inline-block; padding: 15px 22px; border-radius: 999px; background: {accent}; color: #fff; text-decoration: none; font-family: Arial, sans-serif; font-weight: 800; box-shadow: 0 12px 30px {accent}55; }}
        .site-btn-outline {{ background: rgba(255,255,255,.10); border: 1px solid rgba(255,255,255,.30); color: {text}; box-shadow: none; }}
        .hero-visual {{ min-height: 430px; position: relative; background: {surface}; border-radius: 48px 48px 48px 8px; box-shadow: 0 32px 80px rgba(0,0,0,.34); overflow: hidden; transform: rotate(1deg); }}
        .hero-image {{ width: 100%; height: 100%; min-height: 430px; object-fit: cover; display: block; filter: saturate(1.05) contrast(1.03); }}
        .hero-visual::after {{ content: ""; position: absolute; inset: 0; background: linear-gradient(180deg, transparent 50%, rgba(0,0,0,.34)); pointer-events: none; }}
        .content-section {{ margin: 30px 0; padding: clamp(28px, 5vw, 52px); background: rgba(255,255,255,.11); border: 1px solid rgba(255,255,255,.16); border-radius: 38px; box-shadow: 0 20px 60px rgba(0,0,0,.20); }}
        .features-grid, .contact-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }}
        .feature-item, .contact-grid div {{ padding: 24px; background: rgba(255,255,255,.13); border: 1px solid rgba(255,255,255,.16); border-radius: 28px; }}
        .feature-item strong, .contact-grid strong {{ display: block; font-family: Arial, sans-serif; font-size: 18px; margin-bottom: 10px; }}
        .page-heading {{ padding: 48px 0 12px; }}
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
