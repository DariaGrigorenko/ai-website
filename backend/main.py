import os
from datetime import datetime, timedelta
from html import escape
from uuid import uuid4
from typing import Any
import re

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


def is_multipage(site_json: dict[str, Any]) -> bool:
    return "много" in str(site_json.get("siteType") or "").lower()


def safe_hex(value: Any, fallback: str) -> str:
    value = str(value or "").strip()
    return value if re.fullmatch(r"#[0-9a-fA-F]{6}", value) else fallback


def css_color(site_json: dict[str, Any], key: str, fallback: str) -> str:
    design = site_json.get("design", {}) if isinstance(site_json.get("design"), dict) else {}
    return safe_hex(design.get(key), fallback)


def design_value(site_json: dict[str, Any], key: str, allowed: set[str], fallback: str) -> str:
    design = site_json.get("design", {}) if isinstance(site_json.get("design"), dict) else {}
    value = str(design.get(key) or "").strip().lower()
    return value if value in allowed else fallback


def clean_generated_text(value: Any) -> str:
    """Убирает markdown-артефакты, которые Gemini иногда кладёт внутрь JSON-строк."""
    text = str(value or "")
    text = text.replace("**", "").replace("__", "").replace("`", "")
    text = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", text)
    text = re.sub(r"^[ \t]*[-*•][ \t]+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[ \t]*\d+[.)][ \t]+", "", text, flags=re.MULTILINE)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def markdown_items_from_text(value: Any) -> list[dict[str, str]]:
    """Превращает строки вида **Название:** описание в карточки, чтобы на сайте не были видны звёздочки."""
    raw = str(value or "").strip()
    if "**" not in raw:
        return []
    pattern = re.compile(r"\*\*\s*([^*:\n]{2,80})\s*:?\s*\*\*\s*([^*]+?)(?=(?:\n?\s*\*\*\s*[^*:\n]{2,80}\s*:?\s*\*\*)|$)", re.S)
    items: list[dict[str, str]] = []
    for title, description in pattern.findall(raw):
        title = clean_generated_text(title).strip(" :—-")
        description = clean_generated_text(description).strip(" :—-")
        if title and description:
            items.append({"title": title[:90], "description": description[:500]})
    return items


def render_rich_text(value: Any) -> str:
    text = clean_generated_text(value)
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) > 1:
        return "".join(f"<p>{escape(line)}</p>" for line in lines)
    return f"<p>{escape(text)}</p>"


def page_slug(page: dict[str, Any], index: int) -> str:
    raw = str(page.get("slug") or "").strip().strip("/")
    if index == 0 or raw in {"", "home", "glavnaia", "главная"}:
        return ""
    return slugify(raw) or slugify(str(page.get("title") or f"page-{index}")) or f"page-{index}"


def pages_with_slugs(site_json: dict[str, Any]) -> list[tuple[dict[str, Any], str]]:
    pages = site_json.get("pages") if isinstance(site_json.get("pages"), list) else []
    result: list[tuple[dict[str, Any], str]] = []
    used: set[str] = set()
    for index, page in enumerate(pages):
        if not isinstance(page, dict):
            continue
        slug = page_slug(page, index)
        if slug in used and slug:
            base = slug
            counter = 2
            while f"{base}-{counter}" in used:
                counter += 1
            slug = f"{base}-{counter}"
        used.add(slug)
        result.append((page, slug))
    if not result:
        result.append(({"title": "Главная", "slug": "/", "sections": []}, ""))
    return result


def section_anchor(section: dict[str, Any], page_index: int, section_index: int) -> str:
    anchor = str(section.get("anchorId") or "").strip().lstrip("#")
    if anchor:
        return slugify(anchor) or f"section-{page_index}-{section_index}"
    section_type = str(section.get("type") or "section")
    if section_type == "hero" and page_index == 0:
        return "home"
    if section_type == "contact":
        return "contacts"
    return f"section-{page_index}-{section_index}"


def first_page_with_meaning(site_json: dict[str, Any], words: list[str]) -> str | None:
    for page, slug in pages_with_slugs(site_json):
        page_text = " ".join([
            str(page.get("title") or ""),
            str(page.get("slug") or ""),
            str(page.get("type") or ""),
            " ".join(
                str(sec.get("title") or "") + " " + str(sec.get("anchorId") or "")
                for sec in page.get("sections", [])
                if isinstance(sec, dict)
            ),
        ]).lower()
        if any(word in page_text for word in words):
            return slug
    return None


def target_page_for_button(text: str, raw_target: str, site_json: dict[str, Any], used: set[str]) -> str:
    low = f"{text} {raw_target}".lower()
    pages = pages_with_slugs(site_json)
    available = [slug for _, slug in pages if slug]
    cleaned_target = slugify(raw_target.strip().lstrip("#/"))
    if cleaned_target in available and cleaned_target not in used:
        return cleaned_target

    meaning_rules = [
        (["услуг", "сервис", "стоим", "цена", "выбрать"], ["услуг", "services", "каталог", "menu", "меню"]),
        (["работ", "портф", "кейс", "пример"], ["портф", "portfolio", "работ", "case"]),
        (["распис", "дат", "время", "программ"], ["распис", "schedule", "программ", "event"]),
        (["команд", "тренер", "специалист"], ["команд", "team", "тренер", "специалист"]),
        (["о нас", "компан", "подроб", "узнать"], ["о нас", "about", "компан", "истори"]),
        (["контакт", "связ", "заяв", "запис", "консульт"], ["контакт", "contacts", "заяв", "связ"]),
        (["faq", "вопрос"], ["faq", "вопрос"]),
    ]
    for button_words, page_words in meaning_rules:
        if any(word in low for word in button_words):
            slug = first_page_with_meaning(site_json, page_words)
            if slug is not None and slug not in used:
                return slug
    for slug in available:
        if slug not in used:
            return slug
    return available[0] if available else ""


def normalize_button_href(button: dict[str, Any], site_json: dict[str, Any], base_path: str, used: set[str]) -> str:
    contact = site_json.get("contact", {}) if isinstance(site_json.get("contact"), dict) else {}
    phone = re.sub(r"[^0-9+]", "", str(contact.get("phone") or ""))
    email = str(contact.get("email") or "").strip()
    text = str(button.get("text") or "").lower()
    raw_target = str(button.get("target") or "").strip()
    low = f"{text} {raw_target}".lower()

    if raw_target.startswith(("tel:", "mailto:")):
        return "#lead-form"
    if any(w in low for w in ["позвон", "звон", "телефон", "контакт", "связ", "заяв", "запис", "консульт"]):
        return "#lead-form"
    if any(w in low for w in ["почт", "email", "mail"]):
        return "#lead-form"

    if is_multipage(site_json):
        slug = target_page_for_button(text, raw_target, site_json, used)
        used.add(slug)
        return base_path if not slug else f"{base_path}/{slug}"

    target = raw_target if raw_target.startswith("#") and len(raw_target) > 1 else "#contacts"
    return target


def render_buttons(buttons: list[dict[str, Any]], site_json: dict[str, Any], base_path: str) -> str:
    if not buttons:
        buttons = [{"text": "Связаться", "target": "contacts"}]
    html = ""
    used_targets: set[str] = set()
    for index, button in enumerate(buttons):
        if not isinstance(button, dict):
            button = {"text": str(button), "target": ""}
        text = escape(clean_generated_text(button.get("text") or f"Кнопка {index + 1}"))
        href = normalize_button_href(button, site_json, base_path, used_targets)
        class_name = "site-btn" if index == 0 else "site-btn site-btn-outline"
        lead_attr = ' data-lead-open="true"' if href == "#lead-form" else ""
        html += f'<a class="{class_name}" href="{escape(href)}"{lead_attr}>{text}</a>'
    return html


def render_section(section: dict[str, Any], page_index: int, section_index: int, site_json: dict[str, Any], base_path: str) -> str:
    section_type = section.get("type")
    anchor_id = escape(section_anchor(section, page_index, section_index))

    if section_type == "hero":
        title = escape(clean_generated_text(section.get("title") or ""))
        subtitle = escape(clean_generated_text(section.get("subtitle") or ""))
        buttons = section.get("buttons")
        if not isinstance(buttons, list):
            buttons = [{"text": section.get("buttonText", "Подробнее"), "target": "contacts"}]
        return f'''
        <section class="hero-block" id="{anchor_id}">
            <div class="hero-content">
                <h1>{title}</h1>
                <p>{subtitle}</p>
                <div class="button-row">{render_buttons(buttons, site_json, base_path)}</div>
            </div>
        </section>
        '''

    if section_type == "features":
        title = escape(clean_generated_text(section.get("title") or "Преимущества"))
        items = section.get("items") if isinstance(section.get("items"), list) else []
        items_html = ""
        for item in items:
            if isinstance(item, dict):
                item_title = escape(clean_generated_text(item.get("title") or "Пункт"))
                item_description = escape(clean_generated_text(item.get("description") or ""))
                items_html += f'<div class="feature-item"><strong>{item_title}</strong><p>{item_description}</p></div>'
            else:
                items_html += f'<div class="feature-item"><strong>{escape(str(item))}</strong></div>'
        return f'<section class="content-section" id="{anchor_id}"><h2>{title}</h2><div class="features-grid">{items_html}</div></section>'

    if section_type == "contact":
        title = escape(clean_generated_text(section.get("title") or "Контакты"))
        phone = escape(str(section.get("phone") or site_json.get("contact", {}).get("phone", "")))
        email = escape(str(section.get("email") or site_json.get("contact", {}).get("email", "")))
        address = escape(str(section.get("address") or "Адрес будет добавлен позже"))
        return f'''
        <section class="content-section contact-section" id="{anchor_id}">
            <h2>{title}</h2>
            <div class="contact-grid">
                <a href="#lead-form" data-lead-open="true" class="contact-card"><strong>Телефон</strong><p>{phone}</p></a>
                <a href="#lead-form" data-lead-open="true" class="contact-card"><strong>Email</strong><p>{email}</p></a>
                <a href="#lead-form" data-lead-open="true" class="contact-card"><strong>Адрес</strong><p>{address}</p></a>
            </div>
        </section>
        '''

    title = escape(clean_generated_text(section.get("title") or "Раздел"))
    raw_description = section.get("description") or ""
    extracted_items = markdown_items_from_text(raw_description)
    if extracted_items:
        items_html = "".join(
            f'<div class="feature-item"><strong>{escape(item["title"])}</strong><p>{escape(item["description"])}</p></div>'
            for item in extracted_items
        )
        return f'<section class="content-section" id="{anchor_id}"><h2>{title}</h2><div class="features-grid">{items_html}</div></section>'
    description_html = render_rich_text(raw_description)
    return f'<section class="content-section card-section" id="{anchor_id}"><h2>{title}</h2>{description_html}</section>'


def ensure_contact_section(site_json: dict[str, Any]) -> str:
    contact = site_json.get("contact", {}) if isinstance(site_json.get("contact"), dict) else {}
    phone = escape(str(contact.get("phone") or "+7 900 123-45-67"))
    email = escape(str(contact.get("email") or "hello@example.ru"))
    return f'''
    <section class="content-section contact-section" id="contacts">
        <h2>Контакты</h2>
        <div class="contact-grid">
            <a href="#lead-form" data-lead-open="true" class="contact-card"><strong>Телефон</strong><p>{phone}</p></a>
            <a href="#lead-form" data-lead-open="true" class="contact-card"><strong>Email</strong><p>{email}</p></a>
            <a href="#lead-form" data-lead-open="true" class="contact-card"><strong>Заявка</strong><p>Оставьте номер, чтобы с вами связались.</p></a>
        </div>
    </section>
    '''


def render_site_html(site_json: dict[str, Any], public_slug: str, current_page_slug: str = "") -> str:
    site_name = escape(str(site_json.get("siteName") or "Сайт"))
    pages = pages_with_slugs(site_json)
    multipage = is_multipage(site_json)
    base_path = f"/s/{public_slug}"

    primary = css_color(site_json, "primaryColor", "#151515")
    secondary = css_color(site_json, "secondaryColor", "#25221e")
    accent = css_color(site_json, "accentColor", "#d58b35")
    text = css_color(site_json, "textColor", "#f7f0e6")
    surface = css_color(site_json, "surfaceColor", "#1f1d1a")

    layout_variant = design_value(site_json, "layoutVariant", {"split", "centered", "editorial", "grid", "brutal", "calm"}, "split")
    card_style = design_value(site_json, "cardStyle", {"solid", "outline", "glass", "minimal", "raised"}, "solid")
    hero_visual = design_value(site_json, "heroVisual", {"panels", "badges", "stats", "lines", "none"}, "panels")
    section_shape = design_value(site_json, "sectionShape", {"rounded", "sharp", "pill", "asymmetric"}, "rounded")
    font_family_key = design_value(site_json, "fontFamily", {"serif", "sans", "mono", "display"}, "sans")
    density = design_value(site_json, "density", {"air", "normal", "compact"}, "normal")
    font_family = {
        "serif": "Georgia, 'Times New Roman', serif",
        "sans": "Inter, Arial, sans-serif",
        "mono": "'JetBrains Mono', Consolas, monospace",
        "display": "'Trebuchet MS', Arial, sans-serif",
    }.get(font_family_key, "Inter, Arial, sans-serif")
    body_classes = f"layout-{layout_variant} card-{card_style} hero-{hero_visual} shape-{section_shape} density-{density}"

    if multipage:
        selected = next(((page, slug, i) for i, (page, slug) in enumerate(pages) if slug == current_page_slug), None)
        if selected is None:
            raise HTTPException(status_code=404, detail="Страница не найдена")
        current_page, _, current_index = selected
        menu_html = ""
        for page, slug in pages:
            href = base_path if not slug else f"{base_path}/{slug}"
            active = "active" if slug == current_page_slug else ""
            menu_html += f'<a class="{active}" href="{href}">{escape(clean_generated_text(page.get("title") or "Страница"))}</a>'
        content_pages = [(current_page, current_index)]
        brand_href = base_path
    else:
        first_page = pages[0][0]
        menu_html = ""
        for i, section in enumerate(first_page.get("sections", [])):
            if isinstance(section, dict) and section.get("type") != "hero":
                title = escape(clean_generated_text(section.get("title") or section.get("type") or "Раздел"))
                anchor = escape(section_anchor(section, 0, i))
                menu_html += f'<a href="#{anchor}">{title}</a>'
        content_pages = [(first_page, 0)]
        brand_href = "#home"

    content_html = ""
    has_contacts = False
    for page, page_index in content_pages:
        page_title = escape(clean_generated_text(page.get("title") or "Страница"))
        content_html += '<main class="page-wrapper">'
        if multipage and page_index > 0:
            content_html += f'<section class="page-heading"><p class="hero-kicker">{site_name}</p><h1>{page_title}</h1></section>'
        for section_index, section in enumerate(page.get("sections", [])):
            if isinstance(section, dict):
                if section.get("type") == "contact":
                    has_contacts = True
                content_html += render_section(section, page_index, section_index, site_json, base_path)
        if not multipage and not has_contacts:
            content_html += ensure_contact_section(site_json)
        content_html += '</main>'

    return f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{site_name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        :root {{ --radius: 28px; --section-pad: clamp(34px, 5vw, 72px); --gap: 20px; --shadow: 0 26px 90px color-mix(in srgb, {primary} 72%, transparent); }}
        html {{ scroll-behavior: smooth; }}
        body {{ font-family: {font_family}; background: radial-gradient(circle at 16% 12%, color-mix(in srgb, {accent} 30%, transparent), transparent 26%), radial-gradient(circle at 82% 8%, color-mix(in srgb, {surface} 42%, transparent), transparent 30%), linear-gradient(135deg, {primary} 0%, {secondary} 100%); color: {text}; min-height: 100vh; overflow-x: hidden; }}
        body::before {{ content: ""; position: fixed; inset: 0; pointer-events: none; background: linear-gradient(90deg, color-mix(in srgb, {text} 5%, transparent) 1px, transparent 1px), linear-gradient(color-mix(in srgb, {text} 5%, transparent) 1px, transparent 1px); background-size: 56px 56px; mask-image: linear-gradient(to bottom, black, transparent 70%); }}
        body.shape-sharp {{ --radius: 4px; }} body.shape-pill {{ --radius: 42px; }} body.shape-asymmetric {{ --radius: 38px 8px 38px 8px; }}
        body.density-air {{ --section-pad: clamp(46px, 7vw, 92px); --gap: 26px; }} body.density-compact {{ --section-pad: clamp(24px, 4vw, 46px); --gap: 14px; }}
        .site-header {{ position: sticky; top: 14px; z-index: 20; width: min(1160px, 92%); margin: 18px auto 0; padding: 16px 18px; background: color-mix(in srgb, {surface} 78%, transparent); border: 1px solid color-mix(in srgb, {accent} 32%, transparent); border-radius: var(--radius); display: flex; justify-content: space-between; align-items: center; gap: 20px; backdrop-filter: blur(18px); box-shadow: var(--shadow); }}
        .brand {{ color: {text}; text-decoration: none; font-size: 25px; font-weight: 950; letter-spacing: -.03em; }}
        nav {{ display: flex; gap: 10px; flex-wrap: wrap; }}
        nav a {{ color: {text}; text-decoration: none; opacity: .82; padding: 10px 14px; border-radius: 999px; border: 1px solid color-mix(in srgb, {text} 12%, transparent); background: color-mix(in srgb, {surface} 64%, transparent); transition: .22s ease; }}
        nav a:hover, nav a.active {{ opacity: 1; border-color: {accent}; color: {accent}; transform: translateY(-2px); }}
        .page-wrapper {{ width: min(1160px, 90%); margin: 0 auto; padding: 64px 0; }}
        .hero-block {{ min-height: 500px; display: grid; grid-template-columns: minmax(0, 1fr); gap: clamp(24px, 5vw, 56px); align-items: center; position: relative; }}
        .hero-block::after {{ content: ""; position: absolute; right: 0; bottom: 40px; width: min(42vw, 420px); height: min(42vw, 420px); border-radius: 50%; background: radial-gradient(circle, color-mix(in srgb, {accent} 28%, transparent), transparent 62%); filter: blur(10px); opacity: .7; z-index: -1; }}
        .hero-kicker {{ color: {accent}; font-size: 13px; text-transform: uppercase; letter-spacing: .2em; margin-bottom: 16px; font-weight: 900; }}
        h1 {{ font-size: clamp(46px, 7.5vw, 96px); line-height: .92; margin-bottom: 26px; font-weight: 950; letter-spacing: -.06em; max-width: 1000px; }}
        h2 {{ font-size: clamp(32px, 4.8vw, 58px); line-height: .96; margin-bottom: 22px; letter-spacing: -.045em; }}
        p {{ font-size: 18px; line-height: 1.75; opacity: .88; max-width: 840px; }}
        .button-row {{ display: flex; gap: 14px; flex-wrap: wrap; margin-top: 30px; }}
        .site-btn {{ display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 15px 22px; background: linear-gradient(135deg, {accent}, color-mix(in srgb, {accent} 74%, {text} 26%)); color: {primary}; text-decoration: none; font-weight: 950; border-radius: 999px; border: 1px solid color-mix(in srgb, {accent} 78%, {text} 22%); box-shadow: 0 14px 34px color-mix(in srgb, {accent} 32%, transparent); transition: transform .22s ease, box-shadow .22s ease; cursor: pointer; }}
        .site-btn:hover {{ transform: translateY(-3px); box-shadow: 0 20px 44px color-mix(in srgb, {accent} 42%, transparent); }}
        .site-btn-outline {{ background: color-mix(in srgb, {surface} 42%, transparent); color: {accent}; border-color: color-mix(in srgb, {accent} 48%, transparent); box-shadow: none; }}
        .content-section {{ margin: 30px 0; padding: var(--section-pad); background: linear-gradient(145deg, color-mix(in srgb, {surface} 88%, transparent), color-mix(in srgb, {surface} 60%, {accent} 8%)); border: 1px solid color-mix(in srgb, {accent} 28%, transparent); border-radius: var(--radius); box-shadow: var(--shadow); position: relative; overflow: hidden; }}
        .content-section::before {{ content: ""; position: absolute; inset: 0; background: radial-gradient(circle at top right, color-mix(in srgb, {accent} 12%, transparent), transparent 35%); pointer-events: none; }}
        .content-section > * {{ position: relative; }}
        .features-grid, .contact-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--gap); }}
        .feature-item, .contact-card {{ display: block; color: {text}; text-decoration: none; padding: 26px; background: color-mix(in srgb, {surface} 66%, {accent} 10%); border: 1px solid color-mix(in srgb, {accent} 24%, transparent); border-radius: calc(var(--radius) * .72); transition: transform .22s ease, border-color .22s ease, background .22s ease; min-height: 150px; }}
        .feature-item:hover, .contact-card:hover {{ transform: translateY(-4px); border-color: {accent}; background: color-mix(in srgb, {surface} 58%, {accent} 16%); }}
        .feature-item strong, .contact-card strong {{ display: block; font-size: 19px; margin-bottom: 10px; color: {accent}; letter-spacing: -.02em; }}
        .page-heading {{ padding: 34px 0 10px; }}
        .lead-modal {{ position: fixed; inset: 0; display: none; place-items: center; padding: 24px; background: rgba(0,0,0,.58); backdrop-filter: blur(8px); z-index: 100; }}
        .lead-modal.is-open {{ display: grid; }}
        .lead-box {{ width: min(460px, 100%); background: color-mix(in srgb, {surface} 92%, {primary} 8%); color: {text}; border: 1px solid color-mix(in srgb, {accent} 38%, transparent); border-radius: 28px; padding: 28px; box-shadow: 0 34px 120px rgba(0,0,0,.42); }}
        .lead-box h3 {{ font-size: 28px; margin-bottom: 10px; }}
        .lead-box p {{ font-size: 15px; margin-bottom: 18px; }}
        .lead-input {{ width: 100%; padding: 15px 16px; border-radius: 16px; border: 1px solid color-mix(in srgb, {accent} 35%, transparent); background: color-mix(in srgb, {primary} 30%, white 8%); color: {text}; outline: none; margin-bottom: 12px; }}
        .lead-actions {{ display: flex; gap: 10px; flex-wrap: wrap; }}
        .lead-close {{ background: transparent; color: {text}; border: 1px solid color-mix(in srgb, {text} 18%, transparent); }}
        .lead-note {{ display: none; margin-top: 12px; color: {accent}; font-weight: 800; }}
        .lead-note.is-visible {{ display: block; }}

        body.layout-centered .hero-block {{ grid-template-columns: 1fr; text-align: center; max-width: 940px; margin-inline: auto; }}
        body.layout-centered .button-row {{ justify-content: center; }}
        body.layout-editorial .site-header {{ border-left: 0; border-right: 0; border-radius: 0; }}
        body.layout-editorial .hero-block {{ grid-template-columns: .85fr 1.15fr; }}
        body.layout-editorial .content-section {{ background: transparent; border-width: 0 0 1px 0; border-radius: 0; padding-left: 0; padding-right: 0; box-shadow: none; }}
        body.layout-grid {{ background-image: linear-gradient(color-mix(in srgb, {accent} 12%, transparent) 1px, transparent 1px), linear-gradient(90deg, color-mix(in srgb, {accent} 12%, transparent) 1px, transparent 1px), linear-gradient(135deg, {primary}, {secondary}); background-size: 42px 42px, 42px 42px, auto; }}
        body.layout-brutal .site-header, body.layout-brutal .content-section, body.layout-brutal .feature-item, body.layout-brutal .contact-card, body.layout-brutal .site-btn {{ box-shadow: 7px 7px 0 {accent}; border: 2px solid {text}; text-transform: uppercase; }}
        body.layout-brutal h1, body.layout-brutal h2 {{ letter-spacing: -.06em; }}
        body.layout-calm .hero-block {{ gap: 70px; }}

        body.card-outline .content-section, body.card-outline .feature-item, body.card-outline .contact-card {{ background: transparent; border: 1.5px solid {accent}; }}
        body.card-glass .content-section, body.card-glass .feature-item, body.card-glass .contact-card {{ background: color-mix(in srgb, {surface} 55%, transparent); backdrop-filter: blur(20px); }}
        body.card-minimal .content-section, body.card-minimal .feature-item, body.card-minimal .contact-card {{ background: transparent; border-color: color-mix(in srgb, {text} 18%, transparent); box-shadow: none; }}
        body.card-raised .feature-item, body.card-raised .contact-card, body.card-raised .content-section {{ box-shadow: 0 22px 70px color-mix(in srgb, {primary} 78%, transparent); }}

        @media (max-width: 850px) {{ .site-header {{ flex-direction: column; align-items: flex-start; }} .hero-block, .features-grid, .contact-grid {{ grid-template-columns: 1fr; }} h1 {{ font-size: clamp(38px, 13vw, 62px); }} }}
    </style>
</head>
<body class="{body_classes}">
    <header class="site-header"><a class="brand" href="{escape(brand_href)}">{site_name}</a><nav>{menu_html}</nav></header>
    {content_html}
    <div class="lead-modal" id="lead-form" aria-hidden="true">
        <div class="lead-box">
            <h3>Оставить заявку</h3>
            <p>Введите номер телефона. В этой MVP-версии форма показывает будущую функцию отправки заявки.</p>
            <input class="lead-input" type="tel" placeholder="+7 900 000-00-00">
            <div class="lead-actions">
                <button class="site-btn" type="button" data-lead-submit>Отправить</button>
                <button class="site-btn site-btn-outline lead-close" type="button" data-lead-close>Закрыть</button>
            </div>
            <div class="lead-note" data-lead-note>Заявка подготовлена. В будущей версии она будет отправляться владельцу сайта.</div>
        </div>
    </div>
    <script>
        const leadModal = document.getElementById('lead-form');
        const leadNote = document.querySelector('[data-lead-note]');
        document.querySelectorAll('[data-lead-open="true"]').forEach((item) => {{
            item.addEventListener('click', (event) => {{
                event.preventDefault();
                leadModal.classList.add('is-open');
                leadModal.setAttribute('aria-hidden', 'false');
                if (leadNote) leadNote.classList.remove('is-visible');
            }});
        }});
        document.querySelectorAll('[data-lead-close]').forEach((item) => {{
            item.addEventListener('click', () => {{
                leadModal.classList.remove('is-open');
                leadModal.setAttribute('aria-hidden', 'true');
            }});
        }});
        document.querySelectorAll('[data-lead-submit]').forEach((item) => {{
            item.addEventListener('click', () => {{
                if (leadNote) leadNote.classList.add('is-visible');
            }});
        }});
        leadModal.addEventListener('click', (event) => {{
            if (event.target === leadModal) {{
                leadModal.classList.remove('is-open');
                leadModal.setAttribute('aria-hidden', 'true');
            }}
        }});
    </script>
</body>
</html>'''


@app.get("/")
def health_check():
    return {"status": "ok", "service": "HGGps Backend API", "aiProvider": os.getenv("AI_PROVIDER", "deepseek"), "message": "Backend работает"}


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
    host = request.headers.get("host") or request.url.netloc
    forwarded_proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "https").split(",")[0].strip()
    if host and not host.startswith(("localhost", "127.0.0.1")):
        forwarded_proto = "https"
    base_url = f"{forwarded_proto}://{host}".rstrip("/")
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
    return {"siteJson": project["siteJson"], "generatedBy": project.get("generatedBy"), "aiModel": project.get("aiModel"), "aiError": project.get("aiError"), "expiresAt": project["expiresAt"]}


@app.get("/s/{slug}", response_class=HTMLResponse)
def open_public_site(slug: str):
    project = find_project_by_slug(slug)
    if not project:
        raise HTTPException(status_code=404, detail="Сайт не найден")
    expires_at = datetime.fromisoformat(project["expiresAt"])
    if datetime.now() > expires_at:
        return HTMLResponse(content="<h1>Срок действия временной ссылки истёк</h1>", status_code=410)
    return HTMLResponse(content=render_site_html(project["siteJson"], slug, ""))


@app.get("/s/{slug}/{page_slug}", response_class=HTMLResponse)
def open_public_site_page(slug: str, page_slug: str):
    project = find_project_by_slug(slug)
    if not project:
        raise HTTPException(status_code=404, detail="Сайт не найден")
    expires_at = datetime.fromisoformat(project["expiresAt"])
    if datetime.now() > expires_at:
        return HTMLResponse(content="<h1>Срок действия временной ссылки истёк</h1>", status_code=410)
    if not is_multipage(project["siteJson"]):
        return HTMLResponse(content=render_site_html(project["siteJson"], slug, ""))
    return HTMLResponse(content=render_site_html(project["siteJson"], slug, page_slug))
