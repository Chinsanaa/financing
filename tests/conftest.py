"""Shared fixtures. All data here is SYNTHETIC — no personal transactions."""
import sys
from pathlib import Path
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def _write_alipay_native(path: Path, encoding: str) -> Path:
    """Write a minimal native-Chinese Alipay export with a header preamble.

    Includes: a normal expense, a refund (退款), an internal transfer
    (信用卡还款, must be excluded), and an income row (收入, not an expense).
    """
    rows = [
        "支付宝交易记录明细查询",
        "---------------------------------交易记录明细列表------------------------------------",
        "交易时间,交易分类,交易对方,商品说明,收/支,金额,交易状态",
        "2025-09-01 08:00:00,餐饮美食,麦当劳,巨无霸套餐,支出,38.00,交易成功",
        "2025-09-02 09:00:00,退款,淘宝店铺,退货退款,支出,20.00,退款成功",
        "2025-09-03 10:00:00,信用卡还款,招商银行,信用卡还款,支出,500.00,交易成功",
        "2025-09-04 11:00:00,收入,张三,转账,收入,100.00,交易成功",
    ]
    path.write_text("\n".join(rows) + "\n", encoding=encoding)
    return path


@pytest.fixture
def alipay_native_utf8(tmp_path):
    return _write_alipay_native(tmp_path / "alipay_utf8.csv", "utf-8-sig")


@pytest.fixture
def alipay_native_gbk(tmp_path):
    return _write_alipay_native(tmp_path / "alipay_gbk.csv", "gbk")


@pytest.fixture
def generic_bank_csv(tmp_path):
    """A generic bank CSV with English aliases, an income row, and a zero row."""
    path = tmp_path / "bank.csv"
    df = pd.DataFrame({
        "Transaction Date": ["2025-09-01", "2025-09-02", "2025-09-03"],
        "Merchant": ["Starbucks", "Salary Corp", "Metro"],
        "Product Description": ["Latte", "Monthly pay", "Subway"],
        "Amount": [30.0, 5000.0, 4.0],
        "Type": ["Expense", "Income", "Expense"],
    })
    df.to_csv(path, index=False, encoding="utf-8")
    return path


@pytest.fixture
def synthetic_labeled():
    """A small, class-balanced labeled frame with MULTIPLE merchants per class.

    Deliberately multi-merchant so GroupKFold can actually hold out whole
    merchants — mirrors the real schema (merchant, description, category).
    """
    recs = []
    plan = {
        "Eating Out": ["McDonalds", "KFC", "Starbucks", "BurgerKing", "Subway", "PizzaHut"],
        "Groceries": ["Aldi", "Walmart", "FamilyMart", "Carrefour", "SevenEleven", "Lawson"],
        "Transportation": ["DiDi", "Metro", "HelloBike", "Uber", "Taxiabc", "BusCard"],
        "Shopping": ["Taobao", "JD", "Ugreen", "Nike", "Uniqlo", "Muji"],
    }
    for cat, merchants in plan.items():
        for m in merchants:
            for i in range(4):  # 4 rows per merchant
                recs.append({
                    "merchant": m,
                    "description": f"{m} purchase {i}",
                    "amount": 10.0 + i,
                    "category": cat,
                    "labeled": True,
                })
    return pd.DataFrame(recs)
