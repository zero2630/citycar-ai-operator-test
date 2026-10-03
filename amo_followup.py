"""Find recent amoCRM leads with no linked tasks or overdue open tasks.
Set AMO_BASE_URL=https://<account>.amocrm.ru and AMO_TOKEN before running.
"""
import os
import time
import requests

BASE = os.environ["AMO_BASE_URL"].rstrip("/")
HEADERS = {"Authorization": f"Bearer {os.environ['AMO_TOKEN']}"}


def pages(path, params=None):
    url = f"{BASE}/api/v4/{path}"
    while url:
        response = requests.get(url, headers=HEADERS, params=params, timeout=30)
        response.raise_for_status()
        if response.status_code == 204:
            return
        data = response.json()
        yield from data.get("_embedded", {}).get(path, [])
        url = data.get("_links", {}).get("next", {}).get("href")
        params = None


def find_followups(now=None):
    now = int(time.time()) if now is None else now
    since = now - 30 * 24 * 60 * 60
    leads = list(pages("leads", {"filter[created_at][from]": since, "limit": 250}))
    lead_ids = {lead["id"] for lead in leads}
    linked = {lead_id: [] for lead_id in lead_ids}
    for task in pages("tasks", {"limit": 250}):
        lead_id = task.get("entity_id")
        if task.get("entity_type") == "leads" and lead_id in linked:
            linked[lead_id].append(task)
    result = []
    for lead in leads:
        tasks = linked[lead["id"]]
        overdue = [t for t in tasks if not t.get("is_completed") and t.get("complete_till", now) < now]
        if not tasks or overdue:
            result.append({"id": lead["id"], "name": lead.get("name"),
                           "reason": "no linked tasks" if not tasks else "overdue open task",
                           "task_ids": [t["id"] for t in overdue]})
    return result


if __name__ == "__main__":
    for row in find_followups():
        print(row)
