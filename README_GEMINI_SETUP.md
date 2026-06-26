# HGGps: запуск backend через Gemini API

## Что изменено

Проект переведён с OpenAI API на Gemini API.

Frontend остаётся на GitHub Pages и отправляет запросы на Render:

```js
const API_URL = "https://ai-website-exwx.onrender.com";
```

Backend работает на FastAPI и обращается к Gemini через официальный пакет `google-genai`.

## Render Environment Variables

В Render нужно добавить:

```text
GEMINI_API_KEY=ваш_ключ_Gemini
GEMINI_MODEL=gemini-2.5-flash
```

Старые переменные OpenAI можно оставить, но они больше не используются.

## Render настройки

```text
Root Directory: backend
Build Command: pip install -r requirements.txt
Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
```

## Проверка

Backend:

```text
https://ai-website-exwx.onrender.com/
```

Должен вернуть JSON с `aiProvider: Gemini`.

Frontend:

```text
https://dariagrigorenko.github.io/ai-website/#create
```

После создания сайта в блоке ссылки будет видно:

```text
Генерация: gemini / gemini-2.5-flash
```

Если будет `mock`, значит Gemini не сработал. Причину можно смотреть в Render Logs и в API:

```text
https://ai-website-exwx.onrender.com/api/public/slug-сайта
```
