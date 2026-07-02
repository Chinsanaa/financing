"""Merchant pattern → spending category rules for the classifier pipeline.

Order matters for export: more specific patterns should appear before broader
ones in MERCHANT_CATEGORY_RULES. apply_merchant_rules() also sorts by length.
"""
from __future__ import annotations

import csv
from pathlib import Path

# (pattern, category) — specific patterns before broad substrings
MERCHANT_CATEGORY_RULES: list[tuple[str, str]] = [
    # --- Groceries: grocery delivery & supermarkets (before 美团/京东) ---
    ("美团买菜", "Groceries"),
    ("美团优选", "Groceries"),
    ("叮咚买菜", "Groceries"),
    ("京东便利店", "Groceries"),
    ("山姆会员商店", "Groceries"),
    ("山姆会员店", "Groceries"),
    ("盒马鲜生", "Groceries"),
    ("永辉超市", "Groceries"),
    ("7-ELEVEN", "Groceries"),
    ("7-11", "Groceries"),
    ("统一超商", "Groceries"),
    ("见福便利店", "Groceries"),
    ("天福便利店", "Groceries"),
    ("可的便利店", "Groceries"),
    ("十足便利店", "Groceries"),
    ("之上便利店", "Groceries"),
    ("易捷便利店", "Groceries"),
    ("唐久便利", "Groceries"),
    ("绝味鸭脖", "Groceries"),
    ("良品铺子", "Groceries"),
    ("三只松鼠", "Groceries"),
    ("荟选集市", "Groceries"),
    ("山姆", "Groceries"),
    ("开市客", "Groceries"),
    ("盒马", "Groceries"),
    ("永辉", "Groceries"),
    ("大润发", "Groceries"),
    ("华润万家", "Groceries"),
    ("美宜佳", "Groceries"),
    ("昆仑好客", "Groceries"),
    ("易捷", "Groceries"),
    ("天福", "Groceries"),
    ("见福", "Groceries"),
    ("红旗连锁", "Groceries"),
    ("便利蜂", "Groceries"),
    ("芙蓉兴盛", "Groceries"),
    ("唐久", "Groceries"),
    ("可的", "Groceries"),
    ("良友金伴", "Groceries"),
    ("良友", "Groceries"),
    ("十足", "Groceries"),
    ("好特卖", "Groceries"),
    ("ALDI", "Groceries"),
    ("奥乐齐", "Groceries"),
    ("LAWSON", "Groceries"),
    ("FamilyMart", "Groceries"),
    ("全家", "Groceries"),
    ("喜士多", "Groceries"),
    ("罗森", "Groceries"),
    ("好德", "Groceries"),
    ("沃尔玛", "Groceries"),
    ("家乐福", "Groceries"),
    ("钱大妈", "Groceries"),
    ("百果园", "Groceries"),
    ("泸溪河", "Groceries"),
    ("周黑鸭", "Groceries"),
    ("绝味", "Groceries"),
    ("APIO", "Groceries"),
    ("大黄鹅", "Groceries"),
    # Vending machines
    ("友宝", "Groceries"),
    ("乐科智控", "Groceries"),
    ("大象智贩", "Groceries"),
    ("聆动电子科技", "Groceries"),
    ("聆动", "Groceries"),
    # --- Transportation (before broad 申通/美团/哈啰) ---
    ("美团单车", "Transportation"),
    ("上海申通地铁", "Transportation"),
    ("申通地铁", "Transportation"),
    ("上海地铁", "Transportation"),
    ("公共交通卡", "Transportation"),
    ("滴滴出行", "Transportation"),
    ("高德打车", "Transportation"),
    ("哈啰出行", "Transportation"),
    ("曹操出行", "Transportation"),
    ("T3出行", "Transportation"),
    ("嘀嗒出行", "Transportation"),
    ("青桔单车", "Transportation"),
    ("摩拜单车", "Transportation"),
    ("一嗨租车", "Transportation"),
    ("神州租车", "Transportation"),
    ("中国东方航空", "Transportation"),
    ("东方航空", "Transportation"),
    ("南方航空", "Transportation"),
    ("春秋航空", "Transportation"),
    ("国际航空", "Transportation"),
    ("浦东机场", "Transportation"),
    ("轨道交通", "Transportation"),
    ("滴滴", "Transportation"),
    ("高德", "Transportation"),
    ("哈啰", "Transportation"),
    ("青桔", "Transportation"),
    ("摩拜", "Transportation"),
    ("地铁", "Transportation"),
    ("国航", "Transportation"),
    ("12306", "Transportation"),
    ("铁路", "Transportation"),
    ("DiDi", "Transportation"),
  # --- Eating Out: food delivery & restaurant chains ---
    ("饿了么", "Eating Out"),
    ("瑞幸咖啡", "Eating Out"),
    ("luckin coffee", "Eating Out"),
    ("汉堡王", "Eating Out"),
    ("BURGER KING", "Eating Out"),
    ("味千拉面", "Eating Out"),
    ("杨国福麻辣烫", "Eating Out"),
    ("张亮麻辣烫", "Eating Out"),
    ("和府捞面", "Eating Out"),
    ("遇见小面", "Eating Out"),
    ("紫燕百味鸡", "Eating Out"),
    ("沙县小吃", "Eating Out"),
    ("太二酸菜鱼", "Eating Out"),
    ("正新鸡排", "Eating Out"),
    ("巴奴毛肚火锅", "Eating Out"),
    ("西贝莜面村", "Eating Out"),
    ("塔可贝尔", "Eating Out"),
    ("乡村基", "Eating Out"),
    ("大米先生", "Eating Out"),
    ("米村拌饭", "Eating Out"),
    ("永和大王", "Eating Out"),
    ("大娘水饺", "Eating Out"),
    ("袁记云饺", "Eating Out"),
    ("眉州东坡", "Eating Out"),
    ("南京大牌档", "Eating Out"),
    ("绿茶餐厅", "Eating Out"),
    ("Manner咖啡", "Eating Out"),
    ("Tims咖啡", "Eating Out"),
    ("CoCo都可", "Eating Out"),
    ("茶颜悦色", "Eating Out"),
    ("库迪咖啡", "Eating Out"),
    ("蜜雪冰城", "Eating Out"),
    ("McDonald's", "Eating Out"),
    ("麦当劳", "Eating Out"),
    ("肯德基", "Eating Out"),
    ("KFC", "Eating Out"),
    ("必胜客", "Eating Out"),
    ("Pizza Hut", "Eating Out"),
    ("达美乐", "Eating Out"),
    ("Domino's", "Eating Out"),
    ("萨莉亚", "Eating Out"),
    ("Saizeriya", "Eating Out"),
    ("瑞幸", "Eating Out"),
    ("星巴克", "Eating Out"),
    ("喜茶", "Eating Out"),
    ("HEYTEA", "Eating Out"),
    ("霸王茶姬", "Eating Out"),
    ("CHAGEE", "Eating Out"),
    ("Mixue", "Eating Out"),
    ("蜜雪", "Eating Out"),
    ("茶百道", "Eating Out"),
    ("古茗", "Eating Out"),
    ("奈雪", "Eating Out"),
    ("沪上阿姨", "Eating Out"),
    ("书亦烧仙草", "Eating Out"),
    ("甜啦啦", "Eating Out"),
    ("益禾堂", "Eating Out"),
    ("1点点", "Eating Out"),
    ("一点点", "Eating Out"),
    ("SUBWAY", "Eating Out"),
    ("POPEYES", "Eating Out"),
    ("海底捞", "Eating Out"),
    ("吉野家", "Eating Out"),
    ("味千", "Eating Out"),
    ("真功夫", "Eating Out"),
    ("老娘舅", "Eating Out"),
    ("西贝", "Eating Out"),
    ("华莱士", "Eating Out"),
    ("德克士", "Eating Out"),
    ("塔斯汀", "Eating Out"),
    ("黄记煌", "Eating Out"),
    ("小肥羊", "Eating Out"),
    ("老乡鸡", "Eating Out"),
    ("杨国福", "Eating Out"),
    ("九毛九", "Eating Out"),
    ("呷哺呷哺", "Eating Out"),
    ("小龙坎", "Eating Out"),
    ("大龙燚", "Eating Out"),
    ("外婆家", "Eating Out"),
    ("费大厨", "Eating Out"),
    ("西少爷", "Eating Out"),
    ("兰熊鲜奶", "Eating Out"),
    ("巴奴", "Eating Out"),
    ("Manner", "Eating Out"),
    ("M Stand", "Eating Out"),
    ("库迪", "Eating Out"),
    ("蘇小柳", "Eating Out"),
    ("昆仑唐府", "Eating Out"),
    ("喝清喝理", "Eating Out"),
    ("正三熙", "Eating Out"),
    ("小满手工粉", "Eating Out"),
    ("卯时六点半", "Eating Out"),
    ("餐饮", "Eating Out"),
    ("catering", "Eating Out"),
    ("Meituan", "Eating Out"),
    ("美团", "Eating Out"),
    # --- Shopping: retail & e-commerce ---
    ("淘宝闪购", "Shopping"),
    ("淘宝平台", "Shopping"),
    ("淘天物流", "Shopping"),
    ("京东物流", "Shopping"),
    ("京东秒送", "Shopping"),
    ("小米有品", "Shopping"),
    ("网易严选", "Shopping"),
    ("淘宝", "Shopping"),
    ("Taobao", "Shopping"),
    ("天猫", "Shopping"),
    ("京东", "Shopping"),
    ("JD.com", "Shopping"),
    ("拼多多", "Shopping"),
    ("Pinduoduo", "Shopping"),
    ("得物", "Shopping"),
    ("Dewu", "Shopping"),
    ("闲鱼", "Shopping"),
    ("1688", "Shopping"),
    ("唯品会", "Shopping"),
    ("抖音", "Shopping"),
    ("快手", "Shopping"),
    ("小红书", "Shopping"),
    ("京喜", "Shopping"),
    ("菜鸟", "Shopping"),
    ("名创优品", "Shopping"),
    ("MINISO", "Shopping"),
    ("无印良品", "Shopping"),
    ("MUJI", "Shopping"),
    ("优衣库", "Shopping"),
    ("泡泡玛特", "Shopping"),
    ("迪卡侬", "Shopping"),
    ("宜家家居", "Shopping"),
    ("宜家", "Shopping"),
    ("全棉时代", "Shopping"),
    ("孩子王", "Shopping"),
    ("苏宁易购", "Shopping"),
    ("苏宁", "Shopping"),
    ("国美电器", "Shopping"),
    ("国美", "Shopping"),
    ("万达影城", "Shopping"),
    ("万达", "Shopping"),
    ("中免日上", "Shopping"),
    ("中免", "Shopping"),
    ("杜福睿", "Shopping"),
    ("杂物社", "Shopping"),
    ("屈臣氏", "Shopping"),
    ("万宁", "Shopping"),
    ("绿联", "Shopping"),
    ("KKV", "Shopping"),
    ("小米之家", "Shopping"),
    ("小米", "Shopping"),
    ("华为", "Shopping"),
    ("苹果", "Shopping"),
    # 华润万家 listed above; bare 华润 often appears on supermarket charges
    ("华润", "Groceries"),
    # --- Utilities & Services ---
    ("国际旅行卫生保健", "Utilities & Services"),
    ("一网通办", "Utilities & Services"),
    ("国家电网", "Utilities & Services"),
    ("南方电网", "Utilities & Services"),
    ("中国移动", "Utilities & Services"),
    ("中国联通", "Utilities & Services"),
    ("中国电信", "Utilities & Services"),
    ("China Mobile", "Utilities & Services"),
    ("中石化", "Utilities & Services"),
    ("中石油", "Utilities & Services"),
    ("Sinopec", "Utilities & Services"),
    ("PetroChina", "Utilities & Services"),
    ("申通快递", "Utilities & Services"),
    ("中通快递", "Utilities & Services"),
    ("圆通速递", "Utilities & Services"),
    ("韵达快递", "Utilities & Services"),
    ("极兔速递", "Utilities & Services"),
    ("德邦快递", "Utilities & Services"),
    ("邮政EMS", "Utilities & Services"),
    ("顺丰", "Utilities & Services"),
    ("中通", "Utilities & Services"),
    ("圆通", "Utilities & Services"),
    ("韵达", "Utilities & Services"),
    ("极兔", "Utilities & Services"),
    ("德邦", "Utilities & Services"),
    ("EMS", "Utilities & Services"),
    ("共享按摩椅", "Utilities & Services"),
    ("爱奇艺", "Utilities & Services"),
    ("腾讯视频", "Utilities & Services"),
    ("优酷", "Utilities & Services"),
    ("芒果TV", "Utilities & Services"),
    ("汽水音乐", "Utilities & Services"),
    ("哔哩哔哩", "Utilities & Services"),
    ("B站", "Utilities & Services"),
    ("网易", "Utilities & Services"),
    # --- Transfers & Gifts ---
    ("个人收款", "Transfers & Gifts"),
]

# User-specific / local merchants (override or supplement chain rules)
LOCAL_MERCHANT_RULES: list[tuple[str, str]] = [
    # NYU Shanghai split by description in special_category() — no blanket rule here
    ("上海蕤盛工贸", "Transportation"),  # Shanghai metro (~¥5 rides)
    ("上海都畅数字技术有限公司", "Transportation"),  # metro payment tech
    ("济明路蘭州牛肉面", "Eating Out"),
    ("美淑家", "Eating Out"),
    ("饿梨酱", "Eating Out"),
    ("YogurtDay", "Eating Out"),
    ("马永胜牛肉面", "Eating Out"),
    ("豹喵酒吧", "Eating Out"),
    ("橘柚梧桐", "Eating Out"),
    ("Sydney Yuen", "Transfers & Gifts"),
    ("Evie", "Transfers & Gifts"),
    ("**店", "Shopping"),  # masked Taobao stores
]

# NYU Shanghai: cafeteria POS charges vs campus admin fees (match on description).
NYU_SHANGHAI_MERCHANT = "上海纽约大学"
NYU_OTHER_DESCRIPTION_MARKERS = (
    "Campus Card Top Up",
    "Tuition and Fees",
    "NYUCard Print Fee",
)


def special_category(merchant: str, description: str) -> str | None:
    """Per-row category override from merchant + description. None if no rule."""
    merchant = str(merchant or "").strip()
    description = str(description or "").strip()

    if merchant == NYU_SHANGHAI_MERCHANT:
        if any(marker in description for marker in NYU_OTHER_DESCRIPTION_MARKERS):
            return "Other"
        return "Eating Out"

    if merchant == "上海蕤盛工贸":
        return "Transportation"

    return None


def all_merchant_rules() -> list[tuple[str, str]]:
    """Chain rules first; local rules override category for the same pattern."""
    merged: dict[str, str] = {}
    order: list[str] = []
    for pattern, category in MERCHANT_CATEGORY_RULES:
        if pattern not in merged:
            order.append(pattern)
        merged[pattern] = category
    for pattern, category in LOCAL_MERCHANT_RULES:
        if pattern not in merged:
            order.append(pattern)
        merged[pattern] = category
    return [(pattern, merged[pattern]) for pattern in order]


def rules_as_dict() -> dict[str, str]:
    """Lowercase pattern → category for label.apply_merchant_rules."""
    return {p.lower(): c for p, c in all_merchant_rules()}


def write_rules_csv(path: Path) -> int:
    """Write rules CSV; returns row count."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = all_merchant_rules()
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["merchant_pattern", "category"])
        writer.writerows(rows)
    return len(rows)


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    starter = root / "data" / "templates" / "merchant_rules_starter.csv"
    expanded = root / "data" / "labeled" / "merchant_rules_expanded.csv"
    n = write_rules_csv(starter)
    write_rules_csv(expanded)
    print(f"Wrote {n} rules to {starter.name} and merchant_rules_expanded.csv")
