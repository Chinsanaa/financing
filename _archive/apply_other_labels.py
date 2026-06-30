"""Apply approved Other labels to the training data."""
import pandas as pd

# Read the reviewed items
review_df = pd.read_csv('REVIEW_OTHER_ITEMS.csv')

# Read current labeled data
df_labeled = pd.read_csv('data/labeled/labeled_transactions.csv')

# Read all transactions (for full data)
df_all = pd.read_csv('data/processed/transactions_classified.csv')

# Apply approvals: items with "yes" in APPROVE_AS_OTHER
approved = review_df[review_df['APPROVE_AS_OTHER'] == 'yes'].copy()

print(f"Processing {len(approved)} approved items...")

# Update labeled data
for idx, row in approved.iterrows():
    ts = row['timestamp']

    # Remove any existing entries for this timestamp
    df_labeled = df_labeled[df_labeled['timestamp'] != ts]

    # Add as Other
    new_entry = {
        'timestamp': ts,
        'merchant': row['merchant'],
        'description': row['description'],
        'amount': row['amount'],
        'source': df_all[df_all['timestamp'] == ts]['source'].values[0] if ts in df_all['timestamp'].values else 'unknown',
        'category': 'Other',
        'labeled': True
    }
    df_labeled = pd.concat([df_labeled, pd.DataFrame([new_entry])], ignore_index=True)
    print(f"  [Other] {ts}")

# Also handle specific reclassifications:
# Row 8 (Hellobike) stays Transportation - no action needed
# Rows 15-16 (Taobao) change from Eating Out to Shopping
taobao_timestamps = ['2026-04-16 20:05:28', '2026-05-11 22:16:42']
for ts in taobao_timestamps:
    mask = df_labeled['timestamp'] == ts
    if mask.any():
        df_labeled.loc[mask, 'category'] = 'Shopping'
        print(f"  [Shopping] {ts} | Taobao membership (reclassified)")

# Remove duplicates and save
df_labeled = df_labeled.drop_duplicates(subset=['timestamp'], keep='last')
df_labeled = df_labeled.sort_values('timestamp')

df_labeled.to_csv('data/labeled/labeled_transactions.csv', index=False, encoding='utf-8')

print(f"\n[OK] Updated labeled_transactions.csv")
print(f"Total labeled transactions: {len(df_labeled)}")

# Show new distribution
print(f"\nNew category distribution:")
for cat, count in df_labeled['category'].value_counts().sort_values(ascending=False).items():
    print(f"  {cat:30s}: {count:3d}")

