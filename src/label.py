"""Rule-based pre-labeling and interactive labeling for transactions."""
import pandas as pd
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from categories import LABEL_CATEGORIES

CATEGORIES = LABEL_CATEGORIES


def load_merchant_rules(rules_path: str) -> dict:
    """Load merchant→category mapping from CSV."""
    df = pd.read_csv(rules_path)
    rules = {}
    for _, row in df.iterrows():
        pattern = row['merchant_pattern'].strip()
        category = row['category'].strip()
        rules[pattern.lower()] = category
    return rules


def apply_merchant_rules(df: pd.DataFrame, rules: dict) -> pd.DataFrame:
    """
    Apply merchant rules to transactions.

    Returns DataFrame with added columns:
    - 'category': assigned category (or NaN if no rule matched)
    - 'labeled': True if rule matched, False if unlabeled
    """
    df = df.copy()
    df['category'] = pd.NA
    df['labeled'] = False

    for idx, row in df.iterrows():
        merchant = str(row['merchant']).strip().lower()

        # Try exact match first
        if merchant in rules:
            df.loc[idx, 'category'] = rules[merchant]
            df.loc[idx, 'labeled'] = True
            continue

        # Try substring match (pattern appears in merchant name)
        for pattern, category in rules.items():
            if pattern in merchant:
                df.loc[idx, 'category'] = category
                df.loc[idx, 'labeled'] = True
                break

    return df


def show_labeling_stats(df: pd.DataFrame) -> None:
    """Show how many transactions were auto-labeled."""
    total = len(df)
    labeled = (df['labeled'] == True).sum()
    unlabeled = (df['labeled'] == False).sum()

    print(f"\n{'='*70}")
    print(f"LABELING RESULTS")
    print(f"{'='*70}")
    print(f"Total transactions: {total}")
    print(f"Auto-labeled: {labeled} ({100*labeled/total:.1f}%)")
    print(f"Remaining unlabeled: {unlabeled} ({100*unlabeled/total:.1f}%)")

    print(f"\n{'Category Breakdown (auto-labeled):':^70}")
    print("-" * 70)
    for category in CATEGORIES:
        count = ((df['category'] == category) & (df['labeled'] == True)).sum()
        if count > 0:
            print(f"  {category:30s}: {count:3d} transactions")

    print(f"\n\nSample of auto-labeled transactions:")
    print("-" * 70)

    # Show 5 random labeled examples
    labeled_df = df[df['labeled'] == True].sample(min(5, len(df[df['labeled'] == True])))

    sample_path = Path('output/samples/_labeling_sample.txt')
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    with open(sample_path, 'w', encoding='utf-8') as f:
        for idx, (_, row) in enumerate(labeled_df.iterrows()):
            f.write(f"\n{idx+1}. Merchant: {row['merchant']}\n")
            f.write(f"   Category: {row['category']}\n")

    print(f"Sample written to {sample_path}")


def interactive_label(df: pd.DataFrame, output_path: str) -> None:
    """
    Interactive labeling for unlabeled transactions.

    Groups by merchant so you only label each unique merchant once.
    Saves progress after each transaction.
    """
    unlabeled = df[df['labeled'] == False].copy()

    if len(unlabeled) == 0:
        print("All transactions already labeled!")
        return

    # Group by merchant
    merchant_groups = unlabeled.groupby('merchant')
    unique_merchants = list(merchant_groups.groups.keys())

    print(f"\n{'='*70}")
    print(f"INTERACTIVE LABELING")
    print(f"{'='*70}")
    print(f"You have {len(unique_merchants)} unique unlabeled merchants to categorize.")
    print(f"(Each merchant only needs to be labeled once)")
    print(f"\nAvailable categories:")
    for i, cat in enumerate(CATEGORIES):
        print(f"  {i}: {cat}")

    df_copy = df.copy()
    labeled_count = 0

    for i, merchant in enumerate(unique_merchants):
        group = merchant_groups.get_group(merchant)
        example_row = group.iloc[0]

        print(f"\n{'-'*70}")
        print(f"Merchant {i+1}/{len(unique_merchants)}: {merchant}")
        print(f"  Sample description: {example_row['description'][:70]}")
        print(f"  Number of transactions: {len(group)}")

        while True:
            try:
                cat_idx = int(input("  Enter category (0-9) or -1 to skip: "))
                if cat_idx == -1:
                    break
                if 0 <= cat_idx < len(CATEGORIES):
                    category = CATEGORIES[cat_idx]
                    df_copy.loc[group.index, 'category'] = category
                    df_copy.loc[group.index, 'labeled'] = True
                    labeled_count += len(group)
                    print(f"  -> Labeled as '{category}'")
                    break
                else:
                    print(f"  Invalid choice. Enter 0-{len(CATEGORIES)-1} or -1.")
            except ValueError:
                print(f"  Invalid input. Enter 0-{len(CATEGORIES)-1} or -1.")

        # Save progress
        df_copy.to_csv(output_path, index=False)

    print(f"\n{'='*70}")
    print(f"Labeling complete! Labeled {labeled_count} additional transactions.")
    print(f"Saved to {output_path}")


if __name__ == '__main__':
    # Stage 3a + 3b: Apply merchant rules
    print("="*70)
    print("STAGE 3: RULE-BASED PRE-LABELING")
    print("="*70)

    df = pd.read_csv('data/processed/transactions.csv')
    rules = load_merchant_rules('data/labeled/merchant_rules_expanded.csv')

    print(f"\nLoaded {len(rules)} merchant rules")
    print(f"Applying rules to {len(df)} transactions...")

    df_labeled = apply_merchant_rules(df, rules)
    show_labeling_stats(df_labeled)

    # Save auto-labeled data
    df_labeled.to_csv('data/intermediate/transactions_auto_labeled.csv', index=False)
    print(f"\nSaved auto-labeled data to data/intermediate/transactions_auto_labeled.csv")

    # Optionally run interactive labeling for remaining
    unlabeled_count = (df_labeled['labeled'] == False).sum()
    if unlabeled_count > 0:
        response = input(f"\n{unlabeled_count} transactions still unlabeled. Start interactive labeling? (y/n): ")
        if response.lower() == 'y':
            interactive_label(df_labeled, 'data/labeled/labeled_transactions.csv')
