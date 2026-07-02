"""Export combined Alipay + WeChat transactions to English Excel."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import EXPORTS, TRANSACTIONS_CLASSIFIED
from translate import has_cjk, merchant_label_english

SOURCE_LABELS = {
    "alipay": "Alipay",
    "wechat": "WeChat",
}

EXPORT_COLUMNS = [
    ("timestamp", "Date & Time"),
    ("merchant_en", "Merchant"),
    ("description_en", "Description"),
    ("amount", "Amount (CNY)"),
    ("source_en", "Source"),
    ("category", "Category"),
    ("confidence", "Confidence"),
    ("needs_review", "Needs Review"),
]


# Common Alipay/WeChat export description phrases (avoid slow per-row API calls).
DESCRIPTION_SHORTCUTS: list[tuple[str, str]] = [
    ("POS机扫微信二维码消费", "WeChat Pay POS purchase"),
    ("POS机扫支付宝二维码消费", "Alipay POS purchase"),
    ("上海地铁", "Shanghai Metro ride"),
    ("滴滴快车", "DiDi ride"),
    ("滴滴出行", "DiDi ride"),
]


def english_description(description: str, merchant_en: str = "") -> str:
    text = str(description or "").strip()
    if not text or text == "/":
        return ""
    for pattern, label in DESCRIPTION_SHORTCUTS:
        if pattern in text:
            return label
    if not has_cjk(text):
        return text[:120]
    # Chinese payment boilerplate — merchant label is enough for English export.
    if merchant_en:
        return f"{merchant_en} payment"
    return "Payment record"


def build_english_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Map classified transactions to English-only display columns."""
    out = df.copy()

    merchants = out["merchant"].dropna().astype(str).unique()
    merchant_map = {m: merchant_label_english(m) for m in merchants}
    out["merchant_en"] = out["merchant"].astype(str).map(merchant_map)
    out["description_en"] = out.apply(
        lambda r: english_description(r["description"], merchant_map.get(str(r["merchant"]), "")),
        axis=1,
    )

    out["source_en"] = out["source"].map(
        lambda s: SOURCE_LABELS.get(str(s).strip().lower(), str(s).title())
    )
    if "confidence" in out.columns:
        out["confidence"] = pd.to_numeric(out["confidence"], errors="coerce").round(3)
    cols = [src for src, _ in EXPORT_COLUMNS if src in out.columns]
    renamed = {src: label for src, label in EXPORT_COLUMNS if src in out.columns}
    return out[cols].rename(columns=renamed).sort_values("Date & Time", ascending=False)


def export_combined_xlsx(
    classified_path: Path | None = None,
    output_path: Path | None = None,
) -> Path:
    """Write English Excel export; returns output path."""
    classified_path = classified_path or TRANSACTIONS_CLASSIFIED
    output_path = output_path or (EXPORTS / "transactions_combined_en.xlsx")

    if not classified_path.exists():
        raise FileNotFoundError(
            f"No classified data at {classified_path}. Run bootstrap.py or classify.py first."
        )

    df = pd.read_csv(classified_path)
    english = build_english_dataframe(df)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        english.to_excel(writer, sheet_name="All Transactions", index=False)
        summary = (
            english.groupby("Category", as_index=False)
            .agg(Transactions=("Amount (CNY)", "count"), Total=("Amount (CNY)", "sum"))
            .sort_values("Total", ascending=False)
        )
        summary["Total"] = summary["Total"].round(2)
        summary.to_excel(writer, sheet_name="By Category", index=False)
        by_source = (
            english.groupby("Source", as_index=False)
            .agg(Transactions=("Amount (CNY)", "count"), Total=("Amount (CNY)", "sum"))
            .sort_values("Total", ascending=False)
        )
        by_source["Total"] = by_source["Total"].round(2)
        by_source.to_excel(writer, sheet_name="By Source", index=False)

    return output_path


if __name__ == "__main__":
    path = export_combined_xlsx()
    df = pd.read_excel(path, sheet_name="All Transactions")
    print(f"Wrote {len(df)} rows to {path}")
    print(df["Source"].value_counts().to_string())
