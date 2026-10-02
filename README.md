# Тестовое задание для CityCar

## 1. Архитектура

Запрос руководителя запускает сбор данных за последние 30 дней. Коннектор к amoCRM получает сделки и связанные с ними задачи через API v4. Отдельный коннектор забирает записи и метаданные звонков из телефонии — конкретный API зависит от используемого провайдера.

Звонки переводятся в текст с помощью распознавания речи. Затем система связывает звонок со сделкой и извлекает, например, договорённости и следующий шаг. Если связь или распознавание ненадёжны, материал помечается для проверки. По данным CRM и звонков считаются показатели и готовится черновик отчёта со ссылками на источники.

Отчёты и нужные для анализа данные хранятся в закрытой БД с ограничением доступа и сроком хранения. Аудиозаписи и транскрипты не следует хранить дольше необходимого; доступ к ним журналируется. Интеграция работает только на чтение.

## 2. Что автоматизировать, что оставить человеку

Система может собрать данные, посчитать согласованные показатели, расшифровать звонки и подготовить черновик с примерами из CRM. Руководитель проверяет выводы, спорные звонки и оценки работы менеджеров. Без подтверждения система не меняет сделки и задачи.

Основные риски:
1. **Данные неполные или не связаны между собой.** Показывать покрытие и отмечать случаи, где звонок не удалось уверенно связать со сделкой.
2. **Ошибки распознавания и выводов AI.** Прикладывать к каждому выводу источник и фрагмент разговора; спорное отправлять на ручную проверку.
3. **Конфиденциальность звонков и клиентских данных.** Ограничить доступ, минимизировать передаваемые данные и установить срок удаления вместе с ответственными за безопасность.

## 3. Пример кода для amoCRM

Ниже — сделки, созданные за последние 30 дней, без привязанных задач либо с просроченной незакрытой задачей. Для краткости обработка ошибок API сведена к `raise_for_status()`.

```python
import os, time, requests
BASE = os.environ["AMO_BASE_URL"].rstrip("/")
HEADERS = {"Authorization": f"Bearer {os.environ['AMO_TOKEN']}"}

def pages(path, params=None):
    url = f"{BASE}/api/v4/{path}"
    while url:
        r = requests.get(url, headers=HEADERS, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        yield from data.get("_embedded", {}).get(path, [])
        url = data.get("_links", {}).get("next", {}).get("href")
        params = None

def find_followups(now=None):
    now = int(time.time()) if now is None else now
    leads = list(pages("leads", {"filter[created_at][from]": now-30*86400, "limit": 250}))
    linked = {x["id"]: [] for x in leads}
    for task in pages("tasks", {"limit": 250}):
        lid = task.get("entity_id")
        if task.get("entity_type") == "leads" and lid in linked:
            linked[lid].append(task)
    return [{"id": x["id"], "name": x.get("name"),
             "reason": "no tasks" if not linked[x["id"]] else "overdue task",
             "overdue_task_ids": [t["id"] for t in linked[x["id"]]
                 if not t.get("is_completed") and t.get("complete_till", now) < now]}
            for x in leads if not linked[x["id"]] or any(
                not t.get("is_completed") and t.get("complete_till", now) < now
                for t in linked[x["id"]])]

if __name__ == "__main__":
    for deal in find_followups():
        print(deal)
```

Для запуска нужны `requests`, `AMO_BASE_URL` и OAuth-токен в переменной `AMO_TOKEN`.

## 4. Опыт AI-проекта

В МФО я реализовал AI-систему. Из-за конфиденциальности не могу раскрыть задачу, архитектуру и показатели проекта, но готов рассказать о своей роли в допустимых рамках.

Документация: [API сделок](https://amocrm.ru/developers/content/crm_platform/leads-api) · [API задач](https://amocrm.ru/developers/content/crm_platform/tasks-api).
