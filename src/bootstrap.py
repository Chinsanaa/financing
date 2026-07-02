"""First-run setup for new users: parse exports, seed rules, suggest labels, train, classify."""
import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from categories import (
    CATEGORY_NORMALIZE,
    FORECAST_MONTHS,
    MIN_SAMPLES_PER_CLASS,
    MIN_TRAINING_SAMPLES,
    ML_CATEGORIES,
)
from label import apply_merchant_rules, load_merchant_rules
from parse import load_transactions, resolve_raw_paths, save_processed
from paths import (
    BUDGET_CONFIG,
    BUDGET_EXAMPLE,
    CLASSIFIER,
    EXPORTS,
    LABELED,
    LABELED_TXNS,
    MERCHANT_RULES,
    MERCHANTS_TO_LABEL,
    PROCESSED,
    RAW,
    STARTER_RULES,
    TRANSACTIONS,
    TRANSACTIONS_CLASSIFIED,
)
from classify import classify_all, load_models, save_classification_outputs
from retrain import retrain_model


def ensure_dirs():
    for d in (RAW, LABELED, PROCESSED, EXPORTS):
        d.mkdir(parents=True, exist_ok=True)


def ensure_user_files(force_rules: bool = False):
    """Copy starter templates into user data paths when missing."""
    if not MERCHANT_RULES.exists() or force_rules:
        shutil.copy(STARTER_RULES, MERCHANT_RULES)
        action = "Reset" if force_rules else "Created"
        print(f"  {action} {MERCHANT_RULES.name} from starter rules ({_count_rules()} patterns)")

    if not LABELED_TXNS.exists():
        pd.DataFrame(columns=[
            'timestamp', 'merchant', 'description', 'amount', 'source', 'category', 'labeled',
        ]).to_csv(LABELED_TXNS, index=False)
        print(f"  Created empty {LABELED_TXNS.name}")

    if not BUDGET_CONFIG.exists():
        shutil.copy(BUDGET_EXAMPLE, BUDGET_CONFIG)
        print(f"  Created {BUDGET_CONFIG.name} from template")


def _count_rules() -> int:
    return len(load_merchant_rules(str(STARTER_RULES)))


def parse_exports() -> pd.DataFrame:
    base = Path(__file__).parent.parent
    alipay_path, wechat_path, additional = resolve_raw_paths(base)
    if not alipay_path and not wechat_path and not additional:
        raise FileNotFoundError(
            "No export files found in data/raw/.\n"
            "  Add alipay.csv and/or raw-wechat.xlsx (see data/raw/README.md)"
        )
    df = load_transactions(
        str(alipay_path) if alipay_path else None,
        str(wechat_path) if wechat_path else None,
        additional_sources=additional,
        raw_dir=base / 'data' / 'raw',
    )
    save_processed(df, str(TRANSACTIONS))
    return df


def normalize_category(cat: str) -> str:
    cat = str(cat).strip()
    return CATEGORY_NORMALIZE.get(cat, cat)


def seed_labeled_from_rules(df: pd.DataFrame, rules: dict) -> pd.DataFrame:
    """Auto-add rule-matched transactions to training data (cold-start bootstrap)."""
    ruled = apply_merchant_rules(df, rules)
    matched = ruled[ruled['labeled'] == True].copy()
    matched['category'] = matched['category'].map(normalize_category)
    matched = matched[matched['category'].isin(ML_CATEGORIES)]

    seed = matched[['timestamp', 'merchant', 'description', 'amount', 'source', 'category']].copy()
    seed['labeled'] = True
    return seed


def _txn_key_series(frame: pd.DataFrame) -> pd.Series:
    ts = pd.to_datetime(frame['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
    return (
        ts + '|' + frame['merchant'].astype(str) + '|'
        + frame['amount'].astype(str) + '|' + frame['source'].astype(str)
    )


def dedupe_labeled(df: pd.DataFrame) -> pd.DataFrame:
    """One row per transaction; keep first (manual labels beat later rule seeds)."""
    if df.empty:
        return df
    df = df.copy()
    df['_key'] = _txn_key_series(df)
    df = df.drop_duplicates(subset='_key', keep='first')
    return df.drop(columns='_key')


def merge_labeled(existing: pd.DataFrame, seed: pd.DataFrame) -> pd.DataFrame:
    """Merge seed rows without duplicating same transaction."""
    if seed.empty:
        return dedupe_labeled(existing)
    if existing.empty:
        return seed

    existing = dedupe_labeled(existing)
    seed = seed.copy()
    existing_keys = set(_txn_key_series(existing))
    seed = seed[~_txn_key_series(seed).isin(existing_keys)]
    return pd.concat([existing, seed], ignore_index=True)


def export_merchants_to_label(df: pd.DataFrame, rules: dict, top_n: int = 40) -> Path:
    """Export top unlabeled merchants for the user to categorize."""
    ruled = apply_merchant_rules(df, rules)
    unlabeled = ruled[ruled['labeled'] == False]
    if unlabeled.empty:
        print("  All merchants matched by rules - nothing to export.")
        return MERCHANTS_TO_LABEL

    stats = (
        unlabeled.groupby('merchant')
        .agg(count=('amount', 'size'), total_spend=('amount', 'sum'),
             sample_description=('description', 'first'))
        .sort_values('count', ascending=False)
        .head(top_n)
        .reset_index()
    )
    stats['suggested_category'] = ''
    stats['notes'] = ''

    EXPORTS.mkdir(parents=True, exist_ok=True)
    stats.to_csv(MERCHANTS_TO_LABEL, index=False, encoding='utf-8-sig')
    print(f"  Exported {len(stats)} merchants -> {MERCHANTS_TO_LABEL}")
    return MERCHANTS_TO_LABEL


def apply_merchants_to_label(rules_path: Path = MERCHANT_RULES) -> int:
    """Read merchants_to_label.csv and append filled rows to merchant rules."""
    if not MERCHANTS_TO_LABEL.exists():
        return 0

    todo = pd.read_csv(MERCHANTS_TO_LABEL)
    if 'suggested_category' not in todo.columns:
        return 0

    filled = todo[todo['suggested_category'].astype(str).str.strip() != ''].copy()
    if filled.empty:
        return 0

    rules_df = pd.read_csv(rules_path)
    new_rows = []
    for _, row in filled.iterrows():
        cat = normalize_category(str(row['suggested_category']).strip())
        if cat not in ML_CATEGORIES:
            continue
        pattern = str(row['merchant']).strip()
        if pattern and pattern not in rules_df['merchant_pattern'].values:
            new_rows.append({'merchant_pattern': pattern, 'category': cat})

    if not new_rows:
        return 0

    rules_df = pd.concat([rules_df, pd.DataFrame(new_rows)], ignore_index=True)
    rules_df.to_csv(rules_path, index=False)
    print(f"  Added {len(new_rows)} merchant rules from {MERCHANTS_TO_LABEL.name}")
    return len(new_rows)


def generate_budget_from_spend(df_classified: pd.DataFrame, monthly_income: Optional[float] = None):
    """Fill budget_config.json using actual spend averages (+10% headroom)."""
    with open(BUDGET_CONFIG, encoding='utf-8') as f:
        config = json.load(f)

    if monthly_income is not None:
        config['income'] = monthly_income

    df = df_classified.copy()
    df['month'] = pd.to_datetime(df['timestamp']).dt.to_period('M')
    monthly = df.groupby(['month', 'category'])['amount'].sum().unstack(fill_value=0)

    for cat in ML_CATEGORIES:
        if cat not in config['categories']:
            config['categories'][cat] = {
                'type': 'Want',
                'avg_monthly': 0,
                'monthly_budget': 200,
                'annual_budget': 2400,
                'monthly': [],
            }

        if cat in monthly.columns and monthly[cat].sum() > 0:
            avg = float(monthly[cat].mean())
            budget = round(avg * 1.1, 0)
        else:
            avg = 0.0
            budget = config['categories'][cat].get('monthly_budget', 200)

        entry = config['categories'][cat]
        entry['avg_monthly'] = avg
        entry['monthly_budget'] = budget
        entry['annual_budget'] = budget * 12
        # Pad forecast months with budget target
        entry['monthly'] = [budget] * len(FORECAST_MONTHS)

    config['total_budget'] = sum(
        c.get('annual_budget', 0) for c in config['categories'].values()
    )

    with open(BUDGET_CONFIG, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"  Updated {BUDGET_CONFIG.name} from spend history")


def can_train(labeled_df: pd.DataFrame) -> Tuple[bool, str]:
    labeled = labeled_df[labeled_df['labeled'] == True]
    labeled = labeled[labeled['category'].isin(ML_CATEGORIES)]
    n = len(labeled)
    if n < MIN_TRAINING_SAMPLES:
        return False, f"need {MIN_TRAINING_SAMPLES}+ labeled rows (have {n})"

    counts = labeled['category'].value_counts()
    thin = counts[counts < MIN_SAMPLES_PER_CLASS]
    if len(thin) > 0:
        return False, f"some categories have <{MIN_SAMPLES_PER_CLASS} samples: {list(thin.index)}"
    return True, f"{n} labeled samples ready"


def run_bootstrap(income: Optional[float] = None, force_rules: bool = False, skip_train: bool = False):
    print("=" * 70)
    print("FIRST-RUN SETUP (bootstrap)")
    print("=" * 70)

    ensure_dirs()
    print("\n1. User data files")
    ensure_user_files(force_rules=force_rules)

    print("\n2. Parse Alipay / WeChat exports")
    df = parse_exports()
    print(f"   Loaded {len(df)} transactions")

    rules = load_merchant_rules(str(MERCHANT_RULES))
    apply_merchants_to_label()

    print("\n3. Seed training data from merchant rules")
    seed = seed_labeled_from_rules(df, rules)
    existing = pd.read_csv(LABELED_TXNS) if LABELED_TXNS.exists() else pd.DataFrame()
    merged = merge_labeled(existing, seed)
    merged.to_csv(LABELED_TXNS, index=False)
    ruled_count = (merged['labeled'] == True).sum() if 'labeled' in merged.columns else 0
    print(f"   {ruled_count} labeled training rows ({len(seed)} from rules this run)")

    print("\n4. Export merchants still needing labels")
    export_merchants_to_label(df, load_merchant_rules(str(MERCHANT_RULES)))

    ok, msg = can_train(merged)
    print(f"\n5. Train classifier - {msg}")
    if not skip_train and ok:
        retrain_model()
    elif not ok:
        print("   Skipping train (rules-only mode until you label more).")
        print(f"   Fill suggested_category in {MERCHANTS_TO_LABEL.name}, re-run bootstrap.")

    print("\n6. Classify all transactions")
    vectorizer, classifier = load_models()
    df_classified = classify_all(df, vectorizer, classifier, rules=rules)
    save_classification_outputs(df_classified)

    n_rules = (df_classified['confidence'] == 1.0).sum()
    n_review = df_classified['needs_review'].sum()
    print(f"   Rule matches: {n_rules}/{len(df_classified)}")
    print(f"   Flagged for review: {n_review}")

    print("\n7. Budget config")
    generate_budget_from_spend(df_classified, monthly_income=income)

    print("\n" + "=" * 70)
    print("SETUP COMPLETE")
    print("=" * 70)
    print("\nNext steps:")
    print(f"  1. Open {MERCHANTS_TO_LABEL.name} - fill suggested_category for your top merchants")
    print("  2. Re-run:  python src/bootstrap.py")
    print(f"  3. Review:   {PROCESSED / 'needs_manual_review.csv'}")
    print("  4. Dashboard: streamlit run src/dashboard.py")
    print("\nExpect ~75-85% category accuracy on day one; improves after labeling + retrain.")


def main():
    parser = argparse.ArgumentParser(description='First-run setup for new users')
    parser.add_argument('--income', type=float, help='Monthly income (CNY) for budget config')
    parser.add_argument('--force-rules', action='store_true',
                        help='Reset merchant rules from starter template')
    parser.add_argument('--skip-train', action='store_true',
                        help='Parse and classify only; do not train')
    args = parser.parse_args()
    run_bootstrap(income=args.income, force_rules=args.force_rules, skip_train=args.skip_train)


if __name__ == '__main__':
    main()
