def build_sitemap_prompt(description: str, site_type: str, goal: str, style: str) -> str:
    valid_site_types = {"landing", "multi_page"}
    if site_type not in valid_site_types:
        raise ValueError(f"site_type должен быть одним из: {valid_site_types}")
    
    json_template = """
{
  "siteName": "Название сайта",
  "siteType": "landing или multi_page",
  "goal": "Цель сайта",
  "style": "Стиль сайта",
  "pages": [
    {
      "title": "Главная",
      "slug": "/",
      "type": "home",
      "purpose": "Зачем нужна эта страница",
      "recommendedSections": ["hero", "features", "services", "cta"]
    }
  ]
}"""
    
    prompt = f"""Ты — AI website planner для сервиса HGGps.

Твоя задача — создать карту сайта по описанию пользователя.

Данные пользователя:
Описание сайта: {description}
Тип сайта: {site_type}
Цель сайта: {goal}
Стиль сайта: {style}

Правила:
1. Верни только JSON.
2. Не добавляй пояснения вне JSON.
3. Не используй HTML или CSS.
4. Если тип сайта landing, создай только одну страницу.
5. Если тип сайта multi_page, создай от 2 до 5 страниц.
6. Используй только эти типы страниц:
home, about, services, portfolio, team, faq, contact, catalog, schedule.
7. Главная страница всегда должна иметь slug "/".
8. Slug должен быть на английском языке.
9. recommendedSections должны содержать только эти типы блоков:
hero, features, services, text, team, portfolio, faq, contact, cta, schedule, catalog, testimonials.

Формат ответа:
{json_template}"""
    
    return prompt
