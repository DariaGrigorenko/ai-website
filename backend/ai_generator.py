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

ALLOWED_PAGE_TITLES = {
    "Главная", "О нас", "Услуги", "Портфолио", "Команда", "FAQ", "Контакты", "Меню", "Каталог", "Расписание"
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

    site_json["contact"] = {
        "phone": phone,
        "email": email,
    }
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

Комментарий к перегенерации:
{regeneration_note or "Сделай другой вариант: измени структуру, стиль, тексты и расположение блоков."}
"""

    prompt = f"""
Ты — ИИ-конструктор сайтов HGGps. Твоя задача — полностью самостоятельно проанализировать запрос пользователя и сгенерировать сайт.

Основные требования MVP:
- поддерживаются только два типа сайта: "Лендинг" и "Многостраничный сайт";
- лендинг — одна страница;
- многостраничный сайт — от 2 до 5 страниц;
- ИИ сам выбирает стиль, фон, цветовую схему, расположение блоков, названия блоков, тексты и кнопки;
- готовый сайт НЕ должен визуально копировать интерфейс HGGps: не используй одинаковую структуру, одинаковые красно-чёрные карточки и одинаковый стиль конструктора;
- дизайн должен соответствовать бизнесу пользователя: можно выбирать светлый, природный, премиальный, творческий, деловой или другой стиль;
- пользователь только описывает проект, желаемое оформление, нужную информацию, контакты и количество кнопок;
- если пользователь не указал телефон или email, используй переданные резервные значения;
- сайт должен быть готов к предпросмотру и публикации по ссылке;
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

ВАЖНО: главная цель сайта — это главный параметр генерации. От неё должны зависеть структура сайта, порядок блоков, тексты, кнопки, названия страниц и финальный призыв к действию.

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
    "primaryColor": "#HEX",
    "secondaryColor": "#HEX",
    "accentColor": "#HEX",
    "textColor": "#HEX",
    "surfaceColor": "#HEX",
    "fontMood": "Описание настроения шрифта"
  }},
  "siteMap": [
    {{
      "title": "Название страницы",
      "slug": "/",
      "description": "Краткое описание страницы"
    }}
  ],
  "pages": [
    {{
      "title": "Название страницы",
      "slug": "/",
      "type": "home",
      "sections": [
        {{
          "type": "hero",
          "title": "Главный заголовок",
          "subtitle": "Подзаголовок",
          "image": {{
            "category": "одна категория из списка: coffee, food, beauty, fitness, yoga, education, business, portfolio, event, technology, interior, travel, health, creative, default",
            "alt": "Короткое описание изображения"
          }},
          "buttons": [
            {{"text": "Текст кнопки", "target": "#contacts"}}
          ]
        }},
        {{
          "type": "features",
          "title": "Название блока",
          "items": [
            {{"title": "Название", "description": "Описание"}}
          ]
        }},
        {{
          "type": "text",
          "title": "Название блока",
          "description": "Текст блока"
        }},
        {{
          "type": "contact",
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
1.1. Все кнопки должны быть рабочими: target используй только "#contacts", "tel:{contact_phone}" или "mailto:{contact_email}". Не используй пустые ссылки, "#", "javascript:void(0)" и несуществующие якоря.
2. Если пользователь указал название компании отдельным полем, siteName должен быть точно этим названием.
3. Если отдельное поле пустое, но в описании явно указано название компании, используй его как siteName.
4. Если названия нет, придумай короткое естественное название сам.
5. Не начинай siteName со слов "Описание проекта", "Сайт для", "Проект".
6. Для лендинга создай ровно 1 страницу со slug "/".
7. Для многостраничного сайта создай от 2 до 5 страниц. Разрешённые страницы: Главная, О нас, Услуги, Портфолио, Команда, FAQ, Контакты, Меню, Каталог, Расписание.
8. siteMap должен совпадать с pages.
9. Количество кнопок в hero на главной странице должно быть равно {button_count}. Все кнопки должны вести к контактам, заявке, телефону или email, чтобы они реально работали. Тексты кнопок обязательно должны соответствовать выбранной цели сайта.
10. Главный экран, порядок блоков и siteMap должны быть разными для разных целей сайта. Нельзя делать одинаковую структуру для всех целей.
11. В каждом сайте обязательно должен быть контактный блок с phone="{contact_phone}" и email="{contact_email}".
12. ИИ сам выбирает визуальный стиль и layout по описанию пользователя, не спрашивая выбор из готовых вариантов.
13. Структура блоков должна отличаться при перегенерации, если есть предыдущий вариант.
14. JSON должен быть корректным.
15. Не выводи на сайте технические фразы: Gemini, provider, model, сгенерировано ИИ, стиль ИИ, объяснение логики блоков.
16. Для hero-блока обязательно выбери image.category по смыслу проекта. Например: кофейня -> coffee/food, йога -> yoga/fitness, салон красоты -> beauty, школа -> education, IT -> technology, мероприятие -> event, портфолио -> portfolio.
17. Не генерируй прямые URL картинок. Верни только смысловую категорию изображения и alt. Backend сам подставит подходящее изображение.
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
    guessed_image_category = guess_image_category(" ".join([description, str(site_json.get("siteName", "")), str(site_json.get("goal", ""))]))

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

    if pages and not any(sec.get("type") == "hero" for sec in pages[0]["sections"]):
        pages[0]["sections"].insert(0, {
            "type": "hero",
            "title": site_json.get("siteName", "Сайт для вашего проекта"),
            "subtitle": "Сайт сгенерирован на основе описания пользователя.",
            "image": {"category": guessed_image_category, "alt": f"Изображение для сайта {site_json.get('siteName', '')}"},
            "buttons": [{"text": "Оставить заявку", "target": "#contacts"}],
        })

    hero = next((sec for sec in pages[0]["sections"] if sec.get("type") == "hero"), None)
    if hero is not None:
        hero_title = str(hero.get("title") or "").strip()
        if resolved_name and resolved_name.lower() not in hero_title.lower():
            hero["title"] = f"{resolved_name} — {hero_title}" if hero_title else resolved_name
        buttons = hero.get("buttons")
        if not isinstance(buttons, list):
            old_text = hero.get("buttonText", "Оставить заявку")
            buttons = [{"text": old_text, "target": "#contacts"}]
        while len(buttons) < button_count:
            buttons.append({"text": f"Действие {len(buttons) + 1}", "target": "#contacts"})
        hero["buttons"] = normalize_buttons(buttons[:button_count], phone, email)
        normalize_image(hero, guessed_image_category, resolved_name)

    if not any(any(sec.get("type") == "contact" for sec in page.get("sections", [])) for page in pages):
        pages[-1]["sections"].append({
            "type": "contact",
            "title": "Контакты",
            "phone": phone,
            "email": email,
            "address": "Адрес будет добавлен позже",
        })

    for page in pages:
        for sec in page.get("sections", []):
            if sec.get("type") == "contact":
                sec["phone"] = phone
                sec["email"] = email

    site_json["pages"] = pages
    site_json["siteMap"] = [
        {
            "title": page.get("title", "Страница"),
            "slug": page.get("slug", "/"),
            "description": page.get("description", f"Страница {page.get('title', '')}"),
        }
        for page in pages
    ]
    site_json["contact"] = {"phone": phone, "email": email}

    design = site_json.get("design")
    if not isinstance(design, dict):
        design = {}
    design.setdefault("styleName", "Современный адаптивный стиль")
    design.setdefault("background", "Градиентный фон, подобранный по тематике проекта")
    design.setdefault("layoutReason", "Блоки расположены так, чтобы сначала показать ценность, затем детали и контакты.")
    design.setdefault("primaryColor", "#0b0b10")
    design.setdefault("secondaryColor", "#151827")
    design.setdefault("accentColor", "#e11d2e")
    design.setdefault("textColor", "#ffffff")
    design.setdefault("surfaceColor", "#12121a")
    design.setdefault("fontMood", "Современный простой интерфейс")
    design.setdefault("imageCategory", guessed_image_category)
    site_json["design"] = sanitize_design(design)

    return site_json


def sanitize_design(design: dict[str, Any]) -> dict[str, str]:
    def color(value: Any, fallback: str) -> str:
        value = str(value or "").strip()
        return value if re.fullmatch(r"#[0-9a-fA-F]{6}", value) else fallback

    return {
        "styleName": str(design.get("styleName") or "Современный стиль")[:80],
        "background": str(design.get("background") or "Фон подобран ИИ")[:220],
        "layoutReason": str(design.get("layoutReason") or "ИИ выбрал структуру по описанию пользователя")[:300],
        "primaryColor": color(design.get("primaryColor"), "#0b0b10"),
        "secondaryColor": color(design.get("secondaryColor"), "#151827"),
        "accentColor": color(design.get("accentColor"), "#e11d2e"),
        "textColor": color(design.get("textColor"), "#ffffff"),
        "surfaceColor": color(design.get("surfaceColor"), "#12121a"),
        "fontMood": str(design.get("fontMood") or "Современный простой интерфейс")[:120],
        "imageCategory": str(design.get("imageCategory") or "default").strip().lower()[:40],
    }



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



def guess_image_category(text: str) -> str:
    value = (text or "").lower()
    rules = [
        ("coffee", ["кофе", "кофейн", "кафе", "бариста"]),
        ("food", ["еда", "ресторан", "меню", "десерт", "пицц", "суши"]),
        ("beauty", ["красот", "салон", "маникюр", "космет", "парикмах", "бров"]),
        ("yoga", ["йога", "пилатес", "растяж"]),
        ("fitness", ["фитнес", "спорт", "трениров", "зал"]),
        ("education", ["школ", "курс", "обуч", "репетитор", "образован"]),
        ("technology", ["it", "айти", "сайт", "прилож", "технолог", "стартап"]),
        ("event", ["мероприят", "конферен", "фестиваль", "выставк", "событ"]),
        ("portfolio", ["портфолио", "фотограф", "дизайн", "работы", "кейсы"]),
        ("health", ["клиник", "здоров", "медиц", "врач"]),
        ("travel", ["тур", "путешеств", "отель", "гостиниц"]),
        ("business", ["бизнес", "агентство", "компания", "консалт"]),
    ]
    for category, words in rules:
        if any(word in value for word in words):
            return category
    return "default"


def normalize_image(section: dict[str, Any], category: str, site_name: str) -> None:
    image = section.get("image") if isinstance(section.get("image"), dict) else {}
    image_category = str(image.get("category") or section.get("imageCategory") or category or "default").strip().lower()
    allowed = {"coffee", "food", "beauty", "fitness", "yoga", "education", "business", "portfolio", "event", "technology", "interior", "travel", "health", "creative", "default"}
    if image_category not in allowed:
        image_category = category if category in allowed else "default"
    image_alt = str(image.get("alt") or section.get("imageAlt") or f"Изображение для сайта {site_name}").strip()[:120]
    section["image"] = {"category": image_category, "alt": image_alt}

def normalize_buttons(buttons: list[Any], phone: str, email: str) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for index, button in enumerate(buttons):
        if isinstance(button, dict):
            text = str(button.get("text") or f"Кнопка {index + 1}").strip()
        else:
            text = str(button or f"Кнопка {index + 1}").strip()

        lower = text.lower()
        if any(word in lower for word in ["позвон", "звон", "телефон"]):
            target = "tel:" + re.sub(r"[^0-9+]", "", phone)
        elif any(word in lower for word in ["почт", "email", "mail", "напис"]):
            target = "mailto:" + email
        else:
            target = "#contacts"

        normalized.append({"text": text[:40] or f"Кнопка {index + 1}", "target": target})
    return normalized

def generate_mock_site(
    description: str,
    site_type: str,
    goal: str,
    company_name: str,
    design_preferences: str,
    desired_info: str,
    contact_email: str,
    contact_phone: str,
    button_count: int,
) -> dict[str, Any]:
    title = resolve_site_name(company_name, description, make_title(description))
    is_multi = "много" in site_type.lower()

    goal_lower = goal.lower()
    if "заяв" in goal_lower:
        hero_buttons = ["Оставить заявку", "Получить консультацию", "Связаться"]
        features_title = "Почему стоит оставить заявку"
        text_title = "Как мы поможем"
    elif "запис" in goal_lower:
        hero_buttons = ["Записаться", "Выбрать время", "Написать для записи"]
        features_title = "Почему удобно записаться"
        text_title = "Как проходит запись"
    elif "компан" in goal_lower:
        hero_buttons = ["Узнать больше", "Связаться", "Посмотреть услуги"]
        features_title = "О компании"
        text_title = "Кто мы и чем полезны"
    elif "услуг" in goal_lower:
        hero_buttons = ["Выбрать услугу", "Получить консультацию", "Уточнить стоимость"]
        features_title = "Основные услуги"
        text_title = "Что входит в услуги"
    elif "портф" in goal_lower:
        hero_buttons = ["Посмотреть работы", "Обсудить проект", "Связаться"]
        features_title = "Работы и опыт"
        text_title = "Что можно увидеть в портфолио"
    elif "мероприят" in goal_lower:
        hero_buttons = ["Зарегистрироваться", "Посмотреть программу", "Уточнить детали"]
        features_title = "Почему стоит участвовать"
        text_title = "О мероприятии"
    else:
        hero_buttons = ["Оставить заявку", "Подробнее", "Связаться"]
        features_title = "Преимущества"
        text_title = "Что будет на сайте"

    pages = [
        {
            "title": "Главная",
            "slug": "/",
            "type": "home",
            "sections": [
                {
                    "type": "hero",
                    "title": title,
                    "subtitle": description[:280],
                    "image": {"category": guess_image_category(description), "alt": f"Изображение для сайта {title}"},
                    "buttons": [
                        {"text": hero_buttons[index % len(hero_buttons)], "target": "#contacts"}
                        for index in range(button_count)
                    ],
                },
                {
                    "type": "features",
                    "title": features_title,
                    "items": [
                        {"title": "Быстрый запуск", "description": "Сайт собирается за несколько минут."},
                        {"title": "ИИ-структура", "description": "Блоки и тексты подбираются автоматически."},
                        {"title": "Публичная ссылка", "description": "Результат можно сразу открыть в браузере."},
                    ],
                },
                {
                    "type": "text",
                    "title": text_title,
                    "description": desired_info or "ИИ подобрал базовые блоки по описанию проекта.",
                },
                {
                    "type": "contact",
                    "title": "Контакты",
                    "phone": contact_phone,
                    "email": contact_email,
                    "address": "Адрес будет добавлен позже",
                },
            ],
        }
    ]

    if is_multi:
        pages.append({
            "title": "Услуги",
            "slug": "/uslugi",
            "type": "services",
            "sections": [{"type": "text", "title": "Услуги", "description": desired_info or "Описание услуг будет дополнено."}],
        })
        pages.append({
            "title": "Контакты",
            "slug": "/kontakty",
            "type": "contacts",
            "sections": [{"type": "contact", "title": "Контакты", "phone": contact_phone, "email": contact_email, "address": "Адрес будет добавлен позже"}],
        })

    site_json = {
        "siteName": title,
        "siteType": "Многостраничный сайт" if is_multi else "Лендинг",
        "goal": goal,
        "design": {
            "styleName": "Автоматический стиль",
            "background": design_preferences or "Фон подобран автоматически",
            "layoutReason": "ИИ разместил блоки по базовой логике лендинга.",
            "primaryColor": "#0b0b10",
            "secondaryColor": "#151827",
            "accentColor": "#e11d2e",
            "textColor": "#ffffff",
            "surfaceColor": "#12121a",
            "fontMood": "Современный простой стиль",
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
