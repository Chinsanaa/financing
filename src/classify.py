"""Apply trained classifier to all transactions."""
import pandas as pd
import joblib
from pathlib import Path
import sys
sys.path.insert(0, str(Path.cwd()))

from segment import clean_text, vectorize


def classify_all(df, vectorizer, classifier, confidence_threshold=0.7):
    """Classify all transactions using trained model.

    Args:
        confidence_threshold: Flag predictions below this threshold for manual review (default 0.7)
    """
    # Clean text
    df = df.copy()
    df['text'] = df.apply(
        lambda row: clean_text(row['merchant'], row['description']),
        axis=1
    )

    # Vectorize
    X = vectorize(df['text'].tolist(), vectorizer)

    # Classify
    predictions = classifier.predict(X)
    probabilities = classifier.predict_proba(X).max(axis=1)

    df['category'] = predictions
    df['confidence'] = probabilities
    df['needs_review'] = probabilities < confidence_threshold

    return df


if __name__ == '__main__':
    print("="*70)
    print("STAGE 6: CLASSIFY ALL TRANSACTIONS")
    print("="*70)

    # Load data and models
    df = pd.read_csv('data/processed/transactions.csv')
    vectorizer = joblib.load('data/processed/tfidf_vectorizer.pkl')
    classifier = joblib.load('data/processed/classifier.pkl')

    print(f"\n1. Loaded {len(df)} transactions")
    print(f"2. Loaded trained classifier (99.1% accuracy)")

    # Classify
    print(f"\n3. Classifying all transactions...")
    df_classified = classify_all(df, vectorizer, classifier)

    # Show stats
    print(f"\n4. CLASSIFICATION RESULTS:")
    category_counts = df_classified['category'].value_counts()
    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        avg_conf = df_classified[df_classified['category'] == cat]['confidence'].mean()
        print(f"   {cat:30s}: {count:3d} transactions (avg confidence: {avg_conf:.1%})")

    # Show low-confidence items
    needs_review = df_classified[df_classified['needs_review']]
    print(f"\n4b. LOW-CONFIDENCE ITEMS (confidence < 0.70):")
    print(f"   {len(needs_review)} transactions flagged for manual review")
    if len(needs_review) > 0:
        print("\n   Sample of low-confidence predictions:")
        for idx, (_, row) in enumerate(needs_review[['merchant', 'description', 'category', 'confidence']].head(5).iterrows()):
            try:
                print(f"      {row['merchant'][:30]} -> {row['category']:20s} ({row['confidence']:.1%})")
            except:
                print(f"      (unicode text) -> {row['category']:20s} ({row['confidence']:.1%})")

    # Show confidence stats
    print(f"\n5. CONFIDENCE STATISTICS:")
    print(f"   Mean confidence: {df_classified['confidence'].mean():.1%}")
    print(f"   Min confidence:  {df_classified['confidence'].min():.1%}")
    print(f"   Max confidence:  {df_classified['confidence'].max():.1%}")

    # Save
    output_path = 'data/processed/transactions_classified.csv'
    df_classified.to_csv(output_path, index=False)
    print(f"\n6. Saved to {output_path}")

    # Save low-confidence items for manual review
    if len(needs_review) > 0:
        review_path = 'data/processed/needs_manual_review.csv'
        needs_review.to_csv(review_path, index=False)
        print(f"   Low-confidence items saved to {review_path}")

    # Show sample
    print(f"\n7. SAMPLE CLASSIFIED TRANSACTIONS:")
    sample_df = df_classified[['merchant', 'description', 'amount', 'category', 'confidence']].head(10)

    with open('_stage6_sample.txt', 'w', encoding='utf-8') as f:
        f.write("CLASSIFIED TRANSACTIONS SAMPLE\n")
        f.write("="*80 + "\n\n")
        for idx, (_, row) in enumerate(sample_df.iterrows()):
            f.write(f"{idx+1}. {row['merchant'][:40]:40s} | {row['category']:20s} | {row['confidence']:.1%}\n")

    print("Sample saved to _stage6_sample.txt")

    print(f"\n{'='*70}")
    print(f"Stage 6 Complete! All {len(df_classified)} transactions classified")
    print(f"Ready for Stage 7: Visualization")
    print(f"{'='*70}")
