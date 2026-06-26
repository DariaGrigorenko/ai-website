import json
import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def generate_site_with_ai(description, site_type, goal, style):
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY не найден")

    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""
Ты — генератор структуры сайта для сервиса HGGps.

На основе данных пользователя создай JSON сайта.

Данные пользователя:
Описание:
{description}

Тип сайта:
{site_type}

Цель сайта:
{goal}

Стиль:
{style}

Верни строго JSON без markdown и без пояснений.

Формат JSON должен быть таким:
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
          "subtitle": "Краткое описание",
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
1. Не добавляй HTML.
2. Не добавляй CSS.
3. Не добавляй markdown.
4. Верни только валидный JSON.
5. У сайта должна быть минимум одна страница.
6. Если данных мало, аккуратно дополни их нейтральными текстами.
7. Тексты должны быть на русском языке.
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

        if start == -1 or end == 0:
            raise ValueError("Нейросеть вернула не JSON")

        site_json = json.loads(raw_text[start:end])

    validate_site_json(site_json)

    return site_json


def generate_mock_site(description, site_type, goal, style):
    title = make_short_title(description)

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
                            "Понятная структура сайта",
                            "Современный внешний вид",
                            "Быстрый запуск проекта"
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


def generate_site(description, site_type, goal, style):
    try:
        return generate_site_with_ai(description, site_type, goal, style)
    except Exception as error:
        print(f"AI generation failed, mock used: {error}")
        return generate_mock_site(description, site_type, goal, style)


def validate_site_json(site_json):
    if not isinstance(site_json, dict):
        raise ValueError("site_json должен быть объектом")

    if "siteName" not in site_json:
        raise ValueError("Нет siteName")

    if "pages" not in site_json:
        raise ValueError("Нет pages")

    if not isinstance(site_json["pages"], list) or len(site_json["pages"]) == 0:
        raise ValueError("pages должен быть непустым списком")


def make_short_title(description):
    first_line = description.strip().split("\n")[0]
    first_sentence = first_line.split(".")[0].strip()

    if len(first_sentence) < 5:
        return "Сайт для вашего проекта"

    return first_sentence[:60]
