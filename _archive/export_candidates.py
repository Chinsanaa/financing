"""Export Travel and Other candidates to spreadsheet for manual review."""
import pandas as pd

# Load current data
df_all = pd.read_csv('data/processed/transactions_classified.csv')
df_labeled = pd.read_csv('data/labeled/labeled_transactions.csv')

# Get IDs already labeled
travel_labeled = set(df_labeled[df_labeled['category'] == 'Travel']['timestamp'])
other_labeled = set(df_labeled[df_labeled['category'] == 'Other']['timestamp'])
already_labeled = travel_labeled | other_labeled

# Find candidates
df_all['text_lower'] = (df_all['merchant'] + ' ' + df_all['description']).str.lower()

travel_keywords = [
    'health', 'visa', 'passport', 'travel', 'hotel', 'flight',
    'ticket', 'booking', 'airbnb', 'airport', 'airline', 'train',
    '旅行', '酒店', '机票', '火车', '客运', '健康'
]

other_keywords = [
    '缴费', '政府', '公共', '卡', '通办', '手工', '共享', '按摩',
    'fee', 'government', 'payment', 'platform'
]

has_travel_kw = df_all['text_lower'].str.contains('|'.join(travel_keywords), na=False)
has_other_kw = df_all['text_lower'].str.contains('|'.join(other_keywords), na=False)
low_confidence = df_all['confidence'] < 0.65

candidates_travel = df_all[
    (has_travel_kw | low_confidence) &
    ~df_all['timestamp'].isin(already_labeled)
].copy()

candidates_other = df_all[
    (has_other_kw | (low_confidence & ~has_travel_kw)) &
    ~df_all['timestamp'].isin(already_labeled)
].copy()

# Sort by likelihood (has keyword = higher priority)
candidates_travel['has_keyword'] = has_travel_kw[candidates_travel.index]
candidates_travel = candidates_travel.sort_values(['has_keyword', 'confidence'], ascending=[False, True])

candidates_other['has_keyword'] = has_other_kw[candidates_other.index]
candidates_other = candidates_other.sort_values(['has_keyword', 'confidence'], ascending=[False, True])

# Create export with labeling column
travel_export = candidates_travel[[
    'timestamp', 'merchant', 'description', 'amount', 'source', 'category', 'confidence'
]].head(50).copy()
travel_export['LABEL_AS_TRAVEL'] = ''
travel_export.to_csv('review_travel_candidates.csv', index=False, encoding='utf-8')

other_export = candidates_other[[
    'timestamp', 'merchant', 'description', 'amount', 'source', 'category', 'confidence'
]].head(50).copy()
other_export['LABEL_AS_OTHER'] = ''
other_export.to_csv('review_other_candidates.csv', index=False, encoding='utf-8')

print(f"[OK] Exported {len(travel_export)} Travel candidates to review_travel_candidates.csv")
print(f"[OK] Exported {len(other_export)} Other candidates to review_other_candidates.csv")
print(f"\nTotal candidates available:")
print(f"  Travel: {len(candidates_travel)}")
print(f"  Other:  {len(candidates_other)}")
print("\nINSTRUCTIONS:")
print("1. Open review_travel_candidates.csv and review_other_candidates.csv")
print("2. For each transaction, put 'yes' in the label column if it matches the category")
print("3. Save the files")
print("4. Run: python src/process_labels.py")
