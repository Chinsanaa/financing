"""
Short English display names for common merchants (charts & tables).
Falls back to the original name when no mapping exists.
"""
import math

# National chains and generic patterns only — no user-specific merchants
EXACT_NAMES: dict[str, str] = {
    "美团": "Meituan",
    "美团平台商户": "Meituan",
    "滴滴出行": "DiDi",
    "淘宝平台商户": "Taobao",
    "淘宝闪购": "Taobao Flash",
    "喜士多": "C-Store",
    "高德打车": "Amap",
    "麦当劳": "McDonald's",
    "全家": "FamilyMart",
    "萨莉亚": "Saizeriya",
    "无印良品MUJI": "MUJI",
    "春秋航空": "Spring Airlines",
    "上海地铁": "Shanghai Metro",
    "上海申通地铁资产经营管理有限公司": "Shanghai Metro",
    "哈啰出行": "HelloBike",
    "拼多多": "Pinduoduo",
    "拼多多平台商户": "Pinduoduo",
    "喜茶": "HEYTEA",
    "霸王茶姬": "CHAGEE",
    "蜜雪冰城": "Mixue",
    "达美乐": "Domino's",
    "必胜客": "Pizza Hut",
    "名创优品": "MINISO",
    "中国移动": "China Mobile",
    "中石化上海": "Sinopec",
    "上海公共交通卡股份有限公司": "Shanghai Transit Card",
    "luckin coffee": "Luckin Coffee",
    "SUBWAY": "Subway",
    "POPEYES": "Popeyes",
    "LAWSON": "Lawson",
}

SUBSTRING_RULES: list[tuple[str, str]] = [
    ("淘宝闪购", "Taobao Flash"),
    ("淘宝", "Taobao"),
    ("美团", "Meituan"),
    ("滴滴", "DiDi"),
    ("高德", "Amap"),
    ("哈啰", "HelloBike"),
    ("喜士多", "C-Store"),
    ("无印良品", "MUJI"),
    ("蜜雪冰城", "Mixue"),
    ("汉堡王", "Burger King"),
    ("萨莉亚", "Saizeriya"),
    ("麦当劳", "McDonald's"),
    ("全家", "FamilyMart"),
    ("7-ELEVEN", "7-ELEVEN"),
    ("7-11", "7-ELEVEN"),
    ("拼多多", "Pinduoduo"),
    ("名创优品", "MINISO"),
    ("春秋航空", "Spring Airlines"),
    ("申通地铁", "Shanghai Metro"),
    ("上海地铁", "Shanghai Metro"),
    ("轨道交通", "Metro"),
    ("奥乐齐", "ALDI"),
    ("中石化", "Sinopec"),
    ("中国移动", "China Mobile"),
]


def display_merchant(name: str) -> str:
    """Return a short English display name for a merchant."""
    if name is None:
        return ""
    if isinstance(name, float) and math.isnan(name):
        return ""
    text = str(name).strip()
    if not text:
        return text

    if text in EXACT_NAMES:
        return EXACT_NAMES[text]

    for pattern, label in SUBSTRING_RULES:
        if pattern in text:
            return label

    try:
        text.encode("ascii")
        return text
    except UnicodeEncodeError:
        pass

    return text


def add_display_names(df, source_col: str = "merchant", target_col: str = "merchant_display"):
    """Add a display-name column to a DataFrame copy."""
    out = df.copy()
    out[target_col] = out[source_col].map(display_merchant)
    return out


def aggregate_merchants(df, n: int = 12) -> "pd.DataFrame":
    """Sum spending by English display name."""
    import pandas as pd

    return (
        df.assign(merchant_display=df['merchant'].map(display_merchant))
        .groupby('merchant_display', as_index=False)['amount']
        .sum()
        .nlargest(n, 'amount')
    )
