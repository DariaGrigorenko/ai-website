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
    design = site_json.get("design", {}) if isinstance(site_json.get("design"), dict) else {}
    value = str(design.get(key, fallback))
    if value.startswith("#") and len(value) == 7:
        return value
    return fallback


def collect_valid_anchors(site_json: dict[str, Any]) -> list[str]:
    anchors: list[str] = []
    pages = site_json.get("pages") if isinstance(site_json.get("pages"), list) else []
    for page_index, page in enumerate(pages):
        if page_index == 0:
            anchors.append("home")
        for section_index, section in enumerate(page.get("sections", [])):
            if isinstance(section, dict):
                anchor = str(section.get("anchorId") or "").strip().lstrip("#")
                if anchor and anchor not in anchors:
                    anchors.append(anchor)
    if "contacts" not in anchors:
        anchors.append("contacts")
    return anchors


def normalize_button_target(raw_target: Any, site_json: dict[str, Any]) -> str:
    contact = site_json.get("contact", {}) if isinstance(site_json.get("contact"), dict) else {}
    phone = str(contact.get("phone") or "").strip()
    email = str(contact.get("email") or "").strip()
    value = str(raw_target or "").strip()
    low = value.lower()
    valid_anchors = collect_valid_anchors(site_json)

    if value.startswith("#"):
        anchor = value[1:].strip()
        if anchor in valid_anchors:
            return f"#{anchor}"
        if low in {"#contact", "#kontakt", "#контакты", "#zayavka", "#request"}:
            return "#contacts"
        return "#contacts"

    if low.startswith(("tel:", "mailto:")):
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

    valid_anchors = collect_valid_anchors(site_json)
    available_block_targets = [f"#{a}" for a in valid_anchors if a not in {"home"}]
    used_targets: set[str] = set()

    for index, button in enumerate(buttons):
        text = escape(str(button.get("text") or f"Кнопка {index + 1}"))
        target = normalize_button_target(button.get("target"), site_json)

        # Если ИИ случайно сделал все кнопки на один блок, разводим их по разным разделам сайта.
        if target in used_targets and available_block_targets:
            for candidate in available_block_targets:
                if candidate not in used_targets:
                    target = candidate
                    break

        used_targets.add(target)
        class_name = "site-btn" if index == 0 else "site-btn site-btn-outline"
        html += f'<a class="{class_name}" href="{escape(target)}">{text}</a>'
    return html


def section_anchor(section: dict[str, Any], page_index: int, section_index: int) -> str:
    anchor = str(section.get("anchorId") or "").strip().lstrip("#")
    if anchor:
        return anchor
    section_type = str(section.get("type") or "section")
    if section_type == "hero" and page_index == 0:
        return "home"
    if section_type == "contact":
        return "contacts" if page_index == 0 else "contacts-page"
    return f"section-{page_index}-{section_index}"


def render_section(section: dict[str, Any], page_index: int, section_index: int, site_json: dict[str, Any]) -> str:
    section_type = section.get("type")
    anchor_id = escape(section_anchor(section, page_index, section_index))

    if section_type == "hero":
        title = escape(str(section.get("title") or ""))
        subtitle = escape(str(section.get("subtitle") or ""))
        buttons = section.get("buttons")
        if not isinstance(buttons, list):
            button_text = section.get("buttonText", "Подробнее")
            buttons = [{"text": button_text, "target": "#contacts"}]
        return f"""
        <section class="hero-block" id="{anchor_id}">
            <div class="hero-content">
                <p class="hero-kicker">{escape(str(site_json.get('goal') or ''))}</p>
                <h1>{title}</h1>
                <p>{subtitle}</p>
                <div class="button-row">{render_buttons(buttons, site_json)}</div>
            </div>
            <div class="hero-panel">
                <div class="panel-line wide"></div>
                <div class="panel-line"></div>
                <div class="panel-line short"></div>
                <div class="panel-grid"><span></span><span></span><span></span></div>
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
        <section class="content-section" id="{anchor_id}">
            <h2>{title}</h2>
            <div class="features-grid">{items_html}</div>
        </section>
        """

    if section_type == "text":
        title = escape(str(section.get("title") or "О проекте"))
        description = escape(str(section.get("description") or ""))
        return f"""
        <section class="content-section card-section" id="{anchor_id}">
            <h2>{title}</h2>
            <p>{description}</p>
        </section>
        """

    if section_type == "contact":
        title = escape(str(section.get("title") or "Контакты"))
        phone = escape(str(section.get("phone") or ""))
        email = escape(str(section.get("email") or ""))
        address = escape(str(section.get("address") or ""))
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
    <section class="content-section card-section" id="{anchor_id}">
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

    primary = css_color(site_json, "primaryColor", "#f6efe7")
    secondary = css_color(site_json, "secondaryColor", "#fffaf3")
    accent = css_color(site_json, "accentColor", "#7c4a2d")
    text = css_color(site_json, "textColor", "#201915")
    surface = css_color(site_json, "surfaceColor", "#ffffff")

    menu_html = ""
    content_html = ""
    has_contacts = False

    for page_index, page in enumerate(pages):
        page_title = escape(str(page.get("title") or "Страница"))
        anchor = "home" if page_index == 0 else slugify(page_title) or f"page-{page_index}"
        menu_html += f'<a href="#{escape(anchor)}">{page_title}</a>'

        content_html += f'<main class="page-wrapper">'
        if page_index > 0:
            content_html += f'<section id="{escape(anchor)}" class="page-heading"><h1>{page_title}</h1></section>'
        for section_index, section in enumerate(page.get("sections", [])):
            if isinstance(section, dict):
                if section.get("type") == "contact":
                    has_contacts = True
                content_html += render_section(section, page_index, section_index, site_json)
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
            font-family: Inter, Arial, sans-serif;
            background: radial-gradient(circle at top left, {secondary} 0%, {primary} 42%, {surface} 100%);
            color: {text};
            min-height: 100vh;
        }}
        .site-header {{
            position: sticky; top: 0; z-index: 20;
            width: min(1120px, 92%);
            margin: 18px auto 0;
            padding: 14px 18px;
            background: rgba(255,255,255,0.78);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(0,0,0,0.08);
            border-radius: 22px;
            display: flex; justify-content: space-between; align-items: center; gap: 18px;
            box-shadow: 0 14px 45px rgba(0,0,0,.08);
        }}
        .brand {{ color: {text}; font-size: 21px; font-weight: 900; text-decoration: none; letter-spacing: -0.03em; }}
        nav {{ display: flex; gap: 8px; flex-wrap: wrap; }}
        nav a {{ color: {text}; text-decoration: none; font-size: 14px; padding: 9px 12px; border-radius: 14px; background: rgba(0,0,0,.04); }}
        nav a:hover {{ background: {accent}; color: #fff; }}
        .page-wrapper {{ width: min(1120px, 90%); margin: 0 auto; padding: 52px 0; }}
        .hero-block {{ min-height: 540px; display: grid; grid-template-columns: 1.05fr .95fr; gap: 34px; align-items: center; }}
        .hero-kicker {{ color: {accent}; font-size: 14px; font-weight: 900; text-transform: uppercase; letter-spacing: .12em; margin-bottom: 16px; }}
        h1 {{ font-size: clamp(42px, 7vw, 82px); line-height: .96; margin-bottom: 22px; letter-spacing: -0.06em; font-weight: 950; }}
        h2 {{ font-size: clamp(30px, 4.8vw, 52px); line-height: 1; margin-bottom: 22px; letter-spacing: -0.04em; }}
        p {{ font-size: 18px; line-height: 1.72; opacity: .82; }}
        .button-row {{ display: flex; gap: 12px; flex-wrap: wrap; margin-top: 28px; }}
        .site-btn {{ display: inline-block; padding: 14px 20px; border-radius: 16px; background: {accent}; color: #fff; text-decoration: none; font-weight: 900; box-shadow: 0 12px 30px {accent}44; }}
        .site-btn-outline {{ background: transparent; border: 1px solid {accent}; color: {accent}; box-shadow: none; }}
        .hero-panel {{ min-height: 380px; border-radius: 36px; background: linear-gradient(145deg, {surface}, rgba(255,255,255,.55)); border: 1px solid rgba(0,0,0,.08); padding: 36px; box-shadow: 0 26px 70px rgba(0,0,0,.12); }}
        .panel-line {{ height: 18px; border-radius: 99px; background: {accent}; opacity: .28; margin-bottom: 16px; }}
        .panel-line.wide {{ width: 82%; }} .panel-line.short {{ width: 46%; }}
        .panel-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-top: 52px; }}
        .panel-grid span {{ height: 120px; border-radius: 26px; background: rgba(0,0,0,.055); border: 1px solid rgba(0,0,0,.06); }}
        .content-section {{ margin: 30px 0; padding: clamp(28px, 5vw, 52px); background: rgba(255,255,255,.72); border: 1px solid rgba(0,0,0,.08); border-radius: 34px; box-shadow: 0 18px 50px rgba(0,0,0,.08); }}
        .features-grid, .contact-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }}
        .feature-item, .contact-grid div {{ padding: 22px; background: rgba(255,255,255,.72); border: 1px solid rgba(0,0,0,.07); border-radius: 24px; }}
        .feature-item strong, .contact-grid strong {{ display: block; font-size: 18px; margin-bottom: 10px; }}
        .page-heading {{ padding: 48px 0 12px; }}
        @media (max-width: 850px) {{
            .site-header {{ flex-direction: column; align-items: flex-start; }}
            .hero-block, .features-grid, .contact-grid {{ grid-template-columns: 1fr; }}
            .hero-panel {{ min-height: 240px; }}
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
