"""GET /dashboard/export: split transactions render a "Split (n)" category
column instead of a category name, in the xlsx build."""
from io import BytesIO
from openpyxl import load_workbook

USER_A = "user-a-id"


def _headers(make_token, sub=USER_A):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def test_export_renders_split_count_for_split_transactions(client, patch_jwks, make_token, fake_db):
    fake_db.seed("categories", [
        {"id": "cat-1", "user_id": USER_A, "name": "Groceries"},
        {"id": "cat-2", "user_id": USER_A, "name": "Household"},
    ])
    fake_db.seed("transactions", [
        {"id": "t1", "user_id": USER_A, "merchant": "Costco", "description": "",
         "amount": 120.0, "timestamp": "2026-06-01T00:00:00", "category_id": None,
         "categories": None, "is_split": True, "label_source": "override"},
        {"id": "t2", "user_id": USER_A, "merchant": "Cafe", "description": "",
         "amount": 15.0, "timestamp": "2026-06-01T00:00:00", "category_id": "cat-1",
         "categories": {"name": "Groceries"}, "is_split": False, "label_source": "rule"},
    ])
    fake_db.seed("transaction_splits", [
        {"id": "s1", "user_id": USER_A, "transaction_id": "t1", "category_id": "cat-1", "amount": 80.0},
        {"id": "s2", "user_id": USER_A, "transaction_id": "t1", "category_id": "cat-2", "amount": 40.0},
    ])

    response = client.get("/dashboard/export", headers=_headers(make_token))

    assert response.status_code == 200
    wb = load_workbook(BytesIO(response.content))
    ws = wb.active
    rows_by_merchant = {row[1]: row for row in ws.iter_rows(min_row=2, values_only=True)}
    assert rows_by_merchant["Costco"][3] == "Split (2)"
    assert rows_by_merchant["Cafe"][3] == "Groceries"
