"""
Load and parse budget configuration from Excel file.
"""
import pandas as pd
import json
from pathlib import Path

BUDGET_FILE = r'c:\Users\User\Downloads\Finances_1st year\Personal_finance.xlsx'


def load_budget_from_excel(excel_path=BUDGET_FILE):
    """
    Parse the Monthly Budget tab from Personal_finance.xlsx.

    Returns dict with budget config:
    {
        'income': float,
        'currency': 'CNY',
        'period': 'Sep 2026 - Jun 2027',
        'total_budget': float,
        'saving_goal_monthly': float,
        'categories': {
            'Category Name': {
                'type': 'Need|Want',
                'annual_budget': float,
                'avg_monthly': float,
                'monthly': [list of 12 monthly allocations]
            },
            ...
        }
    }
    """

    # Read Monthly Budget tab
    df = pd.read_excel(excel_path, sheet_name='Monthly Budget', header=None)

    # Find the header row (contains "Category", "Type", etc.)
    header_row = None
    for i, row in df.iterrows():
        if 'Category' in str(row.values) and 'Type' in str(row.values):
            header_row = i
            break

    if header_row is None:
        raise ValueError("Could not find header row in Monthly Budget tab")

    # Re-read with proper header
    df = pd.read_excel(excel_path, sheet_name='Monthly Budget', header=header_row)

    # Extract key metrics
    monthly_income_row = df[df.iloc[:, 0].astype(str).str.contains('Monthly Income', na=False, case=False)]
    monthly_income = None
    if not monthly_income_row.empty:
        # Income value is typically in column index 1
        monthly_income = float(monthly_income_row.iloc[0, 1]) if pd.notna(monthly_income_row.iloc[0, 1]) else None

    # Find and extract category data
    categories = {}
    month_cols = ['Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']

    for idx, row in df.iterrows():
        cat_name = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else None
        cat_type = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else None

        # Skip if this is a header, total, or invalid row
        if not cat_name or cat_name in ['Category', 'Total', 'NaN', ''] or cat_type in ['Type', 'NaN', '']:
            continue

        if cat_type not in ['Need', 'Want']:
            continue

        # Get average monthly
        avg_monthly_val = row.iloc[2]
        if pd.isna(avg_monthly_val):
            continue

        try:
            avg_monthly = float(avg_monthly_val)
        except (ValueError, TypeError):
            continue

        # Get monthly budget target (column 3)
        budget_target = float(row.iloc[3]) if pd.notna(row.iloc[3]) else avg_monthly

        # Get monthly allocations (columns 4 onwards)
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

        # Pad if needed (9 months of data, use budget_target for missing)
        while len(monthly_values) < 9:
            monthly_values.append(budget_target)

        categories[cat_name] = {
            'type': cat_type,
            'avg_monthly': avg_monthly,
            'monthly_budget': budget_target,
            'annual_budget': avg_monthly * 12,
            'monthly': monthly_values[:9]  # Sep-May (9 months)
        }

    # Calculate total budget
    total_budget = sum(cat['annual_budget'] for cat in categories.values())

    # Saving goal (typically ¥600/month)
    saving_goal_monthly = 600.0

    config = {
        'income': monthly_income or 2986.0,
        'currency': 'CNY',
        'period': 'Sep 2026 - Jun 2027',
        'total_budget': total_budget,
        'saving_goal_monthly': saving_goal_monthly,
        'saving_goal_annual': saving_goal_monthly * 12,
        'categories': categories
    }

    return config


def save_budget_config(config, output_path='data/budget_config.json'):
    """Save budget config to JSON file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    return str(output_path)


def load_budget_config(config_path='data/budget_config.json'):
    """Load budget config from JSON file."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


if __name__ == '__main__':
    # Generate budget config
    print("Loading budget from Excel...")
    config = load_budget_from_excel()

    print(f"\nBudget Summary:")
    print(f"  Monthly Income: ¥{config['income']:.2f}")
    print(f"  Total Annual Budget: ¥{config['total_budget']:.2f}")
    print(f"  Saving Goal: ¥{config['saving_goal_monthly']:.2f}/month (¥{config['saving_goal_annual']:.2f}/year)")
    print(f"  Categories: {len(config['categories'])}")

    for cat, data in config['categories'].items():
        print(f"    {cat:30s}: {data['type']:5s} | Avg: ¥{data['avg_monthly']:7.2f} | Annual: ¥{data['annual_budget']:8.2f}")

    # Save to JSON
    output_path = save_budget_config(config)
    print(f"\nSaved to: {output_path}")
