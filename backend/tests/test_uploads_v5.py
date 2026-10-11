"""POST /uploads/ under API v5 (contract §1.4, §3.9): kinds persisted,
bank statements, rows_by_kind, FX trigger, and re-import over parser-v1 rows.

All data is synthetic (tests/fixtures/statements/ at the repo root).
fake_supabase.py is used as-is (no extensions needed).
"""
import hashlib
import sys
import types
from pathlib import Path

import pytest

import routes.uploads as uploads_module

USER = "user-v5-id"
FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "statements"
UNDETECTED = "Could not detect file source. Expected an Alipay, WeChat or bank statement export."


@pytest.fixture(autouse=True)
def fx_calls(monkeypatch):
    """Stub the FX module (B3's backend/fx.py) and record backfill requests."""
    calls = []
    stub = types.ModuleType("fx")
    stub.request_backfill_for_user = lambda user_id, start=None: calls.append((user_id, start))
    monkeypatch.setitem(sys.modules, "fx", stub)
    monkeypatch.setattr(uploads_module, "schedule_classification", lambda request, user_id: None)
    # The 20/hour upload limit is a process-wide in-memory counter; this file
    # alone makes more than 20 uploads, so start each test from zero.
    from limiter import limiter
    limiter.reset()
    return calls


def _headers(make_token):
    return {"Authorization": f"Bearer {make_token(sub=USER)}"}


def _post(client, make_token, name, content):
    mime = "text/csv" if name.endswith(".csv") else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return client.post("/uploads/", headers=_headers(make_token), files={"file": (name, content, mime)})


def _txns(fake_db):
    t = fake_db._tables.get("transactions")
    return t.rows if t else []


def _by_merchant(fake_db, merchant):
    return [r for r in _txns(fake_db) if r["merchant"] == merchant]


# ---------------------------------------------------------------------------
# Ordinary uploads
# ---------------------------------------------------------------------------

def test_upload_persists_kinds_and_non_expense_defaults(client, patch_jwks, make_token, fake_db, fx_calls):
    content = (FIXTURES / "alipay_cn.csv").read_bytes()
    resp = _post(client, make_token, "alipay.csv", content)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["rows_imported"] == 19
    assert body["rows_by_kind"] == {"expense": 6, "income": 3, "transfer": 10}
    assert body["rows_updated"] == 0 and body["rows_removed"] == 0 and body["reimported"] is False
    assert body["message"] == "Imported 19 transactions (3 income, 10 transfers). Categorization is running."

    rows = _txns(fake_db)
    for r in rows:
        assert r["source"] == "alipay"
        if r["kind"] == "expense":
            assert r["needs_review"] is True
        else:
            assert r["needs_review"] is False
            assert r["category_id"] is None
            assert r["label_source"] == "none"
            assert r["confidence"] is None
    salary = _by_merchant(fake_db, "示例科技有限公司")   # "Example Tech Co."
    assert [(r["kind"], r["flow_subtype"], r["amount"]) for r in salary] == [("income", "salary", 15000.0)]
    refund = [r for r in _by_merchant(fake_db, "淘宝店铺A") if r["amount"] < 0]   # Taobao shop A
    assert [(r["kind"], r["flow_subtype"]) for r in refund] == [("expense", "refund")]

    upload = fake_db._tables["uploads"].rows[0]
    assert upload["parser_version"] == 2
    assert upload["file_type"] == "alipay"

    # FX backfill requested from the earliest uploaded row's date.
    assert len(fx_calls) == 1
    assert fx_calls[0][0] == USER and str(fx_calls[0][1]) == "2025-09-01"


def test_bank_upload_detected_and_stored_as_bank(client, patch_jwks, make_token, fake_db):
    resp = _post(client, make_token, "statement.csv", (FIXTURES / "bank_direction.csv").read_bytes())
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["file_type"] == "bank"
    assert body["rows_by_kind"] == {"expense": 1, "income": 2, "transfer": 3}
    assert {r["source"] for r in _txns(fake_db)} == {"bank"}
    wallet = _by_merchant(fake_db, "支付宝(中国)网络技术有限公司")   # Alipay (China) Network Technology
    assert [(r["kind"], r["flow_subtype"]) for r in wallet] == [("transfer", "own_account")]


def test_bank_xlsx_upload(client, patch_jwks, make_token, fake_db, tmp_path):
    import pandas as pd

    xlsx = tmp_path / "bank.xlsx"
    pd.read_csv(FIXTURES / "bank_debit_credit.csv").to_excel(xlsx, index=False)
    resp = _post(client, make_token, "bank.xlsx", xlsx.read_bytes())
    assert resp.status_code == 200, resp.text
    assert resp.json()["file_type"] == "bank"
    assert resp.json()["rows_imported"] == 5


def test_undetectable_file_400_with_contract_message(client, patch_jwks, make_token, fake_db, fx_calls):
    resp = _post(client, make_token, "garbage.csv", b"not,a,real,statement\nfoo,bar,baz,qux\n")
    assert resp.status_code == 400
    assert resp.json()["detail"] == UNDETECTED
    assert fake_db._tables["uploads"].rows[0]["status"] == "failed"
    assert fx_calls == []


def test_v2_hash_match_still_409(client, patch_jwks, make_token, fake_db):
    content = (FIXTURES / "wechat_cn.csv").read_bytes()
    assert _post(client, make_token, "w.csv", content).status_code == 200
    second = _post(client, make_token, "w.csv", content)
    assert second.status_code == 409
    assert len(fake_db._tables["uploads"].rows) == 1


def test_fx_module_missing_does_not_break_upload(client, patch_jwks, make_token, fake_db, monkeypatch):
    monkeypatch.setitem(sys.modules, "fx", None)   # import fx -> ImportError
    resp = _post(client, make_token, "a.csv", (FIXTURES / "alipay_cn.csv").read_bytes())
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Re-import over parser-v1 data
# ---------------------------------------------------------------------------

def _seed_upload(fake_db, upload_id, file_type, file_hash="h-other", parser_version=1):
    fake_db.seed("uploads", [{
        "id": upload_id, "user_id": USER, "original_filename": f"{upload_id}.csv",
        "file_type": file_type, "status": "parsed", "file_hash": file_hash,
        "parser_version": parser_version, "row_count": 0, "created_at": "2025-10-01T00:00:00+00:00",
    }])


def _v1_row(row_id, upload_id, source, ts, merchant, description, amount, **extra):
    row = {
        "id": row_id, "user_id": USER, "upload_id": upload_id, "source": source,
        "timestamp": ts, "merchant": merchant, "description": description, "amount": amount,
        "kind": "expense", "flow_subtype": "refund" if amount < 0 else None,
        "category_id": None, "label_source": "none", "needs_review": True,
        "is_manually_labeled": False, "is_split": False, "confidence": None,
    }
    row.update(extra)
    return row


def _seed_wechat_v1(fake_db, file_hash):
    """What the v1 parser stored for wechat_cn.csv, plus one phantom row."""
    _seed_upload(fake_db, "up-w1", "wechat", file_hash=file_hash)
    fake_db.seed("transactions", [
        # 美团 Meituan, labeled by the user — identical in v2, must stay untouched
        _v1_row("t-meituan", "up-w1", "wechat", "2025-09-01T08:00:00", "美团", "外卖订单", 45.0,
                category_id="cat-food", label_source="manual", is_manually_labeled=True, needs_review=False),
        _v1_row("t-store", "up-w1", "wechat", "2025-09-02T12:00:00+00:00", "便利店", "/", 12.5),   # convenience store
        # 京东 JD: v1 negated the whole partially refunded purchase (-100); v2 says 70
        _v1_row("t-jd", "up-w1", "wechat", "2025-09-03T18:00:00", "京东", "耳机", -100.0,
                category_id="cat-elec", label_source="manual", is_manually_labeled=True, needs_review=False),
        # 拼多多 Pinduoduo: original fully refunded (-60 in v1, +60 in v2) + its refund row (-60 both)
        _v1_row("t-pdd", "up-w1", "wechat", "2025-09-04T18:00:00", "拼多多", "T恤", -60.0),
        _v1_row("t-pdd-r", "up-w1", "wechat", "2025-09-05T09:00:00", "拼多多", "退款", -60.0),
        # 王五 Wang Wu red packet sent: v1 kept it as an (even split) expense
        _v1_row("t-red", "up-w1", "wechat", "2025-09-08T10:00:00", "王五", "/", 8.88,
                is_split=True, label_source="manual"),
        # A row v1 kept that the statement no longer contains
        _v1_row("t-ghost", "up-w1", "wechat", "2025-09-10T12:00:00", "幽灵商户", "/", 9.99),   # "ghost merchant"
    ])
    fake_db.seed("transaction_splits", [
        {"id": "s1", "user_id": USER, "transaction_id": "t-red", "category_id": "cat-a", "amount": 4.44},
        {"id": "s2", "user_id": USER, "transaction_id": "t-red", "category_id": "cat-b", "amount": 4.44},
    ])


def test_reimport_hash_match_on_v1_upload(client, patch_jwks, make_token, fake_db):
    content = (FIXTURES / "wechat_cn.csv").read_bytes()
    _seed_wechat_v1(fake_db, hashlib.sha256(content).hexdigest())

    resp = _post(client, make_token, "wechat.csv", content)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["reimported"] is True
    assert body["upload_id"] == "up-w1"
    assert body["rows_updated"] == 3      # JD amount, Pinduoduo amount, Wang Wu -> transfer
    assert body["rows_removed"] == 1      # ghost row
    assert body["rows_imported"] == 10
    assert body["rows_by_kind"] == {"expense": 0, "income": 1, "transfer": 9}
    assert "Updated 3 and removed 1 earlier transactions from this statement." in body["message"]

    rows = {r["id"]: r for r in _txns(fake_db)}
    # Identical labeled row untouched.
    assert rows["t-meituan"]["category_id"] == "cat-food" and rows["t-meituan"]["label_source"] == "manual"
    # Amount updated in place, labels kept, refund subtype cleared.
    jd = rows["t-jd"]
    assert (jd["amount"], jd["flow_subtype"], jd["category_id"], jd["label_source"], jd["is_manually_labeled"]) == \
        (70.0, None, "cat-elec", "manual", True)
    assert (rows["t-pdd"]["amount"], rows["t-pdd"]["flow_subtype"]) == (60.0, None)
    assert rows["t-pdd-r"]["amount"] == -60.0
    # Converted to a transfer with the non-expense defaults; splits removed.
    red = rows["t-red"]
    assert (red["kind"], red["flow_subtype"], red["category_id"], red["needs_review"],
            red["label_source"], red["is_split"], red["confidence"]) == \
        ("transfer", "red_packet", None, False, "none", False, None)
    assert fake_db._tables["transaction_splits"].rows == []
    # Phantom row deleted.
    assert "t-ghost" not in rows

    # No second uploads row; new rows inserted under the existing upload.
    uploads = fake_db._tables["uploads"].rows
    assert len(uploads) == 1
    assert uploads[0]["parser_version"] == 2           # fully covered
    assert uploads[0]["row_count"] == 16
    assert all(r["upload_id"] == "up-w1" for r in _txns(fake_db))
    assert len(_by_merchant(fake_db, "张三")) == 1      # Zhang San transfer inserted once

    # Uploading the same bytes again now 409s (it's a v2 upload).
    assert _post(client, make_token, "wechat.csv", content).status_code == 409


def _seed_alipay_v1(fake_db, with_old_row: bool):
    _seed_upload(fake_db, "up-a1", "alipay")
    rows = [
        _v1_row("a-mcd", "up-a1", "alipay", "2025-09-01T08:00:00", "麦当劳", "巨无霸套餐", 38.0),   # McDonald's Big Mac meal
        _v1_row("a-sbx", "up-a1", "alipay", "2025-09-06T13:00:00", "星巴克", "拿铁", 32.0),        # Starbucks latte: closed, unpaid
    ]
    if with_old_row:
        rows.append(_v1_row("a-old", "up-a1", "alipay", "2025-08-15T09:00:00", "旧商户", "旧订单", 10.0))   # "old merchant", "old order"
    fake_db.seed("transactions", rows)


def test_reimport_partial_coverage_keeps_parser_version_1(client, patch_jwks, make_token, fake_db):
    _seed_alipay_v1(fake_db, with_old_row=True)
    resp = _post(client, make_token, "alipay.csv", (FIXTURES / "alipay_cn.csv").read_bytes())
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["reimported"] is True
    assert body["rows_removed"] == 1          # closed, unpaid Starbucks order
    assert body["rows_updated"] == 0          # McDonald's identical
    assert body["rows_imported"] == 18        # everything else in the file
    ids = {r["id"] for r in _txns(fake_db)}
    assert "a-sbx" not in ids and "a-mcd" in ids and "a-old" in ids
    assert len(_by_merchant(fake_db, "麦当劳")) == 1
    v1 = next(u for u in fake_db._tables["uploads"].rows if u["id"] == "up-a1")
    assert v1["parser_version"] == 1          # the 2025-08-15 row is outside the file's window
    new = next(u for u in fake_db._tables["uploads"].rows if u["id"] != "up-a1")
    assert new["parser_version"] == 2


def test_reimport_full_coverage_sets_parser_version_2(client, patch_jwks, make_token, fake_db):
    _seed_alipay_v1(fake_db, with_old_row=False)
    resp = _post(client, make_token, "alipay.csv", (FIXTURES / "alipay_cn.csv").read_bytes())
    assert resp.status_code == 200, resp.text
    v1 = next(u for u in fake_db._tables["uploads"].rows if u["id"] == "up-a1")
    assert v1["parser_version"] == 2


def test_reimport_filtered_export_skips_deletions(client, patch_jwks, make_token, fake_db):
    _seed_alipay_v1(fake_db, with_old_row=False)
    text = (FIXTURES / "alipay_cn.csv").read_text(encoding="utf-8")
    # 导出交易类型：[支出] = "export transaction type: [expense]" (user filtered before export)
    filtered = text.replace("导出交易类型：[全部]", "导出交易类型：[支出]").encode("utf-8")
    resp = _post(client, make_token, "alipay_filtered.csv", filtered)
    assert resp.status_code == 200, resp.text
    assert resp.json()["reimported"] is True
    assert resp.json()["rows_removed"] == 0
    assert "a-sbx" in {r["id"] for r in _txns(fake_db)}
    # Deletions were skipped, so the v1 upload must NOT be marked reconciled:
    # a later full export still gets to remove what v1 wrongly kept.
    v1 = next(u for u in fake_db._tables["uploads"].rows if u["id"] == "up-a1")
    assert v1["parser_version"] == 1


def test_reimport_ignores_other_source_and_v2_uploads(client, patch_jwks, make_token, fake_db):
    # A v1 WeChat upload and a v2 Alipay upload in the same window: neither
    # triggers an Alipay re-import.
    _seed_upload(fake_db, "up-w", "wechat")
    _seed_upload(fake_db, "up-a2", "alipay", parser_version=2)
    fake_db.seed("transactions", [
        _v1_row("w-1", "up-w", "wechat", "2025-09-06T13:00:00", "星巴克", "拿铁", 32.0),
        _v1_row("a2-1", "up-a2", "alipay", "2025-09-06T13:00:00", "星巴克", "拿铁", 32.0),
    ])
    resp = _post(client, make_token, "alipay.csv", (FIXTURES / "alipay_cn.csv").read_bytes())
    assert resp.status_code == 200, resp.text
    assert resp.json()["reimported"] is False
    assert {"w-1", "a2-1"} <= {r["id"] for r in _txns(fake_db)}
