"""
Load and parse budget configuration from Excel or JSON.
"""
import argparse
import json
import pandas as pd
from pathlib import Path

from paths import BUDGET_CONFIG, BUDGET_EXAMPLE, DATA


def load_budget_from_excel(excel_path: str):
    """
    Parse the Monthly Budget tab from a personal finance Excel workbook.

    Returns dict with budget config (income, categories, saving goals).
    """
    excel_path = Path(excel_path)
    if not excel_path.exists():
        raise FileNotFoundError(f"Budget Excel not found: {excel_path}")

    df = pd.read_excel(excel_path, sheet_name='Monthly Budget', header=None)

    header_row = None
    for i, row in df.iterrows():
        if 'Category' in str(row.values) and 'Type' in str(row.values):
            header_row = i
            break

    if header_row is None:
        raise ValueError("Could not find header row in Monthly Budget tab")

    df = pd.read_excel(excel_path, sheet_name='Monthly Budget', header=header_row)

    monthly_income_row = df[df.iloc[:, 0].astype(str).str.contains('Monthly Income', na=False, case=False)]
    monthly_income = None
    if not monthly_income_row.empty:
        monthly_income = float(monthly_income_row.iloc[0, 1]) if pd.notna(monthly_income_row.iloc[0, 1]) else None

    categories = {}
    month_cols = ['Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']

    for idx, row in df.iterrows():
        cat_name = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else None
        cat_type = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else None

        if not cat_name or cat_name in ['Category', 'Total', 'NaN', ''] or cat_type in ['Type', 'NaN', '']:
            continue

        if cat_type not in ['Need', 'Want']:
            continue

        avg_monthly_val = row.iloc[2]
        if pd.isna(avg_monthly_val):
            continue

        try:
            avg_monthly = float(avg_monthly_val)
        except (ValueError, TypeError):
            continue

        budget_target = float(row.iloc[3]) if pd.notna(row.iloc[3]) else avg_monthly

        monthly_values = []
        for i in range(4, min(4 + len(month_cols), len(row))):
            val = row.iloc[i]
            if pd.notna(val):
                try:
                    monthly_values.append(float(val))
                except (ValueError, TypeError):
                    monthly_values.append(budget_target)
            else:
                monthly_values.append(budget_target)

        while len(monthly_values) < 9:
            monthly_values.append(budget_target)

        categories[cat_name] = {
            'type': cat_type,
            'avg_monthly': avg_monthly,
            'monthly_budget': budget_target,
            'annual_budget': avg_monthly * 12,
            'monthly': monthly_values[:9],
        }

    total_budget = sum(cat['annual_budget'] for cat in categories.values())
    saving_goal_monthly = 600.0

    return {
        'income': monthly_income or 8000.0,
        'currency': 'CNY',
        'period': 'Jan 2026 - Dec 2026',
        'total_budget': total_budget,
        'saving_goal_monthly': saving_goal_monthly,
        'saving_goal_annual': saving_goal_monthly * 12,
        'categories': categories,
    }


def save_budget_config(config, output_path=None):
    """Save budget config to JSON file."""
    output_path = Path(output_path or BUDGET_CONFIG)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    return str(output_path)


def load_budget_config(config_path=None):
    """Load budget config from JSON file."""
    path = Path(config_path or BUDGET_CONFIG)
    if not path.exists():
        path = BUDGET_EXAMPLE
    with open(path, encoding='utf-8') as f:
        return json.load(f)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Import budget from Excel or show current config')
    parser.add_argument('--excel', help='Path to Personal_finance.xlsx (Monthly Budget tab)')
    parser.add_argument('--output', default=str(BUDGET_CONFIG), help='Output JSON path')
    args = parser.parse_args()

    if args.excel:
        print(f"Loading budget from {args.excel}...")
        config = load_budget_from_excel(args.excel)
    else:
        print(f"Loading budget from {BUDGET_CONFIG}...")
        config = load_budget_config()

    print(f"\n  Monthly Income: ¥{config['income']:.2f}")
    print(f"  Saving Goal: ¥{config['saving_goal_monthly']:.2f}/month")
    print(f"  Categories: {len(config['categories'])}")

    if args.excel:
        out = save_budget_config(config, args.output)
        print(f"\nSaved to: {out}")
    else:
        print("\nTip: import from Excel with  python src/budget_loader.py --excel your_file.xlsx")
