import json
import os
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def generate_site(description: str, site_type: str, goal: str, style: str) -> dict[str, Any]:
    try:
        site_json = generate_site_with_gemini(description, site_type, goal, style)
        site_json["_generatedBy"] = "gemini"
        site_json["_aiModel"] = GEMINI_MODEL
        return site_json
    except Exception as error:
        print("Gemini generation failed. Mock generation used:", repr(error))
        site_json = generate_mock_site(description, site_type, goal, style)
        site_json["_generatedBy"] = "mock"
        site_json["_aiError"] = str(error)
        return site_json


def generate_site_with_gemini(description: str, site_type: str, goal: str, style: str) -> dict[str, Any]:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing")

    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""
Ты — генератор сайтов для проекта HGGps.

Пользователь создаёт сайт по этапам:
1. описание проекта;
2. настройка фона;
3. размещение кнопок и блоков;
4. добавление информации;
5. получение финального сайта.

На основе данных пользователя создай структуру сайта в JSON.

Описание пользователя:
{description}

Тип сайта:
{site_type}

Цель сайта:
{goal}

Стиль:
{style}

Верни только валидный JSON без markdown, без пояснений и без HTML.

Формат ответа:
{{
  "siteName": "Название сайта",
  "siteType": "Тип сайта",
  "goal": "Цель сайта",
  "style": "Стиль сайта",
  "pages": [
    {{
      "title": "Главная",
      "slug": "/",
      "type": "home",
      "sections": [
        {{
          "type": "hero",
          "title": "Главный заголовок",
          "subtitle": "Краткое описание сайта",
          "buttonText": "Текст кнопки"
        }},
        {{
          "type": "features",
          "title": "Преимущества",
          "items": [
            "Преимущество 1",
            "Преимущество 2",
            "Преимущество 3"
          ]
        }},
        {{
          "type": "text",
          "title": "О проекте",
          "description": "Описание проекта"
        }},
        {{
          "type": "contact",
          "title": "Контакты",
          "phone": "+7 000 000-00-00",
          "email": "example@email.com",
          "address": "Адрес будет добавлен позже"
        }}
      ]
    }}
  ]
}}

Правила:
1. Все тексты должны быть на русском языке.
2. Не используй HTML.
3. Не используй CSS.
4. Не добавляй markdown.
5. Сайт должен соответствовать описанию пользователя.
6. Если данных не хватает, аккуратно дополни нейтральными текстами.
7. Название сайта должно быть коротким и понятным.
8. Не начинай название сайта со слов "Описание проекта".
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.7,
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

    validate_site_json(site_json)
    return site_json


def generate_mock_site(description: str, site_type: str, goal: str, style: str) -> dict[str, Any]:
    title = make_title(description)

    return {
        "siteName": title,
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
                        "title": title,
                        "subtitle": description[:350],
                        "buttonText": "Оставить заявку",
                    },
                    {
                        "type": "features",
                        "title": "Преимущества",
                        "items": [
                            "Быстрое создание сайта",
                            "Современный внешний вид",
                            "Понятная структура",
                        ],
                    },
                    {
                        "type": "text",
                        "title": "О проекте",
                        "description": description,
                    },
                    {
                        "type": "contact",
                        "title": "Контакты",
                        "phone": "+7 000 000-00-00",
                        "email": "example@email.com",
                        "address": "Адрес будет добавлен позже",
                    },
                ],
            }
        ],
    }


def validate_site_json(site_json: dict[str, Any]) -> None:
    if not isinstance(site_json, dict):
        raise ValueError("site_json must be object")

    if not site_json.get("siteName"):
        raise ValueError("siteName is missing")

    if not isinstance(site_json.get("pages"), list):
        raise ValueError("pages must be list")

    if len(site_json["pages"]) == 0:
        raise ValueError("pages must not be empty")


def make_title(description: str) -> str:
    clean = description.replace("Описание проекта:", "").strip()
    first_line = clean.split("\n")[0]
    first_sentence = first_line.split(".")[0].strip()

    if len(first_sentence) < 5:
        return "Сайт для вашего проекта"

    return first_sentence[:60]
