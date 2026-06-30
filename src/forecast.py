"""
Spending forecasting: project future spending based on historical patterns.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json


def load_budget_config(path='data/budget_config.json'):
    """Load budget configuration."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def calculate_historical_patterns(df, basis_start=None, basis_end=None):
    """
    Calculate spending patterns from classified transactions.

    Args:
        df: DataFrame with timestamp, category, amount
        basis_start: Start date for pattern basis (default: data min)
        basis_end: End date for pattern basis (default: data max)

    Returns:
        dict with patterns per category:
        {
            'Category': {
                'monthly_avg': float,
                'monthly_std': float,
                'monthly_values': {month_str: [list of years]},
                'trend': float (slope),
                'volatility': float,
                'confidence': float (0-1 based on data points)
            }
        }
    """

    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['month'] = df['timestamp'].dt.to_period('M')
    df['month_str'] = df['timestamp'].dt.strftime('%b')  # 'Aug', 'Sep', etc.

    if basis_start:
        df = df[df['timestamp'] >= basis_start]
    if basis_end:
        df = df[df['timestamp'] < basis_end]

    patterns = {}

    for category in df['category'].unique():
        cat_data = df[df['category'] == category]

        # Monthly aggregates
        monthly = cat_data.groupby('month')['amount'].sum()
        monthly_avg = monthly.mean()
        monthly_std = monthly.std() or 0

        # Month-of-year patterns (e.g., all Septembers, all Octobers)
        month_str_values = {}
        for month_str in df['month_str'].unique():
            values = cat_data[cat_data['month_str'] == month_str].groupby('month')['amount'].sum().values
            if len(values) > 0:
                month_str_values[month_str] = list(values)

        # Trend (linear regression)
        if len(monthly) > 1:
            x = np.arange(len(monthly))
            y = monthly.values
            coeffs = np.polyfit(x, y, 1)
            trend = coeffs[0]  # slope
        else:
            trend = 0

        # Volatility (coefficient of variation)
        if monthly_avg > 0:
            volatility = monthly_std / monthly_avg
        else:
            volatility = 0

        # Confidence (how many data points)
        confidence = min(len(monthly) / 10, 1.0)  # max 10 months = 100% confidence

        patterns[category] = {
            'monthly_avg': monthly_avg,
            'monthly_std': monthly_std,
            'monthly_values': month_str_values,
            'trend': trend,
            'volatility': volatility,
            'confidence': confidence,
            'n_observations': len(monthly)
        }

    return patterns


def project_spending(df, patterns, budget_config, forecast_months=9):
    """
    Project spending for next N months.

    Args:
        df: Current transaction data
        patterns: Historical patterns dict
        budget_config: Budget configuration dict
        forecast_months: Number of months to forecast (default 9 for Sep-May)

    Returns:
        DataFrame with projected spending:
        month, category, projected_spend, budget, variance, % of budget, risk_level, confidence
    """

    months_list = ['Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May']
    now = pd.to_datetime('today')
    current_month = now.strftime('%b')

    forecast_data = []

    for category in budget_config['categories'].keys():
        pattern = patterns.get(category, {})
        cat_budget = budget_config['categories'][category]
        avg_monthly = cat_budget['avg_monthly']
        monthly_allocations = cat_budget.get('monthly', [])

        for month_idx, month in enumerate(months_list[:forecast_months]):
            # Base: use historical average or budget target
            historical_avg = pattern.get('monthly_avg', avg_monthly)

            # Adjust by historical month-of-year pattern
            month_pattern = pattern.get('monthly_values', {}).get(month, [])
            if month_pattern and len(month_pattern) > 0:
                # Use average of that month across all years
                month_avg = np.mean(month_pattern)
                # Weight: 70% historical month pattern, 30% overall average
                base = 0.7 * month_avg + 0.3 * historical_avg
            else:
                base = historical_avg

            # Apply trend
            trend = pattern.get('trend', 0)
            projected = base + (trend * month_idx)

            # Compare to budget
            budget_target = monthly_allocations[month_idx] if month_idx < len(monthly_allocations) else avg_monthly
            variance = projected - budget_target
            pct_of_budget = (projected / budget_target * 100) if budget_target > 0 else 0

            # Risk level
            if pct_of_budget > 110:
                risk = 'High'
            elif pct_of_budget > 90:
                risk = 'Medium'
            else:
                risk = 'Low'

            confidence = pattern.get('confidence', 0.5)

            forecast_data.append({
                'month': month,
                'category': category,
                'type': cat_budget['type'],
                'projected_spend': max(0, projected),
                'budget': budget_target,
                'variance': variance,
                'pct_of_budget': pct_of_budget,
                'risk': risk,
                'confidence': confidence
            })

    df_forecast = pd.DataFrame(forecast_data)
    return df_forecast


def calculate_ytd_summary(df_transactions, budget_config, forecast_df):
    """
    Calculate year-to-date actual and projected totals.

    Returns:
        dict with ytd and projected year-end numbers
    """

    # Actual YTD
    df_trans = df_transactions.copy()
    df_trans['timestamp'] = pd.to_datetime(df_trans['timestamp'])

    ytd_actual = df_trans.groupby('category')['amount'].sum().to_dict()

    # Projected full year (actual YTD + forecasted remaining)
    projected_by_cat = forecast_df.groupby('category')['projected_spend'].sum().to_dict()

    summary = {}
    for category in budget_config['categories'].keys():
        actual = ytd_actual.get(category, 0)
        projected = projected_by_cat.get(category, 0)
        budget = budget_config['categories'][category]['annual_budget']

        summary[category] = {
            'actual_ytd': actual,
            'projected_year_end': actual + projected,
            'annual_budget': budget,
            'variance': (actual + projected) - budget,
            'pct_of_budget': ((actual + projected) / budget * 100) if budget > 0 else 0
        }

    return summary


def calculate_savings_projection(df_transactions, budget_config, monthly_income=2986):
    """
    Project savings at year-end.

    Returns:
        dict with savings metrics
    """

    df_trans = df_transactions.copy()
    df_trans['timestamp'] = pd.to_datetime(df_trans['timestamp'])
    df_trans['month'] = df_trans['timestamp'].dt.to_period('M')

    # YTD actual spending
    ytd_total_spend = df_trans['amount'].sum()

    # Calculate months passed
    min_date = df_trans['timestamp'].min()
    max_date = df_trans['timestamp'].max()
    months_passed = (max_date.year - min_date.year) * 12 + (max_date.month - min_date.month) + 1

    # Actual YTD savings
    ytd_income = monthly_income * months_passed
    ytd_savings = ytd_income - ytd_total_spend

    # Projected year-end (assuming 12 months of income, current avg spending)
    avg_monthly_spend = ytd_total_spend / months_passed if months_passed > 0 else 0
    remaining_months = 12 - months_passed
    projected_remaining_spend = avg_monthly_spend * remaining_months
    projected_total_spend = ytd_total_spend + projected_remaining_spend

    annual_income = monthly_income * 12
    projected_year_end_savings = annual_income - projected_total_spend
    saving_goal_annual = budget_config['saving_goal_annual']

    return {
        'ytd_income': ytd_income,
        'ytd_spend': ytd_total_spend,
        'ytd_savings': ytd_savings,
        'ytd_savings_pct': (ytd_savings / ytd_income * 100) if ytd_income > 0 else 0,
        'months_passed': months_passed,
        'avg_monthly_spend': avg_monthly_spend,
        'projected_annual_income': annual_income,
        'projected_total_spend': projected_total_spend,
        'projected_year_end_savings': projected_year_end_savings,
        'saving_goal_annual': saving_goal_annual,
        'projected_vs_goal': projected_year_end_savings - saving_goal_annual,
        'on_track': projected_year_end_savings >= saving_goal_annual
    }


if __name__ == '__main__':
    # Test forecasting
    import sys
    sys.path.insert(0, '/home/claude/financing/src')

    df = pd.read_csv('data/processed/transactions_classified.csv')
    budget_config = load_budget_config()

    print("Calculating historical patterns...")
    patterns = calculate_historical_patterns(df)

    print("Projecting spending...")
    forecast = project_spending(df, patterns, budget_config, forecast_months=9)

    print("\nForecast Summary:")
    print(forecast.groupby('category')[['projected_spend', 'budget', 'variance', 'risk']].sum())

    print("\nSavings Projection:")
    savings = calculate_savings_projection(df, budget_config)
    print(f"  YTD Savings: ¥{savings['ytd_savings']:.2f}")
    print(f"  Projected Year-End: ¥{savings['projected_year_end_savings']:.2f}")
    print(f"  Goal: ¥{savings['saving_goal_annual']:.2f}")
    print(f"  On Track: {savings['on_track']}")
