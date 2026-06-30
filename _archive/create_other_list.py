"""Create a curated list of "Other" candidates for manual approval."""
import pandas as pd

df_all = pd.read_csv('data/processed/transactions_classified.csv')
df_labeled = pd.read_csv('data/labeled/labeled_transactions.csv')

# Start with current "Other" examples
current_other = df_labeled[df_labeled['category'] == 'Other'].copy()

# Add hand-picked candidates from low-confidence that are clearly "Other"
# These are from our manual review above
clear_other_picks = [
    '2025-08-23 20:17:06',  # shared massage chair
    '2025-08-31 14:20:30',  # variety store
    '2025-09-17 15:38:45',  # government payment
    '2025-09-13 12:54:18',  # photo/service
]

clear_picks = df_all[df_all['timestamp'].isin(clear_other_picks)].copy()

print(f"Current 'Other' labels: {len(current_other)}")
print(f"Clear new picks: {len(clear_picks)}")

# Find more: ambiguous/misc keywords
other_keywords = [
    '相机', '照相', '摄影',  # photo
    '杂物', '杂货',  # misc
    '证件', '公章',  # documents
    '卡', '会员',  # memberships
    '服务',  # services
    'service', 'fee', 'subscription'
]

df_all['text_lower'] = (df_all['merchant'] + ' ' + df_all['description']).str.lower()
has_other_kw = df_all['text_lower'].str.contains('|'.join(other_keywords), na=False)

more_candidates = df_all[
    has_other_kw &
    ~df_all['timestamp'].isin(current_other['timestamp']) &
    ~df_all['timestamp'].isin(clear_picks['timestamp'])
].copy()

more_candidates = more_candidates.sort_values('confidence', ascending=True)[:15]

print(f"Additional keyword matches: {len(more_candidates)}")

# Combine all
all_candidates = pd.concat([current_other, clear_picks, more_candidates], ignore_index=True)
all_candidates = all_candidates.drop_duplicates(subset=['timestamp'])

# Export with approval column
export = all_candidates[[
    'timestamp', 'merchant', 'description', 'amount', 'category'
]].copy()

export['APPROVE_AS_OTHER'] = ''
export = export.sort_values('timestamp')

export.to_csv('REVIEW_OTHER_ITEMS.csv', index=False, encoding='utf-8')

print(f"\n[OK] Exported {len(export)} items to REVIEW_OTHER_ITEMS.csv")
print("\nINSTRUCTIONS:")
print("1. Open REVIEW_OTHER_ITEMS.csv")
print("2. For items you CONFIRM are 'Other', put 'yes' in APPROVE_AS_OTHER")
print("3. DELETE rows you don't approve (these stay as their current category)")
print("4. Save and close the file")
print("5. Run: python src/apply_other_labels.py")

