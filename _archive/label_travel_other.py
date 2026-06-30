"""Interactive labeling tool for Travel and Other categories.

This script finds candidate transactions that might be Travel or Other,
and lets you manually review and label them one at a time.
"""
import pandas as pd
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

def find_candidates():
    """Find candidates for Travel and Other labeling."""

    # Load current data
    df_all = pd.read_csv('data/processed/transactions_classified.csv')
    df_labeled = pd.read_csv('data/labeled/labeled_transactions.csv')

    # Get IDs already labeled as Travel or Other
    travel_labeled = set(df_labeled[df_labeled['category'] == 'Travel']['timestamp'])
    other_labeled = set(df_labeled[df_labeled['category'] == 'Other']['timestamp'])
    already_labeled = travel_labeled | other_labeled

    # Find candidates: low confidence OR merchants with Travel/Other keywords
    df_all['text_lower'] = (df_all['merchant'] + ' ' + df_all['description']).str.lower()

    # Travel keywords: health checks, visa, passport, hotel, flight, ticket, etc.
    travel_keywords = [
        'health', 'visa', 'passport', 'travel', 'hotel', 'flight',
        'ticket', 'booking', 'airbnb', 'airport', 'airline', 'train',
        '旅行', '酒店', '机票', '火车', '客运', '健康'
    ]

    # Other keywords: government fees, services, misc
    other_keywords = [
        '缴费', '政府', '公共', '卡', '通办', '手工', '共享', '按摩',
        'fee', 'government', 'payment', 'platform'
    ]

    # Find candidates
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

    return candidates_travel, candidates_other


def interactive_label():
    """Interactively label transactions."""

    candidates_travel, candidates_other = find_candidates()

    print("="*80)
    print("INTERACTIVE TRAVEL & OTHER LABELING")
    print("="*80)
    print(f"\nFound {len(candidates_travel)} potential Travel candidates")
    print(f"Found {len(candidates_other)} potential Other candidates")
    print(f"\nTotal to review: {len(candidates_travel) + len(candidates_other)}")

    # Load labeled data to append to
    df_labeled = pd.read_csv('data/labeled/labeled_transactions.csv')

    labeled_count = 0

    # Start with Travel
    print("\n" + "="*80)
    print("TRAVEL CANDIDATES (look for: flights, hotels, visas, travel health checks)")
    print("="*80)

    for idx, row in candidates_travel.iterrows():
        print(f"\n[{labeled_count + 1}]")
        print(f"  Date:       {row['timestamp']}")
        print(f"  Merchant:   {row['merchant']}")
        print(f"  Amount:     ¥{row['amount']:.2f}")
        print(f"  Current:    {row['category']} (confidence: {row['confidence']:.1%})")

        while True:
            choice = input("\nIs this Travel? (y/n/skip): ").strip().lower()
            if choice == 'y':
                df_labeled = pd.concat([df_labeled, pd.DataFrame([{
                    'timestamp': row['timestamp'],
                    'merchant': row['merchant'],
                    'description': row['description'],
                    'amount': row['amount'],
                    'source': row['source'],
                    'category': 'Travel',
                    'labeled': True
                }])], ignore_index=True)
                labeled_count += 1
                print("  ✓ Labeled as Travel")
                break
            elif choice == 'n':
                print("  Skipped (not Travel)")
                break
            elif choice == 'skip':
                print("  Skipped")
                break
            else:
                print("  Invalid input. Enter y/n/skip")

    # Then Other
    print("\n" + "="*80)
    print("OTHER CANDIDATES (look for: ambiguous, one-off, misc, government fees)")
    print("="*80)

    for idx, row in candidates_other.iterrows():
        print(f"\n[{labeled_count + 1}]")
        print(f"  Date:       {row['timestamp']}")
        print(f"  Merchant:   {row['merchant']}")
        print(f"  Amount:     ¥{row['amount']:.2f}")
        print(f"  Current:    {row['category']} (confidence: {row['confidence']:.1%})")

        while True:
            choice = input("\nIs this Other? (y/n/skip): ").strip().lower()
            if choice == 'y':
                df_labeled = pd.concat([df_labeled, pd.DataFrame([{
                    'timestamp': row['timestamp'],
                    'merchant': row['merchant'],
                    'description': row['description'],
                    'amount': row['amount'],
                    'source': row['source'],
                    'category': 'Other',
                    'labeled': True
                }])], ignore_index=True)
                labeled_count += 1
                print("  ✓ Labeled as Other")
                break
            elif choice == 'n':
                print("  Skipped (not Other)")
                break
            elif choice == 'skip':
                print("  Skipped")
                break
            else:
                print("  Invalid input. Enter y/n/skip")

    # Save results
    if labeled_count > 0:
        print("\n" + "="*80)
        print(f"SUMMARY: Labeled {labeled_count} transactions")
        print("="*80)

        # Remove duplicates and save
        df_labeled = df_labeled.drop_duplicates(subset=['timestamp'], keep='last')
        df_labeled.to_csv('data/labeled/labeled_transactions.csv', index=False)
        print(f"✓ Saved to data/labeled/labeled_transactions.csv")
        print(f"  Total labeled transactions: {len(df_labeled)}")
    else:
        print("\nNo new transactions labeled.")


if __name__ == '__main__':
    interactive_label()
