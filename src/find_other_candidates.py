"""Find candidates for "Other" category labeling."""
import pandas as pd
import joblib
from pathlib import Path
import sys
sys.path.insert(0, str(Path.cwd()))

from segment import clean_text, vectorize


def find_other_candidates(labeled_df, classified_df, n_candidates=30):
    """Find transactions that might belong to "Other" category.

    Strategy:
    1. Low-confidence predictions (< 0.70) that aren't already "Other"
    2. Transactions with merchant/description patterns not matching main categories
    3. Sort by confidence to get most ambiguous first
    """

    # Get currently labeled "Other" examples
    other_labeled = labeled_df[labeled_df['category'] == 'Other']
    print(f"Currently labeled 'Other' examples: {len(other_labeled)}")
    if len(other_labeled) > 0:
        print("  Examples:")
        for idx, (_, row) in enumerate(other_labeled[['merchant', 'description']].head(5).iterrows()):
            try:
                print(f"    - {row['merchant'][:35]} | {row['description'][:40]}")
            except:
                print(f"    - (unicode text)")

    # Find low-confidence predictions that might be "Other"
    low_conf = classified_df[classified_df['confidence'] < 0.70].copy()
    low_conf = low_conf.sort_values('confidence')

    print(f"\nLow-confidence predictions (<0.70): {len(low_conf)}")

    # Filter to get candidates (exclude ones already confident in "Other")
    candidates = low_conf[low_conf['category'] != 'Other'].head(n_candidates)

    if len(candidates) > 0:
        # Save to CSV for manual review
        output_path = 'OTHER_CANDIDATES_TO_LABEL.csv'
        candidates[['timestamp', 'merchant', 'description', 'amount', 'source', 'category', 'confidence']].to_csv(
            output_path, index=False
        )
        print(f"\nSaved {len(candidates)} candidates to {output_path}")
        print("\nTOP 10 CANDIDATES (most ambiguous):")
        for idx, (_, row) in enumerate(candidates[['merchant', 'description', 'category', 'confidence']].head(10).iterrows()):
            try:
                print(f"  {idx+1}. {row['merchant'][:30]} | {row['description'][:30]}")
                print(f"     Current: {row['category']:20s} | Confidence: {row['confidence']:.1%}")
            except:
                print(f"  {idx+1}. (unicode text)")
                print(f"     Current: {row['category']:20s} | Confidence: {row['confidence']:.1%}")
    else:
        print("\nNo low-confidence candidates found. Model is confident in its predictions!")
        # Fall back: show high-value "Other" candidates
        print("\nFinding high-value transactions as potential 'Other' examples...")
        high_value = classified_df[classified_df['amount'] > classified_df['amount'].quantile(0.75)].copy()
        high_value = high_value.sort_values('amount', ascending=False)

        candidates = high_value.head(n_candidates)
        output_path = 'OTHER_CANDIDATES_TO_LABEL.csv'
        candidates[['timestamp', 'merchant', 'description', 'amount', 'source', 'category', 'confidence']].to_csv(
            output_path, index=False
        )
        print(f"Saved {len(candidates)} high-value candidates to {output_path}")


if __name__ == '__main__':
    print("="*70)
    print("FINDING 'OTHER' CATEGORY CANDIDATES FOR LABELING")
    print("="*70)

    # Load data
    labeled_df = pd.read_csv('data/labeled/labeled_transactions.csv')
    classified_df = pd.read_csv('data/processed/transactions_classified.csv')

    print(f"\nLoaded {len(labeled_df)} labeled transactions")
    print(f"Loaded {len(classified_df)} classified transactions")

    # Find candidates
    find_other_candidates(labeled_df, classified_df, n_candidates=30)

    print(f"\n{'='*70}")
    print("NEXT STEP: Review OTHER_CANDIDATES_TO_LABEL.csv")
    print("Mark transactions you think belong to 'Other' category, then")
    print("copy them to data/labeled/labeled_transactions.csv and retrain")
    print(f"{'='*70}")
