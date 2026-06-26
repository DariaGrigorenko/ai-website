import json
import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def generate_site(description, site_type, goal, style):
    try:
        return generate_site_with_openai(description, site_type, goal, style)
    except Exception as error:
        print("AI generation failed. Mock generation used:", error)
        return generate_mock_site(description, site_type, goal, style)


def generate_site_with_openai(description, site_type, goal, style):
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is missing")

    client = OpenAI(api_key=OPENAI_API_KEY)

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
5. Сайт должен выглядеть логично по описанию пользователя.
6. Если данных не хватает, аккуратно дополни нейтральными текстами.
7. Название сайта должно быть коротким и понятным.
"""

    response = client.responses.create(
        model=OPENAI_MODEL,
        input=prompt
    )

    raw_text = response.output_text.strip()

    try:
        site_json = json.loads(raw_text)
    except json.JSONDecodeError:
        start = raw_text.find("{")
        end = raw_text.rfind("}") + 1

        if start == -1 or end <= 0:
            raise ValueError("OpenAI returned invalid JSON")

        site_json = json.loads(raw_text[start:end])

    validate_site_json(site_json)

    return site_json


def generate_mock_site(description, site_type, goal, style):
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
                        "buttonText": "Оставить заявку"
                    },
                    {
                        "type": "features",
                        "title": "Преимущества",
                        "items": [
                            "Быстрое создание сайта",
                            "Современный внешний вид",
                            "Понятная структура"
                        ]
                    },
                    {
                        "type": "text",
                        "title": "О проекте",
                        "description": description
                    },
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


def validate_site_json(site_json):
    if not isinstance(site_json, dict):
        raise ValueError("site_json must be object")

    if not site_json.get("siteName"):
        raise ValueError("siteName is missing")

    if not isinstance(site_json.get("pages"), list):
        raise ValueError("pages must be list")

    if len(site_json["pages"]) == 0:
        raise ValueError("pages must not be empty")


def make_title(description):
    first_line = description.strip().split("\n")[0]
    first_sentence = first_line.split(".")[0].strip()

    if len(first_sentence) < 5:
        return "Сайт для вашего проекта"

    return first_sentence[:60]
