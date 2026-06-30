"""Find the highest-confidence Travel and Other candidates for labeling."""
import pandas as pd
import re

df_all = pd.read_csv('data/processed/transactions_classified.csv')
df_labeled = pd.read_csv('data/labeled/labeled_transactions.csv')

# Get already labeled
already_labeled = set(df_labeled['timestamp'])

# Filter to unlabeled
df_candidates = df_all[~df_all['timestamp'].isin(already_labeled)].copy()

# Create combined text field
df_candidates['text'] = df_candidates['merchant'] + ' ' + df_candidates['description']

# TRAVEL: look for these patterns specifically
travel_patterns = [
    'travel', 'hotel', 'flight', 'flight', 'ticket', 'booking',
    'airbnb', 'airport', 'airline', 'train', 'bus', 'visa', 'passport',
    '旅行', '酒店', '宾馆', '机票', '火车', '高铁', '客运',
    '健康', '卫生', '疫苗', '签证', '护照', '出入境',
    'health', 'vaccine', 'health check'
]

# OTHER: look for government/service/misc patterns
other_patterns = [
    'government', 'fee', 'payment', 'platform', 'service',
    '缴费', '政府', '公共', '卡', '通办', '订阅', '会费',
    'subscription', 'membership', 'utility', 'service fee'
]

df_candidates['text_lower'] = df_candidates['text'].str.lower()

# Find matches
travel_mask = df_candidates['text_lower'].str.contains('|'.join(travel_patterns), na=False)
other_mask = df_candidates['text_lower'].str.contains('|'.join(other_patterns), na=False)

travel_candidates = df_candidates[travel_mask].sort_values('confidence', ascending=False)
other_candidates = df_candidates[other_mask].sort_values('confidence', ascending=False)

# Remove duplicates between lists (e.g., "carding" could match both)
other_candidates = other_candidates[~other_candidates.index.isin(travel_candidates.index)]

print("="*80)
print(f"TRAVEL CANDIDATES: {len(travel_candidates)} found")
print("="*80)
print("\nTop 20 Travel candidates (sorted by relevance):\n")

for i, (idx, row) in enumerate(travel_candidates.head(20).iterrows(), 1):
    print(f"{i:2d}. {row['timestamp'][:10]} | {row['amount']:7.2f} | {row['merchant'][:40]}")
    print(f"    >>> {row['description'][:60]}")
    print()

print("\n" + "="*80)
print(f"OTHER CANDIDATES: {len(other_candidates)} found")
print("="*80)
print("\nTop 20 Other candidates (sorted by relevance):\n")

for i, (idx, row) in enumerate(other_candidates.head(20).iterrows(), 1):
    print(f"{i:2d}. {row['timestamp'][:10]} | {row['amount']:7.2f} | {row['merchant'][:40]}")
    print(f"    >>> {row['description'][:60]}")
    print()

# Save for detailed review
travel_candidates.head(30)[['timestamp', 'merchant', 'description', 'amount', 'category', 'confidence']].to_csv(
    'TOP_TRAVEL_CANDIDATES.csv', index=False, encoding='utf-8'
)

other_candidates.head(30)[['timestamp', 'merchant', 'description', 'amount', 'category', 'confidence']].to_csv(
    'TOP_OTHER_CANDIDATES.csv', index=False, encoding='utf-8'
)

print("\n[OK] Saved to TOP_TRAVEL_CANDIDATES.csv and TOP_OTHER_CANDIDATES.csv")
