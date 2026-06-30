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
    value = str(design.get(key, fallback)).strip()
    if value.startswith("#") and len(value) == 7:
        return value
    return fallback


def is_multipage(site_json: dict[str, Any]) -> bool:
    return "много" in str(site_json.get("siteType") or "").lower()


def page_slug_value(page: dict[str, Any], index: int) -> str:
    raw = str(page.get("slug") or "").strip()
    if index == 0 or raw in {"", "/", "home", "/home"}:
        return ""
    raw = raw.strip("/")
    return slugify(raw) or slugify(str(page.get("title") or f"page-{index}")) or f"page-{index}"


def page_url(public_slug: str, page_slug: str = "", anchor: str = "") -> str:
    base = f"/s/{public_slug}"
    if page_slug:
        base += f"/{page_slug}"
    if anchor:
        base += f"#{anchor.lstrip('#')}"
    return base


def pages_list(site_json: dict[str, Any]) -> list[dict[str, Any]]:
    pages = site_json.get("pages")
    return pages if isinstance(pages, list) else []


def find_page(site_json: dict[str, Any], current_page_slug: str = "") -> tuple[dict[str, Any], int]:
    pages = pages_list(site_json)
    if not pages:
        return {"title": "Сайт", "slug": "/", "sections": []}, 0

    current = current_page_slug.strip("/")
    for index, page in enumerate(pages):
        if page_slug_value(page, index) == current:
            return page, index
    raise HTTPException(status_code=404, detail="Страница сайта не найдена")


def collect_sections(site_json: dict[str, Any]) -> list[tuple[int, int, dict[str, Any], str]]:
    result: list[tuple[int, int, dict[str, Any], str]] = []
    for page_index, page in enumerate(pages_list(site_json)):
        for section_index, section in enumerate(page.get("sections", [])):
            if isinstance(section, dict):
                result.append((page_index, section_index, section, section_anchor(section, page_index, section_index)))
    return result


def find_target_for_anchor(site_json: dict[str, Any], anchor: str) -> tuple[str, str] | None:
    anchor = anchor.strip().lstrip("#")
    for page_index, _, _, sec_anchor in collect_sections(site_json):
        if sec_anchor == anchor:
            page = pages_list(site_json)[page_index]
            return page_slug_value(page, page_index), anchor
    return None


def normalize_button_target(raw_target: Any, site_json: dict[str, Any], public_slug: str, current_page_slug: str) -> str:
    contact = site_json.get("contact", {}) if isinstance(site_json.get("contact"), dict) else {}
    phone = str(contact.get("phone") or "").strip()
    email = str(contact.get("email") or "").strip()
    value = str(raw_target or "").strip()
    low = value.lower()
    multipage = is_multipage(site_json)

    if low.startswith(("tel:", "mailto:")):
        return value

    if "тел" in low or "звон" in low or "phone" in low or "call" in low:
        return f"tel:{phone}" if phone else page_url(public_slug, current_page_slug, "contacts")

    if "mail" in low or "поч" in low or "email" in low:
        return f"mailto:{email}" if email else page_url(public_slug, current_page_slug, "contacts")

    if value.startswith("/") and multipage:
        page = value.strip("/")
        return page_url(public_slug, "" if page in {"", "home"} else page)

    if value.startswith("#"):
        anchor = value[1:].strip()
        target = find_target_for_anchor(site_json, anchor)
        if target and multipage:
            return page_url(public_slug, target[0], target[1])
        if target:
            return f"#{target[1]}"
        return page_url(public_slug, current_page_slug, "contacts") if multipage else "#contacts"

    return page_url(public_slug, current_page_slug, "contacts") if multipage else "#contacts"


def page_targets(site_json: dict[str, Any], public_slug: str, current_page_slug: str) -> list[str]:
    if is_multipage(site_json):
        urls: list[str] = []
        for index, page in enumerate(pages_list(site_json)):
            ps = page_slug_value(page, index)
            if ps != current_page_slug:
                urls.append(page_url(public_slug, ps))
        urls.append(page_url(public_slug, current_page_slug, "contacts"))
        return urls

    anchors = []
    for _, _, _, anchor in collect_sections(site_json):
        if anchor != "home":
            anchors.append(f"#{anchor}")
    return anchors or ["#contacts"]


def render_buttons(buttons: list[dict[str, Any]], site_json: dict[str, Any], public_slug: str, current_page_slug: str) -> str:
    html = ""
    if not buttons:
        buttons = [{"text": "Связаться", "target": "#contacts"}]

    fallback_targets = page_targets(site_json, public_slug, current_page_slug)
    used_targets: set[str] = set()

    for index, button in enumerate(buttons):
        text = escape(str(button.get("text") or f"Кнопка {index + 1}"))
        target = normalize_button_target(button.get("target"), site_json, public_slug, current_page_slug)

        if target in used_targets and fallback_targets:
            for candidate in fallback_targets:
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
        return slugify(anchor) or anchor
    section_type = str(section.get("type") or "section")
    if section_type == "hero" and page_index == 0:
        return "home"
    if section_type == "contact":
        return "contacts"
    return f"section-{page_index}-{section_index}"


def clean_text(value: Any, fallback: str = "") -> str:
    text = str(value or fallback).strip()
    banned = [
        "индивидуальный подход",
        "качественный сервис",
        "широкий спектр услуг",
        "лучшие решения",
        "мы ценим каждого клиента",
    ]
    for phrase in banned:
        if text.lower() == phrase:
            return fallback or "Информация будет уточнена по запросу."
    return text


def render_section(section: dict[str, Any], page_index: int, section_index: int, site_json: dict[str, Any], public_slug: str, current_page_slug: str) -> str:
    section_type = section.get("type")
    anchor_id = escape(section_anchor(section, page_index, section_index))

    if section_type == "hero":
        title = escape(clean_text(section.get("title"), str(site_json.get("siteName") or "")))
        subtitle = escape(clean_text(section.get("subtitle"), "Краткое описание проекта и основного предложения."))
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
                <div class="button-row">{render_buttons(buttons, site_json, public_slug, current_page_slug)}</div>
            </div>
            <div class="hero-panel">
                <div class="panel-card main-card"></div>
                <div class="panel-card small-card"></div>
                <div class="panel-card wide-card"></div>
            </div>
        </section>
        """

    if section_type == "features":
        title = escape(clean_text(section.get("title"), "Преимущества"))
        items = section.get("items")
        if not isinstance(items, list):
            items = []
        items_html = ""
        for item in items[:6]:
            if isinstance(item, dict):
                item_title = escape(clean_text(item.get("title"), "Пункт"))
                item_description = escape(clean_text(item.get("description"), "Описание пункта."))
                items_html += f'<div class="feature-item"><strong>{item_title}</strong><p>{item_description}</p></div>'
            else:
                items_html += f'<div class="feature-item"><strong>{escape(clean_text(item, "Пункт"))}</strong></div>'
        return f"""
        <section class="content-section" id="{anchor_id}">
            <h2>{title}</h2>
            <div class="features-grid">{items_html}</div>
        </section>
        """

    if section_type == "contact":
        title = escape(clean_text(section.get("title"), "Контакты"))
        phone = escape(str(section.get("phone") or site_json.get("contact", {}).get("phone") or ""))
        email = escape(str(section.get("email") or site_json.get("contact", {}).get("email") or ""))
        address = escape(clean_text(section.get("address"), "Адрес будет добавлен позже"))
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

    title = escape(clean_text(section.get("title"), "Раздел"))
    description = escape(clean_text(section.get("description"), "Информация по разделу."))
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
            <div><strong>Заявка</strong><p>Свяжитесь удобным способом, чтобы уточнить детали.</p></div>
        </div>
    </section>
    """


def build_menu(site_json: dict[str, Any], public_slug: str, current_page_slug: str) -> str:
    items = []
    if is_multipage(site_json):
        for index, page in enumerate(pages_list(site_json)):
            ps = page_slug_value(page, index)
            title = escape(str(page.get("title") or "Страница"))
            active = " active" if ps == current_page_slug else ""
            items.append(f'<a class="{active.strip()}" href="{page_url(public_slug, ps)}">{title}</a>')
    else:
        for _, _, section, anchor in collect_sections(site_json):
            section_type = section.get("type")
            if section_type == "hero":
                title = "Главная"
            else:
                title = str(section.get("title") or anchor).strip()[:24]
            if anchor not in {""}:
                items.append(f'<a href="#{escape(anchor)}">{escape(title)}</a>')
    return "".join(items)


def render_site_html(site_json: dict[str, Any], public_slug: str, current_page_slug: str = "") -> str:
    site_name = escape(str(site_json.get("siteName") or "Сайт"))
    pages = pages_list(site_json)

    primary = css_color(site_json, "primaryColor", "#171321")
    secondary = css_color(site_json, "secondaryColor", "#2c1d3a")
    accent = css_color(site_json, "accentColor", "#f59e0b")
    text = css_color(site_json, "textColor", "#fff7ed")
    surface = css_color(site_json, "surfaceColor", "#241b2f")

    page, page_index = find_page(site_json, current_page_slug) if is_multipage(site_json) else (pages[0] if pages else {"sections": []}, 0)
    sections = page.get("sections", []) if isinstance(page.get("sections"), list) else []
    content_html = '<main class="page-wrapper">'

    if is_multipage(site_json) and page_index > 0:
        content_html += f'<section class="page-heading"><p class="hero-kicker">{escape(str(site_json.get("siteName") or ""))}</p><h1>{escape(str(page.get("title") or "Страница"))}</h1></section>'

    has_contacts = False
    for section_index, section in enumerate(sections):
        if isinstance(section, dict):
            if section.get("type") == "contact":
                has_contacts = True
            content_html += render_section(section, page_index, section_index, site_json, public_slug, current_page_slug)

    if not has_contacts and (not is_multipage(site_json) or current_page_slug in {"", "contacts"}):
        content_html += ensure_contact_section(site_json)

    content_html += '</main>'
    menu_html = build_menu(site_json, public_slug, current_page_slug)
    home_href = page_url(public_slug, "") if is_multipage(site_json) else "#home"

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
            font-family: Manrope, Inter, Arial, sans-serif;
            background: linear-gradient(135deg, {primary} 0%, {secondary} 58%, {surface} 100%);
            color: {text};
            min-height: 100vh;
        }}
        .site-header {{
            position: sticky; top: 0; z-index: 20;
            width: min(1160px, 92%);
            margin: 18px auto 0;
            padding: 16px 18px;
            background: color-mix(in srgb, {surface} 88%, transparent);
            backdrop-filter: blur(18px);
            border: 1px solid rgba(255,255,255,0.16);
            border-radius: 28px;
            display: flex; justify-content: space-between; align-items: center; gap: 18px;
            box-shadow: 0 20px 60px rgba(0,0,0,.18);
        }}
        .brand {{ color: {text}; font-size: 22px; font-weight: 950; text-decoration: none; letter-spacing: -0.04em; }}
        nav {{ display: flex; gap: 8px; flex-wrap: wrap; }}
        nav a {{ color: {text}; text-decoration: none; font-size: 14px; padding: 10px 13px; border-radius: 999px; background: rgba(255,255,255,.10); border: 1px solid rgba(255,255,255,.10); }}
        nav a:hover, nav a.active {{ background: {accent}; color: #fff; }}
        .page-wrapper {{ width: min(1160px, 90%); margin: 0 auto; padding: 54px 0; }}
        .hero-block {{ min-height: 540px; display: grid; grid-template-columns: 1.1fr .9fr; gap: 34px; align-items: center; }}
        .hero-kicker {{ color: {accent}; font-size: 13px; font-weight: 950; text-transform: uppercase; letter-spacing: .13em; margin-bottom: 16px; }}
        h1 {{ font-size: clamp(40px, 7vw, 86px); line-height: .95; margin-bottom: 22px; letter-spacing: -0.07em; font-weight: 950; }}
        h2 {{ font-size: clamp(28px, 4.6vw, 54px); line-height: 1; margin-bottom: 22px; letter-spacing: -0.05em; }}
        p {{ font-size: 18px; line-height: 1.75; opacity: .86; }}
        .button-row {{ display: flex; gap: 12px; flex-wrap: wrap; margin-top: 28px; }}
        .site-btn {{ display: inline-block; padding: 15px 21px; border-radius: 999px; background: {accent}; color: #fff; text-decoration: none; font-weight: 950; box-shadow: 0 14px 34px rgba(0,0,0,.18); }}
        .site-btn-outline {{ background: rgba(255,255,255,.08); border: 1px solid {accent}; color: {text}; box-shadow: none; }}
        .hero-panel {{ min-height: 370px; border-radius: 42px; background: rgba(255,255,255,.10); border: 1px solid rgba(255,255,255,.18); padding: 28px; position: relative; overflow: hidden; }}
        .panel-card {{ position: absolute; border-radius: 32px; background: {accent}; opacity: .26; }}
        .main-card {{ width: 72%; height: 54%; top: 34px; left: 28px; }}
        .small-card {{ width: 34%; height: 28%; right: 26px; top: 66px; opacity: .46; }}
        .wide-card {{ width: 76%; height: 24%; left: 54px; bottom: 38px; opacity: .18; }}
        .content-section {{ margin: 30px 0; padding: clamp(28px, 5vw, 54px); background: color-mix(in srgb, {surface} 88%, white 12%); border: 1px solid rgba(255,255,255,.14); border-radius: 38px; box-shadow: 0 22px 58px rgba(0,0,0,.16); }}
        .features-grid, .contact-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }}
        .feature-item, .contact-grid div {{ padding: 24px; background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.12); border-radius: 26px; }}
        .feature-item strong, .contact-grid strong {{ display: block; font-size: 19px; margin-bottom: 10px; }}
        .page-heading {{ padding: 42px 0 8px; }}
        @media (max-width: 850px) {{
            .site-header {{ flex-direction: column; align-items: flex-start; }}
            .hero-block, .features-grid, .contact-grid {{ grid-template-columns: 1fr; }}
            .hero-panel {{ min-height: 220px; }}
        }}
    </style>
</head>
<body>
    <header class="site-header">
        <a class="brand" href="{escape(home_href)}">{site_name}</a>
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


@app.get("/s/{slug}/{page_slug}", response_class=HTMLResponse)
def open_public_site_page(slug: str, page_slug: str):
    project = find_project_by_slug(slug)
    if not project:
        raise HTTPException(status_code=404, detail="Сайт не найден")

    expires_at = datetime.fromisoformat(project["expiresAt"])
    if datetime.now() > expires_at:
        return HTMLResponse(content="<h1>Срок действия временной ссылки истёк</h1>", status_code=410)

    html = render_site_html(project["siteJson"], public_slug=slug, current_page_slug=page_slug)
    return HTMLResponse(content=html)


@app.get("/s/{slug}", response_class=HTMLResponse)
def open_public_site(slug: str):
    project = find_project_by_slug(slug)
    if not project:
        raise HTTPException(status_code=404, detail="Сайт не найден")

    expires_at = datetime.fromisoformat(project["expiresAt"])
    if datetime.now() > expires_at:
        return HTMLResponse(content="<h1>Срок действия временной ссылки истёк</h1>", status_code=410)

    html = render_site_html(project["siteJson"], public_slug=slug, current_page_slug="")
    return HTMLResponse(content=html)
