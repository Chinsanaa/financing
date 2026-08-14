"""Merchant pattern → spending category rules for the classifier pipeline.

Order matters for export: more specific patterns should appear before broader
ones in MERCHANT_CATEGORY_RULES. apply_merchant_rules() also sorts by length.

Precedence at match time (see label._match_merchant): patterns are tried
longest-first, so a more specific/longer pattern always beats a shorter,
broader one for the same merchant string. For two patterns of *equal*
length, the sort is stable, so whichever one appears first in this file (in
MERCHANT_CATEGORY_RULES, then LOCAL_MERCHANT_RULES) wins — a same-length
collision is resolved by list position, not by any explicit rule. Keep this
in mind when adding new short/generic patterns; prefer patterns specific
enough that same-length collisions can't happen at all (see
tests/test_merchant_rules.py for regression coverage of known-risky cases).
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
    # Grocery keywords (English)
    ("grocery", "Groceries"),
    ("supermarket", "Groceries"),
    ("mart", "Groceries"),
    ("market", "Groceries"),
    # --- Groceries: disambiguation keywords (for unseen merchants/descriptions) ---
    ("produce", "Groceries"),
    ("vegetables", "Groceries"),
    ("fruits", "Groceries"),
    ("fruit", "Groceries"),
    ("meat market", "Groceries"),
    ("fish market", "Groceries"),
    ("bakery", "Groceries"),
    ("daily essentials", "Groceries"),
    ("household items", "Groceries"),
    ("bulk buy", "Groceries"),
    ("wholesale", "Groceries"),
    ("蔬菜", "Groceries"),
    ("水果", "Groceries"),
    ("生鲜", "Groceries"),
    ("菜市场", "Groceries"),
    ("日用品", "Groceries"),
    ("家用", "Groceries"),
    ("批发", "Groceries"),
    ("食材", "Groceries"),
    ("粮油", "Groceries"),
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
    ("轨道交通", "Transportation"),
    ("滴滴", "Transportation"),
    ("高德", "Transportation"),
    ("哈啰", "Transportation"),
    ("青桔", "Transportation"),
    ("摩拜", "Transportation"),
    ("地铁", "Transportation"),
    ("12306", "Transportation"),
    ("铁路", "Transportation"),
    ("DiDi", "Transportation"),
    # --- Transportation: disambiguation keywords (for unseen merchants/descriptions) ---
    ("ride", "Transportation"),
    ("driver", "Transportation"),
    ("passenger", "Transportation"),
    ("fare", "Transportation"),
    ("transit", "Transportation"),
    ("train", "Transportation"),
    # "bus" deliberately excluded: too generic (matches "business", "busy", etc.);
    # "subway"/"metro"/"transit" cover public transit without the collision risk.
    ("subway", "Transportation"),
    ("metro", "Transportation"),
    ("parking", "Transportation"),
    ("toll", "Transportation"),
    # "gas" deliberately excluded: matches inside unrelated words (e.g. "Vegas");
    # "fuel" below covers the same intent more safely.
    ("fuel", "Transportation"),
    ("车费", "Transportation"),
    ("乘坐", "Transportation"),
    ("班车", "Transportation"),
    ("高铁", "Transportation"),
    ("停泊费", "Transportation"),
    ("汽油", "Transportation"),
    # --- Travel: flights, airports, hotels, trips (moved off Transportation so
    # local commuting stays distinct from vacation/trip spend) ---
    ("中国东方航空", "Travel"),
    ("东方航空", "Travel"),
    ("南方航空", "Travel"),
    ("春秋航空", "Travel"),
    ("国际航空", "Travel"),
    ("浦东机场", "Travel"),
    ("国航", "Travel"),
    ("携程", "Travel"),
    ("Ctrip", "Travel"),
    ("去哪儿", "Travel"),
    ("Qunar", "Travel"),
    ("飞猪", "Travel"),
    ("Fliggy", "Travel"),
    ("Booking.com", "Travel"),
    ("Airbnb", "Travel"),
    ("如家酒店", "Travel"),
    ("汉庭酒店", "Travel"),
    ("锦江之星", "Travel"),
    ("7天连锁酒店", "Travel"),
    ("flight", "Travel"),
    ("airport", "Travel"),
    ("airline", "Travel"),
    ("hotel", "Travel"),
    ("resort", "Travel"),
    # bare "ticket" deliberately excluded: too generic (movie/concert/parking
    # tickets aren't Travel) — flight/train ticket keywords above cover the
    # real intent without the collision.
    ("itinerary", "Travel"),
    ("vacation", "Travel"),
    ("visa", "Travel"),
    ("火车票", "Travel"),
    ("飞机票", "Travel"),
    ("机票", "Travel"),
    ("酒店", "Travel"),
    ("民宿", "Travel"),
    ("度假", "Travel"),
    ("旅游", "Travel"),
    ("签证", "Travel"),
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
    # --- Eating Out: disambiguation keywords (for unseen merchants/descriptions) ---
    ("restaurant", "Eating Out"),
    ("cafe", "Eating Out"),
    ("coffee", "Eating Out"),
    ("café", "Eating Out"),
    ("food delivery", "Eating Out"),
    ("takeout", "Eating Out"),
    ("takeaway", "Eating Out"),
    ("order food", "Eating Out"),
    ("menu", "Eating Out"),
    ("dine", "Eating Out"),
    ("snack", "Eating Out"),
    ("noodle", "Eating Out"),
    ("ramen", "Eating Out"),
    ("sushi", "Eating Out"),
    ("burger", "Eating Out"),
    ("pizza", "Eating Out"),
    ("taco", "Eating Out"),
    ("kebab", "Eating Out"),
    ("boba", "Eating Out"),
    ("bubble tea", "Eating Out"),
    ("面馆", "Eating Out"),
    ("饭店", "Eating Out"),
    ("饮食", "Eating Out"),
    ("外卖", "Eating Out"),
    ("订餐", "Eating Out"),
    ("小吃", "Eating Out"),
    ("烧烤", "Eating Out"),
    ("火锅", "Eating Out"),
    ("粥店", "Eating Out"),
    ("炸鸡", "Eating Out"),
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
    ("中免日上", "Shopping"),
    ("中免", "Shopping"),
    ("杜福睿", "Shopping"),
    ("杂物社", "Shopping"),
    ("绿联", "Shopping"),
    ("KKV", "Shopping"),
    ("小米之家", "Shopping"),
    ("小米", "Shopping"),
    ("华为", "Shopping"),
    ("苹果", "Shopping"),
    # Clothing brands
    ("NIKE", "Shopping"),
    ("nike", "Shopping"),
    ("Adidas", "Shopping"),
    ("adidas", "Shopping"),
    ("ZARA", "Shopping"),
    ("zara", "Shopping"),
    ("H&M", "Shopping"),
    ("h&m", "Shopping"),
    ("Forever 21", "Shopping"),
    ("ASOS", "Shopping"),
    ("Uniqlo", "Shopping"),
    ("uniqlo", "Shopping"),
    ("GAP", "Shopping"),
    ("SHEIN", "Shopping"),
    ("Gucci", "Shopping"),
    ("LV", "Shopping"),
    ("Prada", "Shopping"),
    ("Burberry", "Shopping"),
    ("Coach", "Shopping"),
    ("Alexander McQueen", "Shopping"),
    ("Balenciaga", "Shopping"),
    ("Dior", "Shopping"),
    ("Fendi", "Shopping"),
    ("Hermes", "Shopping"),
    ("Versace", "Shopping"),
    ("Valentino", "Shopping"),
    ("Armani", "Shopping"),
    ("Tommy Hilfiger", "Shopping"),
    ("Calvin Klein", "Shopping"),
    ("Ralph Lauren", "Shopping"),
    ("Lacoste", "Shopping"),
    ("champion", "Shopping"),
    ("Champion", "Shopping"),
    ("Reebok", "Shopping"),
    ("Puma", "Shopping"),
    ("New Balance", "Shopping"),
    ("Converse", "Shopping"),
    ("Vans", "Shopping"),
    # Electronics & gadgets
    ("Samsung", "Shopping"),
    ("samsung", "Shopping"),
    ("LG", "Shopping"),
    ("Sony", "Shopping"),
    ("Panasonic", "Shopping"),
    ("Intel", "Shopping"),
    ("Nvidia", "Shopping"),
    ("AMD", "Shopping"),
    ("Razer", "Shopping"),
    ("Logitech", "Shopping"),
    ("SteelSeries", "Shopping"),
    ("Corsair", "Shopping"),
    ("ASUS", "Shopping"),
    ("Acer", "Shopping"),
    ("Lenovo", "Shopping"),
    ("Dell", "Shopping"),
    ("HP", "Shopping"),
    ("Microsoft", "Shopping"),
    ("Canon", "Shopping"),
    ("Nikon", "Shopping"),
    ("Sony", "Shopping"),
    ("GoPro", "Shopping"),
    ("DJI", "Shopping"),
    ("iPhone", "Shopping"),
    ("iPad", "Shopping"),
    ("MacBook", "Shopping"),
    ("AirPods", "Shopping"),
    ("Apple Watch", "Shopping"),
    ("watch", "Shopping"),  # Watches (broad but often used for shopping)
    ("camera", "Shopping"),  # Cameras
    ("drone", "Shopping"),  # Drones
    ("headphone", "Shopping"),  # Headphones
    ("earphone", "Shopping"),  # Earphones
    ("laptop", "Shopping"),  # Laptops
    ("monitor", "Shopping"),  # Monitors
    ("keyboard", "Shopping"),  # Keyboards
    ("mouse", "Shopping"),  # Mice
    ("charger", "Shopping"),  # Chargers
    ("cable", "Shopping"),  # Cables
    ("battery", "Shopping"),  # Batteries
    ("router", "Shopping"),  # Routers
    ("speaker", "Shopping"),  # Speakers
    ("microphone", "Shopping"),  # Microphones
    # --- Shopping: disambiguation keywords (for unseen merchants/descriptions) ---
    ("product", "Shopping"),
    ("item", "Shopping"),
    ("clothing", "Shopping"),
    ("apparel", "Shopping"),
    ("shoes", "Shopping"),
    ("shoe", "Shopping"),
    ("outfit", "Shopping"),
    ("dress", "Shopping"),
    ("pants", "Shopping"),
    ("shirt", "Shopping"),
    ("jacket", "Shopping"),
    ("gadget", "Shopping"),
    ("device", "Shopping"),
    # bare "toy"/"pet" deliberately excluded: too generic (e.g. "Toyota", "carpet",
    # "Pete's"); the "toy store"/"pet store" patterns below cover the real intent.
    ("toy store", "Shopping"),
    ("pet store", "Shopping"),
    ("book", "Shopping"),
    ("bookstore", "Shopping"),
    ("office supplies", "Shopping"),
    ("office", "Shopping"),
    ("craft", "Shopping"),
    ("服装", "Shopping"),
    ("衣服", "Shopping"),
    ("鞋子", "Shopping"),
    ("玩具", "Shopping"),
    ("宠物", "Shopping"),
    ("书籍", "Shopping"),
    ("图书", "Shopping"),
    ("办公", "Shopping"),
    ("手工", "Shopping"),
    # Taobao-like patterns (merchants with ** in name)
    ("**", "Shopping"),
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
    # --- Utilities & Services: disambiguation keywords (for unseen merchants/descriptions) ---
    ("subscription", "Utilities & Services"),
    ("monthly fee", "Utilities & Services"),
    ("annual fee", "Utilities & Services"),
    ("renewal", "Utilities & Services"),
    ("service charge", "Utilities & Services"),
    ("membership", "Utilities & Services"),
    ("premium", "Utilities & Services"),
    ("bill", "Utilities & Services"),
    ("invoice", "Utilities & Services"),
    ("service", "Utilities & Services"),
    ("续费", "Utilities & Services"),
    ("会费", "Utilities & Services"),
    ("月费", "Utilities & Services"),
    ("年费", "Utilities & Services"),
    ("服务费", "Utilities & Services"),
    ("订阅", "Utilities & Services"),
    ("会员", "Utilities & Services"),
    ("insurance", "Utilities & Services"),
    ("保险", "Utilities & Services"),
    # --- Housing: rent, mortgage, property management, home repairs ---
    ("rent", "Housing"),
    ("mortgage", "Housing"),
    ("property management", "Housing"),
    ("房租", "Housing"),
    ("房贷", "Housing"),
    ("物业费", "Housing"),
    ("物业管理", "Housing"),
    ("房屋维修", "Housing"),
    # --- Personal Care & Health: pharmacies, clinics, gyms, salons ---
    ("屈臣氏", "Personal Care & Health"),
    ("万宁", "Personal Care & Health"),
    ("Watsons", "Personal Care & Health"),
    ("pharmacy", "Personal Care & Health"),
    ("drugstore", "Personal Care & Health"),
    ("hospital", "Personal Care & Health"),
    ("clinic", "Personal Care & Health"),
    ("dental", "Personal Care & Health"),
    ("dentist", "Personal Care & Health"),
    ("fitness", "Personal Care & Health"),
    ("yoga", "Personal Care & Health"),
    ("salon", "Personal Care & Health"),
    ("haircut", "Personal Care & Health"),
    ("药店", "Personal Care & Health"),
    ("药房", "Personal Care & Health"),
    ("医院", "Personal Care & Health"),
    ("诊所", "Personal Care & Health"),
    ("牙科", "Personal Care & Health"),
    ("健身房", "Personal Care & Health"),
    ("美容", "Personal Care & Health"),
    ("美发", "Personal Care & Health"),
    ("理发", "Personal Care & Health"),
    # --- Entertainment: streaming, gaming, cinema, live events ---
    ("万达影城", "Entertainment"),
    ("万达", "Entertainment"),
    ("爱奇艺", "Entertainment"),
    ("腾讯视频", "Entertainment"),
    ("优酷", "Entertainment"),
    ("芒果TV", "Entertainment"),
    ("汽水音乐", "Entertainment"),
    ("哔哩哔哩", "Entertainment"),
    ("B站", "Entertainment"),
    ("网易云音乐", "Entertainment"),
    ("网易", "Entertainment"),
    ("Netflix", "Entertainment"),
    ("Spotify", "Entertainment"),
    ("Steam", "Entertainment"),
    ("PlayStation", "Entertainment"),
    ("Xbox", "Entertainment"),
    ("cinema", "Entertainment"),
    ("movie ticket", "Entertainment"),
    ("concert ticket", "Entertainment"),
    ("streaming", "Entertainment"),
    ("电影院", "Entertainment"),
    ("电影票", "Entertainment"),
    ("演唱会", "Entertainment"),
    ("剧院", "Entertainment"),
    ("游戏", "Entertainment"),
    # --- Education: tuition, schools, courses, books ---
    ("tuition", "Education"),
    ("university", "Education"),
    ("textbook", "Education"),
    ("学费", "Education"),
    ("大学", "Education"),
    ("学校", "Education"),
    ("教材", "Education"),
    ("培训班", "Education"),
    ("课程", "Education"),
    # --- Investments: funds, brokerage, wealth management ---
    ("余额宝", "Investments"),
    ("天弘基金", "Investments"),
    ("蚂蚁财富", "Investments"),
    ("brokerage", "Investments"),
    ("基金申购", "Investments"),
    ("基金定投", "Investments"),
    ("理财通", "Investments"),
    ("基金", "Investments"),
    ("理财", "Investments"),
    ("股票", "Investments"),
    # --- Transfers & Gifts ---
    # Keywords
    ("transfer", "Transfers & Gifts"),
    ("Transfer", "Transfers & Gifts"),
    ("p2p", "Transfers & Gifts"),
    ("P2P", "Transfers & Gifts"),
    ("个人收款", "Transfers & Gifts"),
    # --- Transfers & Gifts: disambiguation keywords (for unseen merchants/descriptions) ---
    ("send money", "Transfers & Gifts"),
    ("payment", "Transfers & Gifts"),
    ("remittance", "Transfers & Gifts"),
    ("gift", "Transfers & Gifts"),
    ("present", "Transfers & Gifts"),
    ("tip", "Transfers & Gifts"),
    ("gratuity", "Transfers & Gifts"),
    ("allowance", "Transfers & Gifts"),
    ("personal loan", "Transfers & Gifts"),
    ("reimbursement", "Transfers & Gifts"),
    ("汇款", "Transfers & Gifts"),
    ("红包", "Transfers & Gifts"),
    ("礼物", "Transfers & Gifts"),
    ("赏金", "Transfers & Gifts"),
    ("补贴", "Transfers & Gifts"),
    ("报销", "Transfers & Gifts"),
    ("打赏", "Transfers & Gifts"),
    # Bank withdrawals & transfers between banks
    ("Bank of China", "Transfers & Gifts"),
    ("中国银行", "Transfers & Gifts"),
    ("中国工商银行", "Transfers & Gifts"),
    ("工商银行", "Transfers & Gifts"),
    ("中国农业银行", "Transfers & Gifts"),
    ("农业银行", "Transfers & Gifts"),
    ("中国建设银行", "Transfers & Gifts"),
    ("建设银行", "Transfers & Gifts"),
    ("交通银行", "Transfers & Gifts"),
    ("中信银行", "Transfers & Gifts"),
    ("招商银行", "Transfers & Gifts"),
    ("浦发银行", "Transfers & Gifts"),
    ("民生银行", "Transfers & Gifts"),
    ("平安银行", "Transfers & Gifts"),
    ("兴业银行", "Transfers & Gifts"),
    ("光大银行", "Transfers & Gifts"),
    ("华夏银行", "Transfers & Gifts"),
    ("北京银行", "Transfers & Gifts"),
    ("上海银行", "Transfers & Gifts"),
    ("深圳发展银行", "Transfers & Gifts"),
    ("深圳银行", "Transfers & Gifts"),
    ("南京银行", "Transfers & Gifts"),
    ("杭州银行", "Transfers & Gifts"),
    ("宁波银行", "Transfers & Gifts"),
    ("温州银行", "Transfers & Gifts"),
    ("成都银行", "Transfers & Gifts"),
    ("西安银行", "Transfers & Gifts"),
    ("重庆银行", "Transfers & Gifts"),
    ("武汉银行", "Transfers & Gifts"),
    ("郑州银行", "Transfers & Gifts"),
    ("邮储银行", "Transfers & Gifts"),
    ("邮政储蓄", "Transfers & Gifts"),
    ("支付宝转账", "Transfers & Gifts"),
    ("微信转账", "Transfers & Gifts"),
    ("微信支付", "Transfers & Gifts"),
    ("alipay", "Transfers & Gifts"),
    ("wechat", "Transfers & Gifts"),
    ("withdrawal", "Transfers & Gifts"),
    ("Withdrawal", "Transfers & Gifts"),
    # Deliberately no bare "bank"/"Bank" rule: it's the most generic collision-prone
    # pattern in this file (matches any merchant with "bank" as a substring, e.g.
    # non-bank businesses with "bank" in the name). The explicit bank names above
    # already cover the realistic domestic cases.
]

# User-specific / local merchants (override or supplement chain rules)
LOCAL_MERCHANT_RULES: list[tuple[str, str]] = [
    # NYU Shanghai split by description in special_category() — no blanket rule here
    ("上海蕤盛工贸", "Transportation"),  # Shanghai metro (~¥5 rides)
    ("上海都畅数字技术有限公司", "Transportation"),  # metro payment tech

    # --- Eating Out (from manual review) ---
    ("济明路蘭州牛肉面", "Eating Out"),
    ("美淑家", "Eating Out"),
    ("饿梨酱", "Eating Out"),
    ("YogurtDay", "Eating Out"),
    ("马永胜牛肉面", "Eating Out"),
    ("豹喵酒吧", "Eating Out"),
    ("橘柚梧桐", "Eating Out"),
    ("Holy Bagel", "Eating Out"),
    ("Habibi", "Eating Out"),
    ("13DE MARZO", "Eating Out"),
    ("AMINO AMIGO", "Eating Out"),
    ("LA BARAKA UV", "Eating Out"),
    ("鹈鹕镇大王", "Eating Out"),
    ("上海英和企业管理有限公司", "Eating Out"),
    ("floating kitchen", "Eating Out"),

    # --- Groceries (from manual review) ---
    ("高青西门市", "Groceries"),
    ("K-MART", "Groceries"),
    ("上海香雪海国际贸易有限公司", "Groceries"),
    ("上海优悠生活商业管理有限公司", "Groceries"),

    # --- Shopping (from manual review) ---
    ("JUNGLEplus", "Shopping"),
    ("上海谱墨品牌管理有限公司", "Shopping"),
    ("ws**1", "Shopping"),
    ("**店", "Shopping"),  # masked Taobao stores

    # --- Transfers & Gifts (from manual review - personal names & P2P transfers) ---
    ("Sydney Yuen", "Transfers & Gifts"),
    ("Evie", "Transfers & Gifts"),
    ("Tara", "Transfers & Gifts"),
    ("sydney", "Transfers & Gifts"),
    ("Steve", "Transfers & Gifts"),
    ("dudu", "Transfers & Gifts"),
    ("enni", "Transfers & Gifts"),
    ("urnma", "Transfers & Gifts"),
    ("UYANGA", "Transfers & Gifts"),
    ("Margad", "Transfers & Gifts"),
    ("O. A. OCHIR", "Transfers & Gifts"),
    ("Yesui Battogtokh", "Transfers & Gifts"),
    ("Munkh-Erdene", "Transfers & Gifts"),
    ("ERDENE", "Transfers & Gifts"),
    ("Tselmeg Bayarjargal", "Transfers & Gifts"),
    ("Tsolmon Khurelbaatar", "Transfers & Gifts"),
    ("Ujin", "Transfers & Gifts"),
    ("ujin", "Transfers & Gifts"),
    ("Uranmaa", "Transfers & Gifts"),
    ("Udval Lkhagvadorj", "Transfers & Gifts"),
    # "Ari" deliberately excluded: doubles as a common substring (e.g. "Mariana",
    # "Aristocrat") — too broad to trust as a bare, never-reviewed rule.
    ("Anar", "Transfers & Gifts"),
    ("E. DULGUUN", "Transfers & Gifts"),
    ("B. E. DULGUUN", "Transfers & Gifts"),
    ("P2P Transfer", "Transfers & Gifts"),
    ("River", "Transfers & Gifts"),
    ("S. MISHEEL", "Transfers & Gifts"),
    ("Laine", "Transfers & Gifts"),
    ("M.i", "Transfers & Gifts"),
    ("Misheel.S", "Transfers & Gifts"),
    ("Erkhkhongor", "Transfers & Gifts"),
    ("G. A. ERDENE", "Transfers & Gifts"),
    ("ODAY", "Transfers & Gifts"),
    ("Naransuvd", "Transfers & Gifts"),
    ("Yugi", "Transfers & Gifts"),
    ("murun", "Transfers & Gifts"),
    # "Hi" and "alex" deliberately excluded: common English greeting/word and a
    # substring of unrelated brand names (e.g. "Alexander McQueen", "Alex's Pizza")
    # — too broad to trust as a bare, never-reviewed rule.
]

# NYU Shanghai: cafeteria POS charges vs campus admin fees (match on description).
NYU_SHANGHAI_MERCHANT = "上海纽约大学"
NYU_SERVICE_DESCRIPTION_MARKERS = (
    "Campus Card Top Up",
    "Tuition and Fees",
    "NYUCard Print Fee",
)

# Description-based disambiguation keywords for unseen merchants.
# Ordered list of (category, keywords) — first category with a keyword hit wins.
# Module-level so the tuples aren't rebuilt on every special_category() call.
DESCRIPTION_KEYWORD_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("Eating Out", ("noodle", "ramen", "sushi", "burger", "pizza", "food order",
                    "takeout", "meal", "dine", "餐", "面", "烧烤", "火锅", "粥", "外卖")),
    ("Groceries", ("vegetable", "fruit", "produce", "grocery", "生鲜", "蔬菜",
                   "水果", "食材", "日用品", "菜", "批发")),
    ("Shopping", ("shoe", "cloth", "dress", "gadget", "book", "laptop",
                  "charger", "cable", "camera", "鞋", "衣服", "玩具", "书籍")),
    # "watch"/"toy" deliberately excluded: "watch" is usually the verb ("watch a
    # movie"), and "toy" collides with unrelated words ("Toyota") — both high
    # false-positive rate in free-text descriptions.
    ("Transportation", (
        "ride", "parking", "fuel", "车费", "停泊", "加油", "汽油",
        # Shanghai Metro station names appearing in transaction descriptions.
        # Station names only, not generic district/province names — those
        # are too broad and collide with unrelated merchants' legal business
        # names (e.g. "上海XX有限公司"). "hongqiao"/"浦东" and "pudong"/"虹桥"
        # are borderline (also district names), included anyway since they're
        # specific, frequently-visited stations for this user.
        "houtan", "后滩", "jing'an temple", "jingan temple", "静安寺",
        "lujiazui", "陆家嘴", "hongqiao", "虹桥", "pudong", "浦东",
        "people's square", "人民广场", "xujiahui", "徐家汇",
        "century avenue", "世纪大道", "nanjing road", "南京东路", "南京西路",
        "zhongshan park", "中山公园", "longyang road", "龙阳路",
        "yuyuan garden", "豫园",
    )),
    # "gas" deliberately excluded: matches inside unrelated words (e.g. "Vegas").
    ("Travel", ("flight", "airport", "hotel", "vacation", "机票", "酒店", "度假", "旅游")),
    ("Housing", ("rent", "mortgage", "房租", "房贷", "物业")),
    ("Personal Care & Health", ("pharmacy", "hospital", "clinic", "gym", "dental",
                                "药店", "医院", "诊所", "健身")),
    ("Entertainment", ("cinema", "movie ticket", "concert", "streaming",
                       "电影", "演唱会", "游戏")),
    ("Education", ("tuition", "textbook", "学费", "学校")),
    ("Investments", ("investment", "fund", "stock", "基金", "理财", "股票")),
    ("Transfers & Gifts", ("send money", "gift", "present", "payment", "transfer", "remittance",
                           "红包", "汇款", "礼物", "赏金")),
]


def special_category(merchant: str, description: str) -> str | None:
    """Per-row category override from merchant + description. None if no rule."""
    merchant = str(merchant or "").strip()
    description = str(description or "").strip()
    description_lower = description.lower()

    if merchant == NYU_SHANGHAI_MERCHANT:
        if any(marker in description for marker in NYU_SERVICE_DESCRIPTION_MARKERS):
            return "Education"
        return "Eating Out"

    if merchant == "上海蕤盛工贸":
        return "Transportation"

    # Description-based disambiguation for unseen merchants.
    # High-confidence product/action keywords that clearly indicate a category.
    for category, keywords in DESCRIPTION_KEYWORD_RULES:
        if any(kw in description_lower for kw in keywords):
            return category

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
