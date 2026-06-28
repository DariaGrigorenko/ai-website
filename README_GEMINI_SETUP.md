# Настройка Gemini API

1. Получить ключ: https://aistudio.google.com/app/apikey
2. В Render открыть сервис backend.
3. Перейти в Environment.
4. Добавить переменные:

```text
GEMINI_API_KEY=твой_ключ_Gemini
GEMINI_MODEL=gemini-2.5-flash
```

5. Нажать Manual Deploy → Clear build cache & deploy.
6. Проверить backend:

```text
https://ai-website-exwx.onrender.com/
```

Должно быть:

```json
{"status":"ok","service":"HGGps Backend API","aiProvider":"Gemini","message":"Backend работает"}
```

Ключ Gemini нельзя добавлять в GitHub. Он должен быть только в Render Environment Variables.
