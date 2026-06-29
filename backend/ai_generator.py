import json
import os
import random
import re
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

DEFAULT_PHONE_POOL = [
    "+7 900 123-45-67",
    "+7 901 234-56-78",
    "+7 902 345-67-89",
    "+7 903 456-78-90",
]
DEFAULT_EMAIL_POOL = [
    "hello@example.ru",
    "info@example.ru",
    "contact@example.ru",
    "request@example.ru",
]

ANCHOR_BY_MEANING = {
    "features": ["преим", "почему", "выг", "довер"],
    "services": ["услуг", "сервис", "направ", "что делаем"],
    "about": ["о нас", "о проект", "компан", "истори", "кто мы"],
    "portfolio": ["портф", "работ", "кей", "пример"],
    "schedule": ["распис", "программ", "дат", "время"],
    "contacts": ["контакт", "заяв", "связ", "запис", "консультац"],
    "team": ["команд", "тренер", "специалист"],
    "faq": ["faq", "вопрос"],
    "catalog": ["каталог", "меню", "товар"],
}


def normalize_phone(phone: str | None) -> str:
    phone = (phone or "").strip()
    return phone if phone else random.choice(DEFAULT_PHONE_POOL)


def normalize_email(email: str | None) -> str:
    email = (email or "").strip()
    if email and "@" in email:
        return email
    return random.choice(DEFAULT_EMAIL_POOL)


def clamp_button_count(value: int | str | None) -> int:
    try:
        count = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 1
    return max(1, min(count, 5))


def generate_site(
    description: str,
    site_type: str,
    goal: str,
    company_name: str = "",
    design_preferences: str = "",
    desired_info: str = "",
    contact_email: str | None = None,
    contact_phone: str | None = None,
    button_count: int = 1,
    previous_site_json: dict[str, Any] | None = None,
    regeneration_note: str = "",
) -> dict[str, Any]:
    phone = normalize_phone(contact_phone)
    email = normalize_email(contact_email)
    buttons = clamp_button_count(button_count)

    try:
        site_json = generate_site_with_gemini(
            description=description,
            site_type=site_type,
            goal=goal,
            company_name=company_name,
            design_preferences=design_preferences,
            desired_info=desired_info,
            contact_email=email,
            contact_phone=phone,
            button_count=buttons,
            previous_site_json=previous_site_json,
            regeneration_note=regeneration_note,
        )
        site_json["_generatedBy"] = "gemini"
        site_json["_aiModel"] = GEMINI_MODEL
    except Exception as error:
        print("Gemini generation failed. Mock generation used:", repr(error))
        site_json = generate_mock_site(
            description=description,
            site_type=site_type,
            goal=goal,
            company_name=company_name,
            design_preferences=design_preferences,
            desired_info=desired_info,
            contact_email=email,
            contact_phone=phone,
            button_count=buttons,
        )
        site_json["_generatedBy"] = "mock"
        site_json["_aiError"] = str(error)

    site_json["contact"] = {"phone": phone, "email": email}
    site_json["requestedButtonCount"] = buttons
    validate_site_json(site_json)
    return site_json


def generate_site_with_gemini(
    description: str,
    site_type: str,
    goal: str,
    company_name: str,
    design_preferences: str,
    desired_info: str,
    contact_email: str,
    contact_phone: str,
    button_count: int,
    previous_site_json: dict[str, Any] | None,
    regeneration_note: str,
) -> dict[str, Any]:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing")

    client = genai.Client(api_key=GEMINI_API_KEY)

    previous_block = ""
    if previous_site_json:
        previous_block = f"""
Предыдущий вариант сайта, который пользователю не понравился:
{json.dumps(previous_site_json, ensure_ascii=False)[:12000]}

Комментарий пользователя к перегенерации. Это обязательное требование, его нужно выполнить в первую очередь:
{regeneration_note or "Сделай другой вариант: измени структуру, стиль, тексты, цвета и расположение блоков."}

Важно: при перегенерации нельзя просто повторять предыдущий сайт. Нужно заметно изменить цветовую палитру, композицию, акценты, тексты и порядок смысловых блоков с учётом комментария пользователя.
"""

    prompt = f"""
Ты — ИИ-конструктор сайтов HGGps. Твоя задача — полностью самостоятельно проанализировать запрос пользователя и сгенерировать сайт.

Основные требования:
- поддерживаются только два типа сайта: "Лендинг" и "Многостраничный сайт";
- лендинг — одна страница;
- многостраничный сайт — от 2 до 5 страниц;
- ИИ сам выбирает стиль, фон, цветовую схему, расположение блоков, названия блоков, тексты и кнопки;
- цветовая схема должна строго учитывать пожелания пользователя: если пользователь просит тёмный сайт — используй тёмные HEX-цвета; если просит яркий — используй контрастные цвета; если просит спокойный — используй мягкую палитру;
- не делай все сайты белыми или серыми по умолчанию; фон, карточки и акценты должны отличаться по цвету;
- текст должен быть хорошо читаемым на выбранном фоне;
- НЕ добавляй изображения и НЕ добавляй поля image/imageCategory/imageUrl;
- готовый сайт НЕ должен визуально копировать интерфейс HGGps;
- дизайн должен соответствовать бизнесу пользователя;
- если пользователь не указал телефон или email, используй переданные резервные значения;
- нельзя делать интернет-магазин, корзину, оплату, личный кабинет и сложный drag-and-drop.

Данные пользователя:
Описание проекта:
{description}

Название компании, если пользователь указал отдельным полем:
{company_name or "Пользователь не указал отдельным полем. Если в описании есть явное название компании, используй его. Если названия нет, придумай короткое подходящее название сам."}

Тип сайта:
{site_type}

Цель сайта:
{goal}

ВАЖНО: главная цель сайта — главный параметр генерации. От неё должны зависеть структура сайта, порядок блоков, тексты, кнопки, названия страниц и финальный призыв к действию.

Если цель = "Получить заявки": делай сайт продающим, с упором на преимущества, доверие, форму/контакты и кнопки "Оставить заявку", "Получить консультацию".
Если цель = "Записать клиента": делай упор на запись, расписание, услуги, удобство, кнопки "Записаться", "Выбрать время", "Написать для записи".
Если цель = "Рассказать о компании": делай упор на историю, ценности, команду, преимущества, доверие, кнопки "Узнать больше", "Связаться".
Если цель = "Показать услуги": делай упор на список услуг, карточки услуг, цены/этапы/преимущества, кнопки "Выбрать услугу", "Получить консультацию".
Если цель = "Показать портфолио": делай упор на работы, кейсы, опыт, результаты, кнопки "Посмотреть работы", "Обсудить проект".
Если цель = "Рассказать о мероприятии": делай упор на дату, программу, место, расписание, регистрацию, кнопки "Зарегистрироваться", "Посмотреть программу".

Как пользователь хочет видеть оформление:
{design_preferences or "Пользователь не указал подробно. Выбери оформление самостоятельно по смыслу проекта."}

Какую информацию пользователь хочет видеть на сайте:
{desired_info or "Пользователь не указал подробно. Сам выбери полезные блоки по описанию проекта."}

Телефон для контактов:
{contact_phone}

Email для контактов:
{contact_email}

Количество кнопок, которое хочет пользователь:
{button_count}

{previous_block}

Верни только валидный JSON без markdown, без пояснений и без HTML.

Строгая структура JSON:
{{
  "siteName": "Название компании или придуманное название сайта",
  "siteType": "Лендинг или Многостраничный сайт",
  "goal": "Главная цель сайта",
  "design": {{
    "styleName": "Название выбранного ИИ стиля",
    "background": "Краткое описание фона",
    "layoutReason": "Почему ИИ выбрал такое расположение блоков",
    "primaryColor": "#HEX основной фон, не всегда белый",
    "secondaryColor": "#HEX дополнительный фон",
    "accentColor": "#HEX акцентный цвет кнопок",
    "textColor": "#HEX цвет текста с хорошим контрастом",
    "surfaceColor": "#HEX цвет карточек, отличается от основного фона",
    "fontMood": "Описание настроения шрифта"
  }},
  "siteMap": [
    {{"title": "Название страницы", "slug": "/", "description": "Краткое описание страницы"}}
  ],
  "pages": [
    {{
      "title": "Название страницы",
      "slug": "/",
      "type": "home",
      "sections": [
        {{
          "type": "hero",
          "anchorId": "home",
          "title": "Главный заголовок",
          "subtitle": "Подзаголовок",
          "buttons": [
            {{"text": "Текст кнопки", "target": "#services"}},
            {{"text": "Текст кнопки", "target": "#contacts"}}
          ]
        }},
        {{
          "type": "features",
          "anchorId": "features",
          "title": "Название блока",
          "items": [{{"title": "Название", "description": "Описание"}}]
        }},
        {{
          "type": "text",
          "anchorId": "services",
          "title": "Название блока",
          "description": "Текст блока"
        }},
        {{
          "type": "contact",
          "anchorId": "contacts",
          "title": "Контакты",
          "phone": "{contact_phone}",
          "email": "{contact_email}",
          "address": "Адрес или нейтральная фраза"
        }}
      ]
    }}
  ]
}}

Правила генерации:
1. Все тексты на русском языке.
2. Если пользователь указал название компании отдельным полем, siteName должен быть точно этим названием.
3. Если отдельное поле пустое, но в описании явно указано название компании, используй его как siteName.
4. Если названия нет, придумай короткое естественное название сам.
5. Не начинай siteName со слов "Описание проекта", "Сайт для", "Проект".
6. Для лендинга создай ровно 1 страницу со slug "/".
7. Для многостраничного сайта создай от 2 до 5 страниц. Разрешённые страницы: Главная, О нас, Услуги, Портфолио, Команда, FAQ, Контакты, Меню, Каталог, Расписание.
8. siteMap должен совпадать с pages.
9. У каждого важного блока должен быть anchorId. Используй понятные значения: home, features, services, about, portfolio, schedule, team, faq, catalog, contacts.
10. Количество кнопок в hero на главной странице должно быть равно {button_count}.
11. Кнопки НЕ должны все вести в один и тот же блок. Если кнопок несколько, распределяй их по разным смысловым блокам: #features, #services, #about, #portfolio, #schedule, #contacts.
12. Если кнопка явно про звонок — можно использовать tel:{contact_phone}. Если явно про почту — mailto:{contact_email}. В остальных случаях лучше вести к блокам сайта через #anchorId.
13. Не используй пустые ссылки, "#", "javascript:void(0)" и несуществующие якоря.
14. Тексты кнопок и целевые блоки должны соответствовать главной цели сайта.
15. Главный экран, порядок блоков и siteMap должны быть разными для разных целей сайта.
16. В каждом сайте обязательно должен быть контактный блок с anchorId="contacts", phone="{contact_phone}" и email="{contact_email}".
17. ИИ сам выбирает визуальный стиль и layout по описанию пользователя.
18. Структура блоков должна отличаться при перегенерации, если есть предыдущий вариант.
19. При перегенерации обязательно учитывай комментарий пользователя и меняй именно то, что он попросил изменить.
20. Цвета в design должны быть реальными HEX-цветами и соответствовать описанию оформления. Не ставь белый фон, если пользователь просит другой стиль.
21. Если пользователь просит тёмный, дорогой, неоновый, яркий, природный, кофейный, спортивный, детский или другой стиль — цветовая палитра должна явно это отражать.
22. JSON должен быть корректным.
23. Не выводи на сайте технические фразы: Gemini, provider, model, сгенерировано ИИ, стиль ИИ, объяснение логики блоков.
24. Не генерируй изображения и не добавляй image-поля.
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.85 if previous_site_json else 0.65,
        ),
    )

    raw_text = (response.text or "").strip()
    if not raw_text:
        raise ValueError("Gemini returned empty response")

    try:
        site_json = json.loads(raw_text)
    except json.JSONDecodeError:
        start = raw_text.find("{")
        end = raw_text.rfind("}") + 1
        if start == -1 or end <= 0:
            raise ValueError("Gemini returned invalid JSON")
        site_json = json.loads(raw_text[start:end])

    return normalize_generated_site(site_json, site_type, contact_email, contact_phone, button_count, company_name, description)


def normalize_generated_site(site_json: dict[str, Any], site_type: str, email: str, phone: str, button_count: int, company_name: str = "", description: str = "") -> dict[str, Any]:
    site_json["siteType"] = "Многостраничный сайт" if "много" in site_type.lower() else "Лендинг"
    resolved_name = resolve_site_name(company_name, description, site_json.get("siteName"))
    site_json["siteName"] = resolved_name

    pages = site_json.get("pages")
    if not isinstance(pages, list) or not pages:
        pages = []

    if site_json["siteType"] == "Лендинг":
        pages = pages[:1] or [{"title": "Главная", "slug": "/", "type": "home", "sections": []}]
        pages[0]["title"] = pages[0].get("title") or "Главная"
        pages[0]["slug"] = "/"
        pages[0]["type"] = "home"
    else:
        pages = pages[:5]
        if len(pages) < 2:
            pages.append({"title": "Контакты", "slug": "/contacts", "type": "contact", "sections": []})
        for index, page in enumerate(pages):
            title = str(page.get("title") or ("Главная" if index == 0 else f"Страница {index + 1}"))
            page["title"] = title
            page["slug"] = "/" if index == 0 else "/" + slug_text(title)
            page["type"] = "home" if index == 0 else slug_text(title)

    for page in pages:
        sections = page.get("sections")
        if not isinstance(sections, list):
            sections = []
        page["sections"] = sections
        for section in sections:
            if isinstance(section, dict):
                section.pop("image", None)
                section.pop("imageUrl", None)
                section.pop("imageCategory", None)

    if pages and not any(sec.get("type") == "hero" for sec in pages[0]["sections"] if isinstance(sec, dict)):
        pages[0]["sections"].insert(0, {
            "type": "hero",
            "anchorId": "home",
            "title": resolved_name,
            "subtitle": "Сайт создан на основе описания пользователя.",
            "buttons": [],
        })

    if pages and not any(sec.get("type") == "features" for sec in pages[0]["sections"] if isinstance(sec, dict)):
        pages[0]["sections"].append({
            "type": "features",
            "anchorId": "features",
            "title": "Преимущества",
            "items": [
                {"title": "Понятная структура", "description": "Информация собрана в логичном порядке."},
                {"title": "Быстрый контакт", "description": "Посетитель может быстро перейти к заявке."},
                {"title": "Под задачу", "description": "Блоки подобраны под цель сайта."},
            ],
        })

    if pages and not any(is_service_like(sec) for sec in pages[0]["sections"] if isinstance(sec, dict)):
        pages[0]["sections"].append({
            "type": "text",
            "anchorId": "services",
            "title": "Что доступно",
            "description": "Основная информация о проекте, услугах или предложении размещается в этом блоке.",
        })

    if not any(any(isinstance(sec, dict) and sec.get("type") == "contact" for sec in page.get("sections", [])) for page in pages):
        pages[-1]["sections"].append({
            "type": "contact",
            "anchorId": "contacts",
            "title": "Контакты",
            "phone": phone,
            "email": email,
            "address": "Адрес будет добавлен позже",
        })

    used_anchors: set[str] = set()
    for page_index, page in enumerate(pages):
        for section_index, section in enumerate(page.get("sections", [])):
            if not isinstance(section, dict):
                continue
            section["anchorId"] = make_section_anchor(section, page_index, section_index, used_anchors)
            if section.get("type") == "contact":
                section["anchorId"] = unique_anchor("contacts", used_anchors)
                section["phone"] = phone
                section["email"] = email

    hero = next((sec for sec in pages[0]["sections"] if isinstance(sec, dict) and sec.get("type") == "hero"), None) if pages else None
    if hero is not None:
        hero["anchorId"] = "home"
        hero_title = str(hero.get("title") or "").strip()
        if resolved_name and resolved_name.lower() not in hero_title.lower():
            hero["title"] = f"{resolved_name} — {hero_title}" if hero_title else resolved_name
        buttons = hero.get("buttons")
        if not isinstance(buttons, list):
            old_text = hero.get("buttonText", "Оставить заявку")
            buttons = [{"text": old_text, "target": "#contacts"}]
        while len(buttons) < button_count:
            buttons.append({"text": default_button_text(len(buttons), site_json.get("goal", "")), "target": ""})
        hero["buttons"] = normalize_buttons(buttons[:button_count], pages, phone, email, site_json.get("goal", ""))

    site_json["pages"] = pages
    site_json["siteMap"] = [
        {"title": page.get("title", "Страница"), "slug": page.get("slug", "/"), "description": page.get("description", f"Страница {page.get('title', '')}")}
        for page in pages
    ]
    site_json["contact"] = {"phone": phone, "email": email}

    design = site_json.get("design")
    if not isinstance(design, dict):
        design = {}

    palette = choose_fallback_palette(
        description=description,
        design_preferences=str(design.get("background") or "") + " " + str(design.get("styleName") or ""),
        goal=str(site_json.get("goal") or ""),
        site_name=str(site_json.get("siteName") or ""),
    )

    design.setdefault("styleName", palette["styleName"])
    design.setdefault("background", palette["background"])
    design.setdefault("layoutReason", "Блоки расположены по смыслу запроса пользователя.")
    design.setdefault("primaryColor", palette["primaryColor"])
    design.setdefault("secondaryColor", palette["secondaryColor"])
    design.setdefault("accentColor", palette["accentColor"])
    design.setdefault("textColor", palette["textColor"])
    design.setdefault("surfaceColor", palette["surfaceColor"])
    design.setdefault("fontMood", palette["fontMood"])
    site_json["design"] = sanitize_design(design, palette)
    return site_json


def is_service_like(section: dict[str, Any]) -> bool:
    text = " ".join([str(section.get("anchorId", "")), str(section.get("title", "")), str(section.get("type", ""))]).lower()
    return any(word in text for word in ["service", "услуг", "направ", "каталог", "меню", "portfolio", "портф", "schedule", "распис"])


def make_section_anchor(section: dict[str, Any], page_index: int, section_index: int, used: set[str]) -> str:
    raw = str(section.get("anchorId") or "").strip().lower().lstrip("#")
    if raw and re.fullmatch(r"[a-z0-9\-]+", raw):
        return unique_anchor(raw, used)

    section_type = str(section.get("type") or "").lower()
    title = str(section.get("title") or "").lower()
    text = f"{section_type} {title}"

    if section_type == "hero" and page_index == 0:
        used.add("home")
        return "home"
    if section_type == "contact":
        return unique_anchor("contacts", used)
    if section_type == "features":
        return unique_anchor("features", used)

    for anchor, words in ANCHOR_BY_MEANING.items():
        if any(word in text for word in words):
            return unique_anchor(anchor, used)

    return unique_anchor(f"section-{page_index}-{section_index}", used)


def unique_anchor(base: str, used: set[str]) -> str:
    base = re.sub(r"[^a-z0-9\-]+", "-", base.lower()).strip("-") or "section"
    if base not in used:
        used.add(base)
        return base
    counter = 2
    while f"{base}-{counter}" in used:
        counter += 1
    value = f"{base}-{counter}"
    used.add(value)
    return value


def available_anchors(pages: list[dict[str, Any]]) -> list[str]:
    anchors: list[str] = []
    for page in pages:
        for section in page.get("sections", []):
            if isinstance(section, dict):
                anchor = str(section.get("anchorId") or "").strip()
                if anchor and anchor != "home" and anchor not in anchors:
                    anchors.append(anchor)
    if "contacts" not in anchors:
        anchors.append("contacts")
    return anchors


def choose_anchor_for_button(text: str, target: str, anchors: list[str], used: set[str], index: int) -> str:
    low = f"{text} {target}".lower()
    preferred: list[str] = []
    if any(w in low for w in ["услуг", "выбрать", "стоим", "сервис"]):
        preferred += ["services", "catalog", "features"]
    if any(w in low for w in ["работ", "портф", "кейс", "пример"]):
        preferred += ["portfolio", "features"]
    if any(w in low for w in ["программ", "распис", "дат", "время"]):
        preferred += ["schedule", "features"]
    if any(w in low for w in ["узнать", "подробнее", "о нас", "компан"]):
        preferred += ["about", "features"]
    if any(w in low for w in ["заяв", "связ", "запис", "консульт", "контакт"]):
        preferred += ["contacts"]
    if target.startswith("#"):
        preferred.insert(0, target[1:])

    for anchor in preferred:
        if anchor in anchors and anchor not in used:
            return anchor
    for anchor in anchors:
        if anchor not in used:
            return anchor
    return anchors[index % len(anchors)] if anchors else "contacts"


def normalize_buttons(buttons: list[Any], pages: list[dict[str, Any]], phone: str, email: str, goal: str) -> list[dict[str, str]]:
    anchors = available_anchors(pages)
    used: set[str] = set()
    normalized: list[dict[str, str]] = []
    for index, button in enumerate(buttons):
        if isinstance(button, dict):
            text = str(button.get("text") or default_button_text(index, goal)).strip()
            target_raw = str(button.get("target") or "").strip()
        else:
            text = str(button or default_button_text(index, goal)).strip()
            target_raw = ""

        lower = text.lower()
        if any(word in lower for word in ["позвон", "звон", "телефон"]):
            target = "tel:" + re.sub(r"[^0-9+]", "", phone)
        elif any(word in lower for word in ["почт", "email", "mail"]):
            target = "mailto:" + email
        else:
            anchor = choose_anchor_for_button(text, target_raw, anchors, used, index)
            used.add(anchor)
            target = f"#{anchor}"

        normalized.append({"text": text[:44] or default_button_text(index, goal), "target": target})
    return normalized


def default_button_text(index: int, goal: str) -> str:
    goal_lower = (goal or "").lower()
    variants = ["Подробнее", "Перейти к услугам", "Связаться", "Посмотреть детали", "Оставить заявку"]
    if "заяв" in goal_lower:
        variants = ["Оставить заявку", "Почему нам доверяют", "Получить консультацию", "Узнать условия", "Связаться"]
    elif "запис" in goal_lower:
        variants = ["Записаться", "Посмотреть расписание", "Выбрать услугу", "Уточнить время", "Связаться"]
    elif "услуг" in goal_lower:
        variants = ["Посмотреть услуги", "Узнать преимущества", "Получить консультацию", "Уточнить стоимость", "Связаться"]
    elif "портф" in goal_lower:
        variants = ["Посмотреть работы", "Узнать подход", "Обсудить проект", "Посмотреть кейсы", "Связаться"]
    elif "мероприят" in goal_lower:
        variants = ["Зарегистрироваться", "Посмотреть программу", "Узнать место", "Уточнить детали", "Связаться"]
    return variants[index % len(variants)]


def choose_fallback_palette(description: str = "", design_preferences: str = "", goal: str = "", site_name: str = "") -> dict[str, str]:
    text = f"{description} {design_preferences} {goal} {site_name}".lower()

    palettes = {
        "dark": {
            "styleName": "Тёмный контрастный стиль",
            "background": "Тёмный фон с яркими акцентами",
            "primaryColor": "#10111f",
            "secondaryColor": "#1f1b35",
            "accentColor": "#a855f7",
            "textColor": "#f8fafc",
            "surfaceColor": "#191827",
            "fontMood": "Современный контрастный шрифт",
        },
        "coffee": {
            "styleName": "Тёплый кофейный стиль",
            "background": "Тёплый фон в кофейных и кремовых оттенках",
            "primaryColor": "#2b1a12",
            "secondaryColor": "#ead7bd",
            "accentColor": "#b86b35",
            "textColor": "#fff7ed",
            "surfaceColor": "#4a2d1f",
            "fontMood": "Мягкий уютный шрифт",
        },
        "beauty": {
            "styleName": "Мягкий beauty-стиль",
            "background": "Нежный фон с розовыми и светлыми акцентами",
            "primaryColor": "#fff1f6",
            "secondaryColor": "#f8d7e7",
            "accentColor": "#c026d3",
            "textColor": "#301323",
            "surfaceColor": "#ffffff",
            "fontMood": "Элегантный мягкий шрифт",
        },
        "nature": {
            "styleName": "Природный спокойный стиль",
            "background": "Натуральный фон в зелёных и светлых оттенках",
            "primaryColor": "#10251e",
            "secondaryColor": "#dbe8d5",
            "accentColor": "#3f7d58",
            "textColor": "#f7fff8",
            "surfaceColor": "#1e3a2e",
            "fontMood": "Спокойный чистый шрифт",
        },
        "sport": {
            "styleName": "Энергичный спортивный стиль",
            "background": "Контрастный фон с динамичными акцентами",
            "primaryColor": "#111827",
            "secondaryColor": "#1f2937",
            "accentColor": "#f97316",
            "textColor": "#f9fafb",
            "surfaceColor": "#182033",
            "fontMood": "Сильный уверенный шрифт",
        },
        "tech": {
            "styleName": "Технологичный стиль",
            "background": "Глубокий технологичный фон с холодными акцентами",
            "primaryColor": "#07111f",
            "secondaryColor": "#0f2a3f",
            "accentColor": "#22d3ee",
            "textColor": "#e0f2fe",
            "surfaceColor": "#0b1b2b",
            "fontMood": "Чёткий технологичный шрифт",
        },
        "bright": {
            "styleName": "Яркий современный стиль",
            "background": "Яркий фон с насыщенными акцентами",
            "primaryColor": "#fff7ed",
            "secondaryColor": "#fee2e2",
            "accentColor": "#ef4444",
            "textColor": "#2b1111",
            "surfaceColor": "#ffffff",
            "fontMood": "Дружелюбный современный шрифт",
        },
        "default": {
            "styleName": "Индивидуальный современный стиль",
            "background": "Фон подобран по тематике проекта",
            "primaryColor": "#171321",
            "secondaryColor": "#2c1d3a",
            "accentColor": "#f59e0b",
            "textColor": "#fff7ed",
            "surfaceColor": "#241b2f",
            "fontMood": "Современный выразительный шрифт",
        },
    }

    if any(word in text for word in ["тём", "темн", "черн", "black", "dark", "неон", "премиум"]):
        return palettes["dark"]
    if any(word in text for word in ["коф", "кафе", "шаур", "еда", "ресторан", "бар", "пекар"]):
        return palettes["coffee"]
    if any(word in text for word in ["салон", "крас", "beauty", "макияж", "ногт", "бров"]):
        return palettes["beauty"]
    if any(word in text for word in ["йог", "эко", "природ", "зел", "цвет", "сад"]):
        return palettes["nature"]
    if any(word in text for word in ["спорт", "фитнес", "зал", "трен", "бокс"]):
        return palettes["sport"]
    if any(word in text for word in ["it", "айти", "тех", "софт", "прилож", "стартап", "цифр"]):
        return palettes["tech"]
    if any(word in text for word in ["ярк", "дет", "празд", "фестив", "ивент"]):
        return palettes["bright"]
    return palettes["default"]


def sanitize_design(design: dict[str, Any], fallback_palette: dict[str, str] | None = None) -> dict[str, str]:
    fallback_palette = fallback_palette or choose_fallback_palette()

    def color(value: Any, fallback: str) -> str:
        value = str(value or "").strip()
        return value if re.fullmatch(r"#[0-9a-fA-F]{6}", value) else fallback

    result = {
        "styleName": str(design.get("styleName") or fallback_palette["styleName"])[:80],
        "background": str(design.get("background") or fallback_palette["background"])[:220],
        "layoutReason": str(design.get("layoutReason") or "Структура выбрана по описанию пользователя")[:300],
        "primaryColor": color(design.get("primaryColor"), fallback_palette["primaryColor"]),
        "secondaryColor": color(design.get("secondaryColor"), fallback_palette["secondaryColor"]),
        "accentColor": color(design.get("accentColor"), fallback_palette["accentColor"]),
        "textColor": color(design.get("textColor"), fallback_palette["textColor"]),
        "surfaceColor": color(design.get("surfaceColor"), fallback_palette["surfaceColor"]),
        "fontMood": str(design.get("fontMood") or fallback_palette["fontMood"])[:120],
    }

    # Если Gemini вернул почти белую палитру по умолчанию, заменяем её на осмысленную.
    if is_too_white_palette(result):
        result.update({
            "primaryColor": fallback_palette["primaryColor"],
            "secondaryColor": fallback_palette["secondaryColor"],
            "accentColor": fallback_palette["accentColor"],
            "textColor": fallback_palette["textColor"],
            "surfaceColor": fallback_palette["surfaceColor"],
        })

    result["textColor"] = ensure_readable_text(result["textColor"], result["primaryColor"], result["surfaceColor"])
    return result


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.strip().lstrip("#")
    return int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)


def luminance(hex_color: str) -> float:
    try:
        r, g, b = hex_to_rgb(hex_color)
    except Exception:
        return 1.0
    vals = []
    for c in (r, g, b):
        v = c / 255
        vals.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
    return 0.2126 * vals[0] + 0.7152 * vals[1] + 0.0722 * vals[2]


def contrast_ratio(c1: str, c2: str) -> float:
    l1, l2 = luminance(c1), luminance(c2)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def is_too_white_palette(design: dict[str, str]) -> bool:
    colors = [design.get("primaryColor", "#ffffff"), design.get("secondaryColor", "#ffffff"), design.get("surfaceColor", "#ffffff")]
    return sum(1 for c in colors if luminance(c) > 0.86) >= 2


def ensure_readable_text(text_color: str, primary: str, surface: str) -> str:
    if contrast_ratio(text_color, primary) >= 3.2 or contrast_ratio(text_color, surface) >= 3.2:
        return text_color
    avg = (luminance(primary) + luminance(surface)) / 2
    return "#111827" if avg > 0.55 else "#f9fafb"

def resolve_site_name(company_name: str | None, description: str, ai_name: Any) -> str:
    company_name = (company_name or "").strip()
    if company_name:
        return clean_site_name(company_name)

    extracted = extract_company_name(description)
    if extracted:
        return clean_site_name(extracted)

    ai_name = clean_site_name(str(ai_name or ""))
    bad_prefixes = ("описание проекта", "сайт для", "проект", "главная")
    if ai_name and len(ai_name) >= 3 and not ai_name.lower().startswith(bad_prefixes):
        return ai_name

    return make_title(description)


def clean_site_name(value: str) -> str:
    value = re.sub(r"\s+", " ", value or "").strip(" .,:;—-")
    return value[:70] if value else "Сайт для вашего проекта"


def extract_company_name(description: str) -> str:
    text = description or ""
    patterns = [
        r"(?:компания|бренд|название|студия|кафе|кофейня|салон|школа|агентство)\s+(?:называется\s+)?[«\"']([^»\"'.,\n]{2,50})[»\"']",
        r"[«\"']([^»\"'.,\n]{2,50})[»\"']",
        r"(?:компания|бренд|название)\s+(?:—|-|:)\s*([^.,\n]{2,50})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def generate_mock_site(description: str, site_type: str, goal: str, company_name: str, design_preferences: str, desired_info: str, contact_email: str, contact_phone: str, button_count: int) -> dict[str, Any]:
    title = resolve_site_name(company_name, description, make_title(description))
    is_multi = "много" in site_type.lower()
    goal_lower = goal.lower()

    if "заяв" in goal_lower:
        features_title, text_title = "Почему стоит оставить заявку", "Как мы поможем"
    elif "запис" in goal_lower:
        features_title, text_title = "Почему удобно записаться", "Как проходит запись"
    elif "компан" in goal_lower:
        features_title, text_title = "О компании", "Кто мы и чем полезны"
    elif "услуг" in goal_lower:
        features_title, text_title = "Основные услуги", "Что входит в услуги"
    elif "портф" in goal_lower:
        features_title, text_title = "Работы и опыт", "Что можно увидеть в портфолио"
    elif "мероприят" in goal_lower:
        features_title, text_title = "Почему стоит участвовать", "О мероприятии"
    else:
        features_title, text_title = "Преимущества", "Что будет на сайте"

    pages = [{
        "title": "Главная",
        "slug": "/",
        "type": "home",
        "sections": [
            {"type": "hero", "anchorId": "home", "title": title, "subtitle": description[:280], "buttons": []},
            {"type": "features", "anchorId": "features", "title": features_title, "items": [
                {"title": "Понятная структура", "description": "Посетитель быстро понимает предложение."},
                {"title": "Удобные переходы", "description": "Кнопки ведут в разные важные блоки сайта."},
                {"title": "Контакт в один шаг", "description": "Данные для связи находятся в отдельном блоке."},
            ]},
            {"type": "text", "anchorId": "services", "title": text_title, "description": desired_info or "ИИ подобрал базовые блоки по описанию проекта."},
            {"type": "contact", "anchorId": "contacts", "title": "Контакты", "phone": contact_phone, "email": contact_email, "address": "Адрес будет добавлен позже"},
        ],
    }]

    if is_multi:
        pages.append({"title": "Услуги", "slug": "/uslugi", "type": "services", "sections": [{"type": "text", "anchorId": "services-page", "title": "Услуги", "description": desired_info or "Описание услуг будет дополнено."}]})
        pages.append({"title": "Контакты", "slug": "/kontakty", "type": "contacts", "sections": [{"type": "contact", "anchorId": "contacts", "title": "Контакты", "phone": contact_phone, "email": contact_email, "address": "Адрес будет добавлен позже"}]})

    palette = choose_fallback_palette(description, design_preferences, goal, title)
    site_json = {
        "siteName": title,
        "siteType": "Многостраничный сайт" if is_multi else "Лендинг",
        "goal": goal,
        "design": {
            "styleName": palette["styleName"],
            "background": design_preferences or palette["background"],
            "layoutReason": "Блоки расположены по смыслу пользовательского запроса.",
            "primaryColor": palette["primaryColor"],
            "secondaryColor": palette["secondaryColor"],
            "accentColor": palette["accentColor"],
            "textColor": palette["textColor"],
            "surfaceColor": palette["surfaceColor"],
            "fontMood": palette["fontMood"],
        },
        "pages": pages,
    }
    return normalize_generated_site(site_json, site_type, contact_email, contact_phone, button_count, company_name, description)


def validate_site_json(site_json: dict[str, Any]) -> None:
    if not isinstance(site_json, dict):
        raise ValueError("site_json must be object")
    if not site_json.get("siteName"):
        raise ValueError("siteName is missing")
    if not isinstance(site_json.get("pages"), list) or not site_json["pages"]:
        raise ValueError("pages must be non-empty list")


def make_title(description: str) -> str:
    clean = description.replace("Описание проекта:", "").strip()
    first_line = clean.split("\n")[0]
    first_sentence = first_line.split(".")[0].strip()
    if len(first_sentence) < 5:
        return "Сайт для вашего проекта"
    return first_sentence[:60]


def slug_text(text: str) -> str:
    mapping = {
        "Главная": "home",
        "О нас": "about",
        "Услуги": "services",
        "Портфолио": "portfolio",
        "Команда": "team",
        "FAQ": "faq",
        "Контакты": "contacts",
        "Меню": "menu",
        "Каталог": "catalog",
        "Расписание": "schedule",
    }
    return mapping.get(text, re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-") or "page")
