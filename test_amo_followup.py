import os
import unittest
from unittest.mock import patch

import requests

with patch.dict(os.environ, AMO_BASE_URL="https://example.amocrm.ru", AMO_TOKEN="test-token"):
    import amo_followup as app


class FollowupTests(unittest.TestCase):
    def test_pagination(self):
        from unittest.mock import Mock
        first = Mock(status_code=200)
        first.json.return_value = {
            "_embedded": {"leads": [{"id": 1}]},
            "_links": {"next": {"href": f"{app.BASE}/api/v4/leads?page=2"}},
        }
        second = Mock(status_code=200)
        second.json.return_value = {"_embedded": {"leads": [{"id": 2}]}}
        with patch.object(app.requests, "get", side_effect=[first, second]) as get:
            self.assertEqual(list(app.pages("leads", {"limit": 250})), [{"id": 1}, {"id": 2}])
            self.assertEqual(get.call_args_list[1].args[0], f"{app.BASE}/api/v4/leads?page=2")
            self.assertIsNone(get.call_args_list[1].kwargs["params"])

    def test_http_error_is_not_treated_as_missing_tasks(self):
        response = requests.Response()
        response.status_code = 403
        with patch.object(app.requests, "get", return_value=response):
            with self.assertRaises(requests.HTTPError):
                list(app.pages("tasks"))

    def test_task_classification(self):
        now = 2000000000
        cases = [
            ([], "no linked tasks", []),
            ([{"id": 10, "is_completed": False, "complete_till": now - 1}], "overdue open task", [10]),
            ([{"id": 10, "is_completed": True, "complete_till": now - 1}], None, []),
            ([{"id": 10, "is_completed": False, "complete_till": now + 1}], None, []),
            ([{"id": 10, "is_completed": False, "complete_till": now}], None, []),
        ]
        for tasks, reason, ids in cases:
            with self.subTest(tasks=tasks):
                tasks = [dict(t, entity_type="leads", entity_id=1) for t in tasks]
                with patch.object(app, "pages", side_effect=[[{"id": 1}], tasks]):
                    result = app.find_followups(now)
                if reason is None:
                    self.assertEqual(result, [])
                else:
                    self.assertEqual(result[0]["reason"], reason)
                    self.assertEqual(result[0]["task_ids"], ids)

    def test_contact_task_does_not_count_as_lead_task(self):
        task = {"id": 10, "entity_type": "contacts", "entity_id": 1,
                "is_completed": False, "complete_till": 1}
        with patch.object(app, "pages", side_effect=[[{"id": 1}], [task]]):
            result = app.find_followups(2000000000)
        self.assertEqual(result[0]["reason"], "no linked tasks")

    def test_empty_response_is_empty_page(self):
        response = requests.Response()
        response.status_code = 204
        response._content = b""
        with patch.object(app.requests, "get", return_value=response):
            self.assertEqual(list(app.pages("tasks")), [])


if __name__ == "__main__":
    unittest.main()
