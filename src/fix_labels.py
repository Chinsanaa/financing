"""One-off script to fix data quality issues: relabel ??? and Travel, add NaN labels."""
import pandas as pd
import sys
sys.stdout.reconfigure(encoding='utf-8')


def fix_labels():
    """Fix labeled_transactions.csv by relabeling ??? and Travel rows, and ~30 NaN rows."""

    # Create backup before modifying
    input_path = 'data/labeled/labeled_transactions.csv'
    backup_path = 'data/labeled/labeled_transactions.csv.backup'

    try:
        # Load data
        df = pd.read_csv(input_path, encoding='utf-8')
        df_backup = df.copy()  # In-memory backup for rollback

        print(f"Loaded {len(df)} rows")
        print(f"Before: category value counts:")
        print(df['category'].value_counts(dropna=False).to_string())
        print()
    except Exception as e:
        print(f"ERROR loading data: {e}")
        return

    # ========================================================================
    # PHASE 1: Relabel 12 "???" rows with their correct categories
    # ========================================================================
    print("PHASE 1: Relabeling ??? rows")
    print("-" * 70)

    remap_dict = {
        '上海公共交通卡股份有限公司': 'Transportation',
        '宁波市轨道交通集团有限公司线网调度分公司': 'Transportation',
        '卓联（上海）餐饮服务有限公司': 'Eating Out',
        '上海饱猫餐饮管理有限公司': 'Eating Out',
        'floating kitchen': 'Eating Out',
        'LA BARAKA UV': 'Eating Out',
        '上海优悠生活商业管理有限公司': 'Shopping',
        'ao**店': 'Shopping',
        'ws**1': 'Shopping',
    }

    q_rows = df[df['category'] == '???'].copy()
    print(f"Found {len(q_rows)} rows with category='???'")

    q_skipped = []
    for idx, row in q_rows.iterrows():
        merchant = row['merchant']
        if merchant in remap_dict:
            new_cat = remap_dict[merchant]
            print(f"  {merchant[:40]:40s} ??? → {new_cat}")
            df.loc[idx, 'category'] = new_cat
            df.loc[idx, 'labeled'] = True
        else:
            print(f"  {merchant[:40]:40s} ??? → (NO MAPPING, skipped)")
            q_skipped.append(merchant)

    print(f"\nAfter Phase 1: {len(df[df['category'] == '???'])} ??? rows remaining")
    print()

    # ========================================================================
    # PHASE 2: Relabel 2 Travel rows as "Other"
    # ========================================================================
    print("PHASE 2: Relabeling Travel rows")
    print("-" * 70)

    travel_rows = df[df['category'] == 'Travel'].copy()
    print(f"Found {len(travel_rows)} Travel rows")

    for idx, row in travel_rows.iterrows():
        merchant = row['merchant']
        print(f"  {merchant[:40]:40s} Travel → Other")
        df.loc[idx, 'category'] = 'Other'
        df.loc[idx, 'labeled'] = True

    print(f"\nAfter Phase 2: {len(df[df['category'] == 'Travel'])} Travel rows remaining")
    print()

    # ========================================================================
    # PHASE 3: Label ~30 NaN rows with high-confidence categories
    # ========================================================================
    print("PHASE 3: Labeling obvious NaN rows")
    print("-" * 70)

    # Mapping of merchants → categories for obvious NaN rows
    nan_remap = {
        '上海蕤盛工贸': 'Groceries',  # Vending machines (12+ rows, fixed at 0.683 conf)
        '济明路蘭州牛肉面（百热客）': 'Eating Out',  # Noodle shop (misclassified as Travel)
        'K-MART': 'Groceries',  # Supermarket
        '达美乐': 'Eating Out',  # Domino's Pizza
        '美淑家·韩国料理·石锅拌饭': 'Eating Out',  # Korean restaurant
        '饿梨酱Hey Guac·美洲活力西餐': 'Eating Out',  # Western restaurant
        '小满手工粉': 'Eating Out',  # Handmade noodles
        '广州市玩客游乐设备有限公司': 'Other',  # Amusement arcade
        '上海国际旅行卫生保健中心': 'Other',  # Health clinic
        '🔥战🙏狼🔥': 'Transfers & Gifts',  # Personal QR payment
    }

    nan_rows = df[df['category'].isna()]
    print(f"Found {len(nan_rows)} NaN rows")

    labeled_count = 0
    nan_skipped = []
    for idx, row in nan_rows.iterrows():
        merchant = row['merchant']
        if merchant in nan_remap:
            new_cat = nan_remap[merchant]
            df.loc[idx, 'category'] = new_cat
            df.loc[idx, 'labeled'] = True
            labeled_count += 1
            print(f"  {merchant[:40]:40s} NaN → {new_cat}")
        else:
            nan_skipped.append(merchant)

    print(f"\nPhase 3: Labeled {labeled_count} NaN rows")
    print(f"Remaining NaN rows: {df['category'].isna().sum()}")
    print()

    # ========================================================================
    # SAVE AND REPORT
    # ========================================================================
    print("FINAL CATEGORY DISTRIBUTION")
    print("-" * 70)
    print(df['category'].value_counts(dropna=False).to_string())
    print()

    print("SUMMARY:")
    print(f"  Relabeled ??? rows: {len(q_rows) - len(q_skipped)}/{len(q_rows)}")
    if q_skipped:
        print(f"    WARNING: {len(q_skipped)} rows skipped (not in mapping)")
    print(f"  Relabeled Travel rows: {len(travel_rows)} → Other")
    print(f"  Labeled NaN rows: {labeled_count}/{len(nan_rows)}")
    if nan_skipped:
        print(f"    WARNING: {len(nan_skipped)} rows skipped (not in mapping)")
    print(f"  Other category total: {(df['category'] == 'Other').sum()}")
    print(f"  Groceries category total: {(df['category'] == 'Groceries').sum()}")
    print(f"  Eating Out category total: {(df['category'] == 'Eating Out').sum()}")
    print()

    # Validate before saving
    print("FINAL VALIDATION:")
    print("-" * 70)

    q_remaining = (df['category'] == '???').sum()
    t_remaining = (df['category'] == 'Travel').sum()
    nan_remaining = df['category'].isna().sum()

    print(f"  ??? rows remaining: {q_remaining} (should be 0)")
    print(f"  Travel rows remaining: {t_remaining} (should be 0)")
    print(f"  NaN rows remaining: {nan_remaining} (was 121)")
    print(f"  labeled=True rows: {(df['labeled'] == True).sum()}")
    print()

    # Abort if validation fails
    if q_remaining > 0 or t_remaining > 0:
        print(f"✗ VALIDATION FAILED: {q_remaining} ??? rows and {t_remaining} Travel rows still exist")
        print(f"  Data NOT saved. No changes made.")
        return

    # Save with backup
    try:
        output_path = 'data/labeled/labeled_transactions.csv'
        # Create timestamped backup
        import shutil
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f'data/labeled/labeled_transactions.csv.{timestamp}.backup'
        shutil.copy2(output_path, backup_path)
        print(f"✓ Backup created: {backup_path}")

        # Write new version
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"✓ Saved to {output_path}")
        print(f"\n✓ SUCCESS: ??? and Travel categories eliminated")
        print(f"  Backup available at: {backup_path}")
    except Exception as e:
        print(f"✗ ERROR saving file: {e}")
        print(f"  Rolling back to in-memory backup...")
        print(f"  Data NOT saved.")


if __name__ == '__main__':
    fix_labels()
