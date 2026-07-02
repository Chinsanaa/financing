"""Build JSON payloads for the 5-tab web dashboard."""
import json
from typing import Dict, List

import pandas as pd

from session_context import SessionContext
from translate import merchant_label_english


def _load_classified(ctx: SessionContext) -> pd.DataFrame:
    df = pd.read_csv(ctx.transactions_classified)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df


def _load_budget(ctx: SessionContext) -> dict:
    with open(ctx.budget_config, encoding='utf-8') as f:
        return json.load(f)


def overview_tab(ctx: SessionContext) -> dict:
    df = _load_classified(ctx)
    by_cat = df.groupby('category')['amount'].sum().sort_values(ascending=False)
    by_month = df.groupby(df['timestamp'].dt.to_period('M'))['amount'].sum()
    top_merchants = (
        df.groupby('merchant')['amount'].sum()
        .sort_values(ascending=False).head(15)
    )
    top_labels = [merchant_label_english(m) for m in top_merchants.index.tolist()]
    return {
        'total_spend': round(float(df['amount'].sum()), 2),
        'transaction_count': len(df),
        'avg_transaction': round(float(df['amount'].mean()), 2),
        'date_range': {
            'start': str(df['timestamp'].min().date()),
            'end': str(df['timestamp'].max().date()),
        },
        'by_category': {
            'labels': by_cat.index.tolist(),
            'values': [round(float(v), 2) for v in by_cat.values],
        },
        'monthly': {
            'labels': [str(m) for m in by_month.index],
            'values': [round(float(v), 2) for v in by_month.values],
        },
        'top_merchants': {
            'labels': top_labels,
            'values': [round(float(v), 2) for v in top_merchants.values],
        },
    }


def budget_tab(ctx: SessionContext) -> dict:
    df = _load_classified(ctx)
    budget = _load_budget(ctx)
    rows = []
    for cat, spent in df.groupby('category')['amount'].sum().items():
        b = budget.get('categories', {}).get(cat, {})
        target = float(b.get('monthly_budget', 0)) * max(1, df['timestamp'].dt.to_period('M').nunique())
        if target <= 0:
            target = float(spent) * 1.1
        rows.append({
            'category': cat,
            'spent': round(float(spent), 2),
            'budget': round(target, 2),
            'variance': round(float(spent) - target, 2),
            'type': b.get('type', 'Want'),
        })
    rows.sort(key=lambda r: r['spent'], reverse=True)
    return {
        'income': budget.get('income', 0),
        'rows': rows,
    }


def savings_tab(ctx: SessionContext) -> dict:
    df = _load_classified(ctx)
    budget = _load_budget(ctx)
    income = float(budget.get('income', 8000))
    months = max(1, df['timestamp'].dt.to_period('M').nunique())
    total_spend = float(df['amount'].sum())
    ytd_income = income * months
    savings = ytd_income - total_spend
    monthly = df.groupby(df['timestamp'].dt.to_period('M'))['amount'].sum()
    q75 = df['amount'].quantile(0.75)
    q25 = df['amount'].quantile(0.25)
    iqr = q75 - q25
    threshold = q75 + max(150, 1.5 * iqr)
    outliers = df[df['amount'] >= threshold].nlargest(10, 'amount')
    return {
        'monthly_income': income,
        'ytd_spend': round(total_spend, 2),
        'ytd_savings': round(savings, 2),
        'savings_rate': round(savings / ytd_income, 4) if ytd_income else 0,
        'monthly_spend': {
            'labels': [str(m) for m in monthly.index],
            'values': [round(float(v), 2) for v in monthly.values],
        },
        'outliers': [
            {
                'merchant': merchant_label_english(r['merchant']),
                'amount': round(float(r['amount']), 2),
                'category': r['category'],
                'date': str(r['timestamp'].date()),
            }
            for _, r in outliers.iterrows()
        ],
    }


def action_tab(ctx: SessionContext) -> dict:
    df = _load_classified(ctx)
    budget = _load_budget(ctx)
    want_cats = {
        c for c, info in budget.get('categories', {}).items()
        if info.get('type') == 'Want'
    }
    if not want_cats:
        want_cats = set(df['category'].unique())
    discretionary = df[df['category'].isin(want_cats)]
    by_merchant = (
        discretionary.groupby('merchant')['amount'].sum()
        .sort_values(ascending=False).head(12)
    )
    return {
        'cuttable_merchants': {
            'labels': [merchant_label_english(m) for m in by_merchant.index.tolist()],
            'values': [round(float(v), 2) for v in by_merchant.values],
        },
        'top_discretionary': [
            {
                'merchant': merchant_label_english(r['merchant']),
                'amount': round(float(r['amount']), 2),
                'category': r['category'],
            }
            for _, r in discretionary.nlargest(15, 'amount').iterrows()
        ],
    }


def reports_tab(ctx: SessionContext) -> dict:
    df = _load_classified(ctx)
    by_month_cat = (
        df.assign(month=df['timestamp'].dt.to_period('M').astype(str))
        .groupby(['month', 'category'])['amount'].sum().reset_index()
    )
    summary = df.groupby('category').agg(
        count=('amount', 'size'),
        total=('amount', 'sum'),
        avg=('amount', 'mean'),
    ).reset_index()
    return {
        'category_summary': [
            {
                'category': r['category'],
                'count': int(r['count']),
                'total': round(float(r['total']), 2),
                'avg': round(float(r['avg']), 2),
            }
            for _, r in summary.iterrows()
        ],
        'monthly_breakdown': [
            {
                'month': r['month'],
                'category': r['category'],
                'amount': round(float(r['amount']), 2),
            }
            for _, r in by_month_cat.iterrows()
        ],
    }


TAB_BUILDERS = {
    'overview': overview_tab,
    'budget': budget_tab,
    'savings': savings_tab,
    'action': action_tab,
    'reports': reports_tab,
}


def build_dashboard_tab(ctx: SessionContext, tab: str) -> dict:
    builder = TAB_BUILDERS.get(tab)
    if not builder:
        raise ValueError(f'Unknown tab: {tab}')
    return builder(ctx)
