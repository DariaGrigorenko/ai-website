# FINAL_WORKING_HGGPS_GENERATOR_V3_CONTACT_BUTTONS
import json
import os
import random
import re
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

AI_PROVIDER = os.getenv("AI_PROVIDER", "deepseek").lower().strip()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

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
        site_json = generate_site_with_deepseek(
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
        site_json["_generatedBy"] = "deepseek"
        site_json["_aiModel"] = DEEPSEEK_MODEL
    except Exception as error:
        print("DeepSeek generation failed. Mock generation used:", repr(error))
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


def generate_site_with_deepseek(
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
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY is missing")

    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

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

Основные требования:
- поддерживаются только два типа сайта: "Лендинг" и "Многостраничный сайт";
- лендинг — одна страница;
- многостраничный сайт — от 2 до 5 страниц;
- ИИ сам выбирает стиль, фон, цветовую схему, расположение блоков, названия блоков, тексты и кнопки;
- дизайн должен реально меняться: меняй цвета, layoutVariant, cardStyle, sectionShape, fontFamily, density; heroVisual всегда ставь "none", потому что изображения и декоративные заглушки не нужны;
- не создавай декоративные круги, овалы, пустые визуальные панели, псевдо-картинки или блоки без текста;
- НЕ добавляй изображения и НЕ добавляй поля image/imageCategory/imageUrl;
- готовый сайт НЕ должен визуально копировать интерфейс HGGps;
- дизайн должен соответствовать бизнесу пользователя;
- цель сайта используй только для логики структуры, текстов и кнопок; НЕ выводи выбранную цель как отдельную надпись на первом экране;
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
Внутри строк тоже запрещён markdown: не используй **жирный текст**, __подчёркивание__, списки через -, markdown-ссылки и символы `.

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
    "fontMood": "Описание настроения шрифта",
    "layoutVariant": "split | centered | editorial | grid | brutal | calm",
    "cardStyle": "solid | outline | glass | minimal | raised",
    "heroVisual": "none",
    "sectionShape": "rounded | sharp | pill | asymmetric",
    "fontFamily": "serif | sans | mono | display",
    "density": "air | normal | compact"
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
7. Для многостраничного сайта создай от 2 до 5 НАСТОЯЩИХ страниц. Разрешённые страницы: Главная, О нас, Услуги, Портфолио, Команда, FAQ, Контакты, Меню, Каталог, Расписание.
8. Для многостраничного сайта у каждой страницы, кроме главной, должен быть отдельный slug: "/services", "/about", "/portfolio", "/contacts" и т.п. Не делай многостраничный сайт одной страницей с якорями.
9. siteMap должен совпадать с pages.
10. У каждого важного блока может быть anchorId. Для многостраничного сайта навигация и обычные кнопки ведут на страницы, а контактные кнопки ведут на /contacts.
11. Количество кнопок в hero на главной странице должно быть равно {button_count}.
12. Для лендинга кнопки могут вести на разные блоки: #features, #services, #about, #portfolio, #schedule, #contacts.
13. Для многостраничного сайта обычные кнопки могут вести на разные страницы: /services, /about, /portfolio, /schedule. Но кнопки связи, записи, заявки, консультации, звонка и контактов ВСЕГДА ведут на /contacts.
14. Никогда не используй tel:, mailto:, пустые ссылки, внешние ссылки и javascript. Кнопки связи, записи, заявки, консультации, звонка и контактов должны вести только на #contacts для лендинга или /contacts для многостраничного сайта.
15. Не используй пустые ссылки, "#", "javascript:void(0)" и несуществующие цели.
16. Тексты кнопок и целевые страницы должны соответствовать главной цели сайта.
17. Главный экран, порядок страниц, тексты и siteMap должны быть разными для разных целей сайта.
18. В каждом сайте обязательно должен быть контактный раздел или отдельная страница контактов с phone="{contact_phone}" и email="{contact_email}".
19. ИИ сам выбирает визуальный стиль и layout по описанию пользователя. Обязательно заполняй поля design.layoutVariant, design.cardStyle, design.sectionShape, design.fontFamily, design.density. Поле design.heroVisual всегда должно быть "none".
19.1. Если пользователь просит тёмный/яркий/минималистичный/премиальный/неоновый/строгий/мягкий стиль — это должно менять цвета, шрифты, форму карточек, hero-блок, сетку и вид текстовых блоков.
19.2. Не используй один и тот же внешний вид для разных запросов. Для IT подойдут grid/mono/sharp, для кафе — calm/rounded/raised, для портфолио — editorial/minimal/asymmetric, для мероприятия — brutal/display/outline.
20. Структура страниц и тексты должны отличаться при перегенерации, если есть предыдущий вариант. Обязательно учитывай комментарий пользователя к перегенерации.
21. JSON должен быть корректным.
22. Не выводи на сайте технические фразы: DeepSeek, Gemini, provider, model, сгенерировано ИИ, стиль ИИ, объяснение логики блоков.
23. Не генерируй изображения и не добавляй image-поля.
23.1. Не выводи системные значения из формы как декоративные подписи: не пиши на сайте отдельной строкой "Показать услуги", "Получить заявки", "Записать клиента" и другие названия целей. Цель нужна только для выбора структуры.
24. Нейро-слоп запрещён. Не используй общие пустые фразы: "индивидуальный подход", "высокое качество", "профессиональная команда", "широкий спектр услуг", "лучшие решения", "современные решения", "комплексный подход", "мы ценим каждого клиента", "быстро и качественно", "ваш надёжный партнёр".
24.1. Каждый абзац должен содержать конкретику из запроса: предмет услуги/проекта, аудиторию, действие посетителя, результат, формат работы, состав предложения, место, время, цену/этапы, если они указаны.
24.2. Если данных мало, не пиши рекламную воду. Лучше коротко сформулируй конкретный блок на основе того, что известно.
25. Каждый блок должен отвечать на конкретный вопрос посетителя: что это, зачем это нужно, как воспользоваться, почему стоит обратиться, как связаться.
26. Не пиши одинаковые заголовки и одинаковые описания в разных блоках. Каждый блок должен иметь свою роль.
27. Не создавай общий блок с названием "Что доступно", "Что мы предлагаем", "Наши возможности", если пользователь прямо не просил такой блок. Вместо этого называй блок конкретно: "Тренировки для начинающих", "Меню шаурмы", "Ремонт iPhone", "Запись на консультацию" и т.п.
28. Не пиши несколько услуг/цен/событий одним абзацем через **Название:** описание. Если внутри раздела есть несколько пунктов, используй type="features" и массив items, где каждый пункт — отдельная карточка с title и description.
29. В description допускается только обычный чистый текст без символов **. Для выделения смысла используй отдельные title в items.
30. Не создавай пустые карточки, карточки с одной точкой, одним символом или без осмысленного текста.
31. Название сайта и заголовки должны быть нормальными словами. Запрещён мусор вида "2п32п2п" или похожие наборы символов.
"""

    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Ты генератор JSON для ИИ-конструктора сайтов HGGps. "
                    "Отвечай только валидным JSON без markdown, без пояснений и без HTML. "
                    "Не используй общие рекламные фразы, пиши конкретно по запросу пользователя."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.85 if previous_site_json else 0.65,
    )

    raw_text = (response.choices[0].message.content or "").strip()
    if not raw_text:
        raise ValueError("DeepSeek returned empty response")

    try:
        site_json = json.loads(raw_text)
    except json.JSONDecodeError:
        start = raw_text.find("{")
        end = raw_text.rfind("}") + 1
        if start == -1 or end <= 0:
            raise ValueError("DeepSeek returned invalid JSON")
        site_json = json.loads(raw_text[start:end])

    return normalize_generated_site(site_json, site_type, contact_email, contact_phone, button_count, company_name, description, design_preferences, desired_info)


def normalize_generated_site(site_json: dict[str, Any], site_type: str, email: str, phone: str, button_count: int, company_name: str = "", description: str = "", design_preferences: str = "", desired_info: str = "") -> dict[str, Any]:
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

    # Не добавляем запасной блок "Что доступно": он выглядел как нейро-слоп.
    # Если Gemini не создал блок услуг/описания, оставляем структуру без общего пустого блока.

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
    contact_anchor_set = False
    for page_index, page in enumerate(pages):
        page["title"] = clean_or_default(page.get("title"), "Главная" if page_index == 0 else "Страница")
        for section_index, section in enumerate(page.get("sections", [])):
            if not isinstance(section, dict):
                continue
            section["title"] = clean_or_default(section.get("title"), "Раздел")
            if "subtitle" in section:
                section["subtitle"] = clean_or_default(section.get("subtitle"), "Оставьте заявку — мы свяжемся и уточним детали.")
            if "description" in section:
                section["description"] = clean_or_default(section.get("description"), "")
            if isinstance(section.get("items"), list):
                cleaned_items = []
                for item in section["items"]:
                    if isinstance(item, dict):
                        title = clean_or_default(item.get("title"), "")
                        desc = clean_or_default(item.get("description"), "")
                        if title or desc:
                            cleaned_items.append({"title": title or "Подробнее", "description": desc or "Информация будет уточнена."})
                    else:
                        val = clean_or_default(item, "")
                        if val:
                            cleaned_items.append({"title": val, "description": ""})
                section["items"] = cleaned_items
            if section.get("type") == "contact" and not contact_anchor_set:
                section["anchorId"] = "contacts"
                used_anchors.add("contacts")
                contact_anchor_set = True
                section["phone"] = phone
                section["email"] = email
            else:
                section["anchorId"] = make_section_anchor(section, page_index, section_index, used_anchors)

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
        hero["buttons"] = normalize_buttons(buttons[:button_count], pages, phone, email, site_json.get("goal", ""), site_json["siteType"] == "Многостраничный сайт")

    site_json["pages"] = pages
    site_json["siteMap"] = [
        {"title": page.get("title", "Страница"), "slug": page.get("slug", "/"), "description": page.get("description", f"Страница {page.get('title', '')}")}
        for page in pages
    ]
    site_json["contact"] = {"phone": phone, "email": email}

    design = site_json.get("design")
    if not isinstance(design, dict):
        design = {}
    inferred = infer_visual_design(description, design_preferences, desired_info)
    design.setdefault("styleName", "Индивидуальный стиль")
    design.setdefault("background", "Фон подобран по тематике проекта")
    design.setdefault("layoutReason", "Блоки расположены по смыслу запроса пользователя.")
    design.setdefault("primaryColor", inferred.get("primaryColor", "#101522"))
    design.setdefault("secondaryColor", inferred.get("secondaryColor", "#1b2440"))
    design.setdefault("accentColor", inferred.get("accentColor", "#ef476f"))
    design.setdefault("textColor", inferred.get("textColor", "#f7f4ee"))
    design.setdefault("surfaceColor", inferred.get("surfaceColor", "#151b2e"))
    design.setdefault("fontMood", "Чистый современный стиль")
    design["heroVisual"] = "none"
    # Цветовую палитру берём из красивого тематического набора, чтобы не было кислотного дизайна.
    for key in ["primaryColor", "secondaryColor", "accentColor", "textColor", "surfaceColor"]:
        design[key] = inferred[key]
    for key, value in inferred.items():
        design.setdefault(key, value)
    site_json["design"] = sanitize_design(design, inferred)
    reduce_neuro_slop(site_json, description, desired_info)
    remove_markdown_from_site(site_json)
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



def available_pages(pages: list[dict[str, Any]]) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for index, page in enumerate(pages):
        if not isinstance(page, dict):
            continue
        raw_slug = str(page.get("slug") or "").strip().strip("/")
        if index == 0 or raw_slug in {"", "home"}:
            continue
        slug = slug_text(raw_slug) if raw_slug.startswith("/") else slug_text(raw_slug)
        if not slug:
            slug = slug_text(str(page.get("title") or f"page-{index}"))
        title = str(page.get("title") or slug)
        if slug and (slug, title) not in result:
            result.append((slug, title))
    return result


def choose_page_for_button(text: str, target: str, pages: list[dict[str, Any]], used: set[str], index: int) -> str:
    low = f"{text} {target}".lower()
    available = available_pages(pages)
    slugs = [slug for slug, _ in available]
    cleaned_target = slug_text(target.strip().lstrip("#/"))
    if cleaned_target in slugs and cleaned_target not in used:
        return cleaned_target

    rules = [
        (["услуг", "сервис", "стоим", "цена", "выбрать"], ["service", "services", "uslugi", "услуги", "каталог", "catalog", "menu"]),
        (["работ", "портф", "кейс", "пример"], ["portfolio", "портфолио", "работ", "case"]),
        (["распис", "дат", "время", "программ"], ["schedule", "расписание", "программа", "event"]),
        (["команд", "тренер", "специалист"], ["team", "команда", "тренер", "специалист"]),
        (["о нас", "компан", "подроб", "узнать"], ["about", "о-нас", "onas", "company", "компания"]),
        (["контакт", "связ", "заяв", "запис", "консульт"], ["contacts", "kontakty", "контакты", "contact"]),
        (["faq", "вопрос"], ["faq", "вопрос"]),
    ]
    for button_words, page_words in rules:
        if any(word in low for word in button_words):
            for slug, title in available:
                joined = f"{slug} {title}".lower()
                if slug not in used and any(word in joined for word in page_words):
                    return slug

    for slug, _ in available:
        if slug not in used:
            return slug
    return available[index % len(available)][0] if available else "contacts"

def normalize_buttons(buttons: list[Any], pages: list[dict[str, Any]], phone: str, email: str, goal: str, multipage: bool = False) -> list[dict[str, str]]:
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

        lower = f"{text} {target_raw}".lower()
        if any(word in lower for word in ["позвон", "звон", "телефон", "почт", "email", "mail", "контакт", "связ", "заяв", "запис", "консульт"]):
            if multipage:
                page = choose_page_for_button("контакты", "contacts", pages, used, index)
                used.add(page)
                target = "/" + page if page else "/"
            else:
                target = "#contacts"
        elif multipage:
            page = choose_page_for_button(text, target_raw, pages, used, index)
            used.add(page)
            target = "/" + page if page else "/"
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




def strip_markdown_artifacts(value: Any) -> str:
    text = str(value or "")
    text = text.replace("**", "").replace("__", "").replace("`", "")
    text = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", text)
    text = re.sub(r"^[ \t]*[-*•][ \t]+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[ \t]*\d+[.)][ \t]+", "", text, flags=re.MULTILINE)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def remove_markdown_from_site(site_json: dict[str, Any]) -> None:
    def clean_obj(obj: Any) -> Any:
        if isinstance(obj, str):
            return strip_markdown_artifacts(obj)
        if isinstance(obj, list):
            return [clean_obj(item) for item in obj]
        if isinstance(obj, dict):
            return {key: clean_obj(value) for key, value in obj.items()}
        return obj
    cleaned = clean_obj(site_json)
    site_json.clear()
    site_json.update(cleaned)


BAD_SLOP_PHRASES = [
    "индивидуальный подход", "высокое качество", "профессиональная команда",
    "широкий спектр услуг", "лучшие решения", "современные решения",
    "комплексный подход", "мы ценим каждого клиента", "быстро и качественно",
    "ваш надёжный партнёр", "надежный партнёр", "надежный партнер"
]


def infer_visual_design(description: str = "", design_preferences: str = "", desired_info: str = "") -> dict[str, str]:
    text = f"{description} {design_preferences} {desired_info}".lower()
    if any(w in text for w in ["неон", "кибер", "it", "айти", "технолог", "стартап", "программ", "нейро"]):
        return {"primaryColor": "#07111f", "secondaryColor": "#101a2e", "accentColor": "#38d5ff", "textColor": "#edf7ff", "surfaceColor": "#111b2f", "layoutVariant": "split", "cardStyle": "glass", "heroVisual": "none", "sectionShape": "sharp", "fontFamily": "mono", "density": "normal"}
    if any(w in text for w in ["темн", "чёрн", "черн", "black", "dark"]):
        return {"primaryColor": "#0e0f12", "secondaryColor": "#1b1c22", "accentColor": "#f0b35b", "textColor": "#f7f1e8", "surfaceColor": "#18191f", "layoutVariant": "split", "cardStyle": "outline", "heroVisual": "none", "sectionShape": "sharp", "fontFamily": "sans", "density": "normal"}
    if any(w in text for w in ["кафе", "кофе", "ресторан", "еда", "шаурм", "пекар", "бар"]):
        return {"primaryColor": "#3b2418", "secondaryColor": "#8b5a35", "accentColor": "#f2c078", "textColor": "#fff6e8", "surfaceColor": "#4b2e1f", "layoutVariant": "calm", "cardStyle": "raised", "heroVisual": "none", "sectionShape": "rounded", "fontFamily": "serif", "density": "air"}
    if any(w in text for w in ["салон", "красот", "beauty", "космет", "стилист", "маник", "визаж"]):
        return {"primaryColor": "#fff3f6", "secondaryColor": "#f5d7df", "accentColor": "#a84f68", "textColor": "#2c1820", "surfaceColor": "#ffffff", "layoutVariant": "centered", "cardStyle": "glass", "heroVisual": "none", "sectionShape": "pill", "fontFamily": "display", "density": "air"}
    if any(w in text for w in ["йога", "природ", "эко", "спорт", "фитнес", "здоров", "массаж"]):
        return {"primaryColor": "#eaf2df", "secondaryColor": "#c7d8b6", "accentColor": "#557a46", "textColor": "#172315", "surfaceColor": "#f8fbf2", "layoutVariant": "calm", "cardStyle": "minimal", "heroVisual": "none", "sectionShape": "rounded", "fontFamily": "sans", "density": "air"}
    if any(w in text for w in ["портфолио", "дизайн", "фото", "худож", "архитект", "творч"]):
        return {"primaryColor": "#f2eee7", "secondaryColor": "#d8d0c4", "accentColor": "#111111", "textColor": "#171717", "surfaceColor": "#fffaf1", "layoutVariant": "editorial", "cardStyle": "minimal", "heroVisual": "none", "sectionShape": "asymmetric", "fontFamily": "serif", "density": "air"}
    if any(w in text for w in ["мероприят", "концерт", "фестиваль", "ивент", "событ", "лекци", "форум"]):
        return {"primaryColor": "#ffefe0", "secondaryColor": "#ff7a1a", "accentColor": "#101010", "textColor": "#111111", "surfaceColor": "#fff7ed", "layoutVariant": "editorial", "cardStyle": "outline", "heroVisual": "none", "sectionShape": "sharp", "fontFamily": "display", "density": "compact"}
    return {"primaryColor": "#f3efe7", "secondaryColor": "#ded6c8", "accentColor": "#365f7d", "textColor": "#171b1f", "surfaceColor": "#fffaf2", "layoutVariant": "split", "cardStyle": "solid", "heroVisual": "none", "sectionShape": "rounded", "fontFamily": "sans", "density": "normal"}



def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)

def _rel_luminance(value: str) -> float:
    r, g, b = _hex_to_rgb(value)
    def channel(c: int) -> float:
        x = c / 255
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)

def _contrast(a: str, b: str) -> float:
    la, lb = _rel_luminance(a), _rel_luminance(b)
    high, low = max(la, lb), min(la, lb)
    return (high + 0.05) / (low + 0.05)

def sanitize_design(design: dict[str, Any], inferred: dict[str, str] | None = None) -> dict[str, str]:
    inferred = inferred or infer_visual_design()

    def color(value: Any, fallback: str) -> str:
        value = str(value or "").strip()
        return value if re.fullmatch(r"#[0-9a-fA-F]{6}", value) else fallback

    def enum(value: Any, allowed: set[str], fallback: str) -> str:
        value = str(value or "").strip().lower()
        return value if value in allowed else fallback

    result = {
        "styleName": str(design.get("styleName") or "Индивидуальный стиль")[:80],
        "background": str(design.get("background") or "Фон подобран по проекту")[:220],
        "layoutReason": str(design.get("layoutReason") or "Структура выбрана по описанию пользователя")[:300],
        "primaryColor": color(design.get("primaryColor"), inferred["primaryColor"]),
        "secondaryColor": color(design.get("secondaryColor"), inferred["secondaryColor"]),
        "accentColor": color(design.get("accentColor"), inferred["accentColor"]),
        "textColor": color(design.get("textColor"), inferred["textColor"]),
        "surfaceColor": color(design.get("surfaceColor"), inferred["surfaceColor"]),
        "fontMood": str(design.get("fontMood") or "Чистый современный стиль")[:120],
        "layoutVariant": enum(design.get("layoutVariant"), {"split", "centered", "editorial", "grid", "brutal", "calm"}, inferred["layoutVariant"]),
        "cardStyle": enum(design.get("cardStyle"), {"solid", "outline", "glass", "minimal", "raised"}, inferred["cardStyle"]),
        "heroVisual": "none",
        "sectionShape": enum(design.get("sectionShape"), {"rounded", "sharp", "pill", "asymmetric"}, inferred["sectionShape"]),
        "fontFamily": enum(design.get("fontFamily"), {"serif", "sans", "mono", "display"}, inferred["fontFamily"]),
        "density": enum(design.get("density"), {"air", "normal", "compact"}, inferred["density"]),
    }

    # Если ИИ вернул почти белую палитру без явного запроса на светлый стиль, берём тематическую палитру.
    too_white = result["primaryColor"].lower() in {"#ffffff", "#fffaf3", "#f6efe7", "#f7f7f7"} and result["secondaryColor"].lower() in {"#ffffff", "#fffaf3", "#f6efe7", "#f7f7f7"}
    poor_contrast = _contrast(result["textColor"], result["primaryColor"]) < 3.8 or _contrast(result["textColor"], result["surfaceColor"]) < 3.4
    if too_white or poor_contrast:
        for key in ["primaryColor", "secondaryColor", "accentColor", "textColor", "surfaceColor"]:
            result[key] = inferred[key]
    result["heroVisual"] = "none"
    return result


def is_slop_text(text: str) -> bool:
    low = (text or "").lower()
    return any(phrase in low for phrase in BAD_SLOP_PHRASES)


def reduce_neuro_slop(site_json: dict[str, Any], description: str = "", desired_info: str = "") -> None:
    source = " ".join(x.strip() for x in [description, desired_info] if x and x.strip())
    source = source[:260] if source else "проект пользователя"
    for page in site_json.get("pages", []):
        if not isinstance(page, dict):
            continue
        for section in page.get("sections", []):
            if not isinstance(section, dict):
                continue
            if is_slop_text(str(section.get("description", ""))):
                title = str(section.get("title") or "Раздел")
                section["description"] = f"{title}: здесь указана конкретная информация по запросу пользователя — {source}."
            if is_slop_text(str(section.get("subtitle", ""))):
                section["subtitle"] = source
            items = section.get("items")
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and is_slop_text(str(item.get("description", ""))):
                        item_title = str(item.get("title") or "Пункт")
                        item["description"] = f"{item_title}: пункт связан с запросом пользователя — {source}."



def looks_broken_generated_text(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return True
    low = text.lower()
    if re.search(r"(?:[0-9]п|п[0-9])", low) or re.search(r"п[а-я0-9]{0,2}п[а-я0-9]{0,2}п", low):
        return True
    letters = re.findall(r"[a-zA-Zа-яА-ЯёЁ]", text)
    if len(letters) >= 6:
        p_count = sum(1 for ch in letters if ch.lower() == "п")
        if p_count / len(letters) > 0.45:
            return True
    return "�" in text

def clean_or_default(value: Any, fallback: str) -> str:
    cleaned = strip_markdown_artifacts(value)
    return fallback if looks_broken_generated_text(cleaned) else cleaned

def resolve_site_name(company_name: str | None, description: str, ai_name: Any) -> str:
    company_name = str(company_name or "").strip()
    if company_name and not looks_broken_generated_text(company_name):
        return company_name[:70]

    ai_name = strip_markdown_artifacts(ai_name).strip()
    bad_prefixes = ["описание проекта", "сайт для", "проект", "лендинг", "многостраничный сайт"]
    if ai_name and not looks_broken_generated_text(ai_name) and not any(ai_name.lower().startswith(prefix) for prefix in bad_prefixes):
        return ai_name[:70]

    description = str(description or "").strip()
    quoted = re.findall(r"[«\"]([^«»\"]{2,50})[»\"]", description)
    for candidate in quoted:
        if not looks_broken_generated_text(candidate):
            return candidate.strip()[:70]

    low = description.lower()
    if "нож" in low or "ножи" in low:
        return "Мастерская ножей"
    if "кофе" in low or "кофей" in low:
        return "Кофейня"
    if "йога" in low:
        return "Студия йоги"
    if "теннис" in low:
        return "Теннисный клуб"
    if "ремонт" in low:
        return "Сервисный центр"
    return "Новый сайт"


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
                {"title": "Что предлагает проект", "description": (desired_info or description)[:180]},
                {"title": "Для кого это сделано", "description": "Содержание сайта собирается вокруг аудитории и задачи, которые указаны в описании проекта."},
                {"title": "Как связаться", "description": f"Посетитель может перейти к контактам: {contact_phone}, {contact_email}."},
            ]},
            {"type": "text", "anchorId": "details", "title": text_title, "description": desired_info or description[:260]},
            {"type": "contact", "anchorId": "contacts", "title": "Контакты", "phone": contact_phone, "email": contact_email, "address": "Адрес будет добавлен позже"},
        ],
    }]

    if is_multi:
        pages.append({"title": "Услуги", "slug": "/uslugi", "type": "services", "sections": [{"type": "text", "anchorId": "services-page", "title": "Услуги", "description": desired_info or description[:300]}]})
        pages.append({"title": "Контакты", "slug": "/kontakty", "type": "contacts", "sections": [{"type": "contact", "anchorId": "contacts", "title": "Контакты", "phone": contact_phone, "email": contact_email, "address": "Адрес будет добавлен позже"}]})

    site_json = {
        "siteName": title,
        "siteType": "Многостраничный сайт" if is_multi else "Лендинг",
        "goal": goal,
        "design": {
            "styleName": "Индивидуальный стиль",
            "background": design_preferences or "Фон подобран автоматически",
            "layoutReason": "Блоки расположены по смыслу пользовательского запроса.",
            "primaryColor": "#f6efe7",
            "secondaryColor": "#fffaf3",
            "accentColor": "#7c4a2d",
            "textColor": "#201915",
            "surfaceColor": "#ffffff",
            "fontMood": "Чистый современный стиль",
            "layoutVariant": "calm",
            "cardStyle": "raised",
            "heroVisual": "none",
            "sectionShape": "rounded",
            "fontFamily": "sans",
            "density": "normal",
        },
        "pages": pages,
    }
    return normalize_generated_site(site_json, site_type, contact_email, contact_phone, button_count, company_name, description, design_preferences, desired_info)


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
