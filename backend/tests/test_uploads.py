"""Tests for POST /uploads/ — extension/duplicate/parse validation and,
most importantly for multi-file uploads, that one file's failure doesn't
block the files around it and that sequential uploads of overlapping date
ranges dedup correctly.

Classification is stubbed out in every test: it runs in a background thread
against the same fake (non-thread-safe) DB, which would make these tests
flaky for no reason relevant to what they're checking.
"""
import routes.uploads as uploads_module

USER_A = "user-a-id"

ALIPAY_HEADER = [
    "支付宝交易记录明细查询",
    "---------------------------------交易记录明细列表------------------------------------",
    "交易时间,交易分类,交易对方,商品说明,收/支,金额,交易状态",
]
# Includes a realistic title/separator preamble above the header (rows with
# fewer fields than the 7-field header row) — routes/uploads.py's
# `_read_headers` used to run this through `pd.read_csv(header=None)`, which
# raised a ParserError on the ragged preamble; now it scans raw lines
# instead, so this is safe. See test_realistic_gb18030_preamble_is_detected
# below for the fuller real-world shape (metadata block, disclaimer, GB18030).


def _alipay_csv(rows: list) -> bytes:
    """rows: list of (timestamp, merchant, description, amount)."""
    lines = list(ALIPAY_HEADER)
    for ts, merchant, desc, amount in rows:
        lines.append(f"{ts},餐饮美食,{merchant},{desc},支出,{amount:.2f},交易成功")
    return ("\n".join(lines) + "\n").encode("utf-8")


def _headers(make_token, sub=USER_A):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def _no_classification(monkeypatch):
    monkeypatch.setattr(uploads_module, "schedule_classification", lambda request, user_id: None)


def test_rejects_unsupported_extension(client, patch_jwks, make_token, fake_db):
    resp = client.post(
        "/uploads/",
        headers=_headers(make_token),
        files={"file": ("statement.pdf", b"not a csv", "application/pdf")},
    )
    assert resp.status_code == 400
    assert fake_db._tables.get("uploads") is None or fake_db._tables["uploads"].rows == []


def test_duplicate_content_returns_409_and_creates_no_second_row(client, patch_jwks, make_token, fake_db, monkeypatch):
    _no_classification(monkeypatch)
    content = _alipay_csv([("2025-09-01 08:00:00", "McDonalds", "Combo", 38.00)])

    first = client.post(
        "/uploads/", headers=_headers(make_token),
        files={"file": ("a.csv", content, "text/csv")},
    )
    assert first.status_code == 200

    second = client.post(
        "/uploads/", headers=_headers(make_token),
        files={"file": ("a.csv", content, "text/csv")},
    )
    assert second.status_code == 409
    assert "already uploaded" in second.json()["detail"].lower()
    assert len(fake_db._tables["uploads"].rows) == 1


def test_failure_between_successes_does_not_block_later_files(client, patch_jwks, make_token, fake_db, monkeypatch):
    """The direct analogue of the browser's upload queue: A succeeds, a
    re-upload of A 409s, and B (queued right after) still succeeds and its
    transactions land — a mid-batch failure must not affect its neighbors."""
    _no_classification(monkeypatch)
    content_a = _alipay_csv([("2025-09-01 08:00:00", "McDonalds", "Combo", 38.00)])
    content_b = _alipay_csv([("2025-09-05 12:00:00", "Starbucks", "Latte", 30.00)])

    r1 = client.post("/uploads/", headers=_headers(make_token), files={"file": ("a.csv", content_a, "text/csv")})
    r2 = client.post("/uploads/", headers=_headers(make_token), files={"file": ("a.csv", content_a, "text/csv")})
    r3 = client.post("/uploads/", headers=_headers(make_token), files={"file": ("b.csv", content_b, "text/csv")})

    assert [r1.status_code, r2.status_code, r3.status_code] == [200, 409, 200]
    assert r3.json()["rows_imported"] == 1

    merchants = {t["merchant"] for t in fake_db._tables["transactions"].rows}
    assert merchants == {"McDonalds", "Starbucks"}


def test_unparseable_file_marks_upload_failed_and_clears_hash(client, patch_jwks, make_token, fake_db, monkeypatch):
    _no_classification(monkeypatch)
    garbage = b"not,a,real,statement\nfoo,bar,baz,qux\n"

    resp = client.post(
        "/uploads/", headers=_headers(make_token),
        files={"file": ("garbage.csv", garbage, "text/csv")},
    )
    assert resp.status_code == 400

    rows = fake_db._tables["uploads"].rows
    assert len(rows) == 1
    assert rows[0]["status"] == "failed"
    assert rows[0]["file_hash"] is None


def test_overlapping_files_do_not_double_import(client, patch_jwks, make_token, fake_db, monkeypatch):
    """Two files sharing a transaction in their overlapping date range,
    uploaded sequentially. Because they're sequential (not concurrent), the
    second file's dedup query sees the first file's already-committed rows —
    this is the exact guarantee the sequential-upload design relies on."""
    _no_classification(monkeypatch)
    content_1 = _alipay_csv([
        ("2025-09-01 08:00:00", "McDonalds", "Combo", 38.00),
        ("2025-09-02 09:00:00", "Uniqlo", "Shirt", 129.00),
    ])
    content_2 = _alipay_csv([
        ("2025-09-02 09:00:00", "Uniqlo", "Shirt", 129.00),   # duplicate of file 1
        ("2025-09-03 10:00:00", "Starbucks", "Latte", 30.00),  # new
    ])

    r1 = client.post("/uploads/", headers=_headers(make_token), files={"file": ("a.csv", content_1, "text/csv")})
    r2 = client.post("/uploads/", headers=_headers(make_token), files={"file": ("b.csv", content_2, "text/csv")})

    assert r1.status_code == 200 and r1.json()["rows_imported"] == 2
    assert r2.status_code == 200
    assert r2.json()["rows_imported"] == 1
    assert r2.json()["rows_skipped"] == 1

    merchants = [t["merchant"] for t in fake_db._tables["transactions"].rows]
    assert merchants.count("Uniqlo") == 1
    assert set(merchants) == {"McDonalds", "Uniqlo", "Starbucks"}


def test_realistic_gb18030_preamble_is_detected(client, patch_jwks, make_token, fake_db, monkeypatch):
    """Regression test for a real-world Alipay export: GB18030-encoded, with
    the full metadata preamble (title, an "导出信息" block, a numbered
    "特别提示" disclaimer, a second separator line) before the real header —
    previously 400'd as "Could not detect file source" because
    routes/uploads.py's `_read_headers` hardcoded utf-8 and choked on the
    ragged preamble via pd.read_csv(header=None)."""
    _no_classification(monkeypatch)
    lines = [
        "------------------------------------------------------------------------------------",
        "导出信息：",
        "姓名：CHULUUNBOLD CHINSANAA",
        "支付宝账户：chinsanaa0202@gmail.com",
        "起始时间：[2025-08-23 00:00:00]    终止时间：[2026-05-17 23:59:59]",
        "导出交易类型：[全部]",
        "导出时间：[2026-05-27 18:22:56]",
        "共1笔记录",
        "",
        "特别提示：",
        "1.本回单内容可表明支付宝受理了相应支付交易申请。",
        "",
        "------------------------------支付宝支付宝对账单 财付通交易明细------------------------------",
        "交易时间,交易分类,交易对方,对方账号,商品说明,收/支,金额,收/付款方式,交易状态,交易分类,交易订单号,商家订单号,备注",
        "2026-05-16 05:01:31,餐饮美食,麦当劳,chu***@didichuxing.com,巨无霸套餐,支出,38.00,Visa(9272),交易成功,餐饮美食,2026051622001413631401481301\t,212_202605168651457701811533\t,",
    ]
    content = ("\r\n".join(lines) + "\r\n").encode("gb18030")

    resp = client.post(
        "/uploads/", headers=_headers(make_token),
        files={"file": ("alipay_export.csv", content, "text/csv")},
    )

    assert resp.status_code == 200
    assert resp.json()["rows_imported"] == 1
    assert fake_db._tables["transactions"].rows[0]["merchant"] == "麦当劳"
