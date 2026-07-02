"""
Streamlit Dashboard — Personal Finance Categorizer
6-tab structure: Overview, Budget & Forecast, Savings & Anomalies,
Action Plan, Label Queue, Reports.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from bootstrap import apply_label_queue_and_retrain, export_merchants_to_label
from categories import ML_CATEGORIES
from dashboard_helpers import (
    load_budget_config,
    calculate_ytd_vs_budget,
    get_status_badge,
    get_budget_type,
    apply_chart_theme,
    CHART_COLORS,
    ACTIVE_CATEGORIES,
    FORECAST_MONTHS,
)
from forecast import (
    calculate_historical_patterns,
    project_spending,
    calculate_savings_projection,
)
from label import load_merchant_rules
from merchant_display import add_display_names, aggregate_merchants
from paths import MERCHANT_RULES, MERCHANTS_TO_LABEL, TRANSACTIONS
from translate import enrich_label_row
from trends import (
    calendar_years_in_data,
    month_of_year_profile,
    trend_summary,
    year_over_year_growth,
    yearly_totals,
)

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Finance Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    .block-container { padding-top: 1.5rem; max-width: 1400px; }
    .dash-header { margin-bottom: 0.25rem; }
    .dash-header h1 {
        font-size: 1.75rem; font-weight: 700; color: #e8eaed;
        margin: 0; letter-spacing: -0.02em;
    }
    .dash-subtitle { color: #8899a6; font-size: 0.85rem; margin-bottom: 1rem; }
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 0.75rem;
        margin-bottom: 1.25rem;
    }
    @media (max-width: 900px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } }
    .kpi-card {
        background: linear-gradient(145deg, #1a1d24 0%, #161920 100%);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 12px;
        padding: 1rem 1.1rem;
    }
    .kpi-label {
        font-size: 0.72rem; text-transform: uppercase;
        letter-spacing: 0.06em; color: #8899a6; margin-bottom: 0.35rem;
    }
    .kpi-value {
        font-size: 1.45rem; font-weight: 700; color: #e8eaed;
        line-height: 1.2;
    }
    .kpi-delta { font-size: 0.78rem; margin-top: 0.3rem; color: #8899a6; }
    .section-title {
        font-size: 1.05rem; font-weight: 600; color: #e8eaed;
        margin: 1.5rem 0 0.75rem 0; padding-bottom: 0.4rem;
        border-bottom: 1px solid rgba(255,255,255,0.06);
    }
    .stTabs [data-baseweb="tab-list"] { gap: 0.5rem; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 0.5rem 1.25rem;
        font-weight: 500;
    }
    .dash-footer {
        text-align: center; color: #5a6570;
        font-size: 0.75rem; padding: 1.5rem 0 0.5rem;
        border-top: 1px solid rgba(255,255,255,0.05);
        margin-top: 2rem;
    }
    .budget-summary-strip {
        display: flex; gap: 1.5rem; flex-wrap: wrap;
        background: rgba(124, 106, 247, 0.08);
        border: 1px solid rgba(124, 106, 247, 0.18);
        border-radius: 10px; padding: 0.65rem 1rem;
        font-size: 0.82rem; color: #c8cdd3;
        margin-bottom: 0.75rem;
    }
    .budget-summary-strip strong { color: #e8eaed; }
    .budget-row {
        display: grid;
        grid-template-columns: repeat(9, 1fr);
        gap: 0.55rem;
        margin-bottom: 0.5rem;
    }
    @media (max-width: 1400px) { .budget-row { grid-template-columns: repeat(5, 1fr); } }
    @media (max-width: 900px)  { .budget-row { grid-template-columns: repeat(3, 1fr); } }
    .budget-cat-card {
        background: #1a1d24;
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 10px;
        padding: 0.7rem 0.65rem 0.75rem;
        min-width: 0;
        display: flex; flex-direction: column; gap: 0.3rem;
    }
    .budget-cat-card.status-ok   { border-top: 3px solid #2ecc71; }
    .budget-cat-card.status-warn { border-top: 3px solid #f39c12; }
    .budget-cat-card.status-over { border-top: 3px solid #e74c3c; }
    .bc-top {
        display: flex; align-items: flex-start; justify-content: space-between; gap: 0.25rem;
    }
    .bc-name { font-size: 0.72rem; font-weight: 600; color: #e8eaed; line-height: 1.25; }
    .bc-type {
        font-size: 0.58rem; text-transform: uppercase; letter-spacing: 0.04em;
        padding: 0.1rem 0.35rem; border-radius: 4px; font-weight: 600;
    }
    .bc-type.need { background: rgba(231, 76, 60, 0.15); color: #e74c3c; }
    .bc-type.want { background: rgba(124, 106, 247, 0.15); color: #7c6af7; }
    .bc-amount { font-size: 1.05rem; font-weight: 700; color: #e8eaed; }
    .bc-budget { font-size: 0.68rem; color: #8899a6; }
    .bc-bar {
        height: 5px; background: rgba(255,255,255,0.08);
        border-radius: 3px; overflow: hidden;
    }
    .bc-fill { height: 100%; border-radius: 3px; }
    .bc-fill.ok   { background: linear-gradient(90deg, #27ae60, #2ecc71); }
    .bc-fill.warn { background: linear-gradient(90deg, #e67e22, #f39c12); }
    .bc-fill.over { background: linear-gradient(90deg, #c0392b, #e74c3c); }
    .bc-footer {
        display: flex; justify-content: space-between; align-items: center;
        font-size: 0.65rem; color: #8899a6;
    }
    .bc-status { font-weight: 600; }
    .bc-status.ok   { color: #2ecc71; }
    .bc-status.warn { color: #f39c12; }
    .bc-status.over { color: #e74c3c; }
    .readiness-ready {
        background: rgba(46, 204, 113, 0.12);
        border: 1px solid rgba(46, 204, 113, 0.35);
        border-radius: 10px; padding: 1rem 1.25rem; color: #c8cdd3;
    }
    .readiness-pending {
        background: rgba(243, 156, 18, 0.12);
        border: 1px solid rgba(243, 156, 18, 0.35);
        border-radius: 10px; padding: 1rem 1.25rem; color: #c8cdd3;
    }
</style>
""", unsafe_allow_html=True)

BUDGET_CATEGORIES = ACTIVE_CATEGORIES
CATEGORY_SHORT = {
    'Groceries': 'Groceries',
    'Transportation': 'Transit',
    'Utilities & Services': 'Utilities',
    'Eating Out': 'Eating Out',
    'Shopping': 'Shopping',
    'Transfers & Gifts': 'Transfers',
    'Other': 'Other',
    'Saving': 'Saving',
    'Investing': 'Investing',
}
DATA_PATH = Path(__file__).parent.parent / 'data' / 'processed' / 'transactions_classified.csv'


# ── Data & helpers ───────────────────────────────────────────────────────────

@st.cache_data
def load_data(file_mtime: float):
    df = pd.read_csv(DATA_PATH)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['month'] = df['timestamp'].dt.to_period('M')
    df['date'] = df['timestamp'].dt.date
    catering_mask = df['merchant'].str.contains('catering|餐饮', case=False, na=False)
    df.loc[catering_mask, 'category'] = 'Eating Out'
    return df


def render_filters(df, key_prefix=''):
    with st.expander("🔍 Filters", expanded=False):
        c1, c2, c3, c4 = st.columns([2, 2, 1.5, 1.5])
        min_date = df['timestamp'].min().date()
        max_date = df['timestamp'].max().date()
        with c1:
            date_range = st.date_input(
                "Date range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                key=f'{key_prefix}date',
            )
        with c2:
            categories = st.multiselect(
                "Categories",
                options=sorted(df['category'].unique()),
                default=sorted(df['category'].unique()),
                key=f'{key_prefix}cat',
            )
        with c3:
            source_options = sorted(df['source'].unique())
            sources = st.multiselect(
                "Source",
                options=source_options,
                default=source_options,
                key=f'{key_prefix}src',
            )
        with c4:
            min_conf = st.slider(
                "Confidence threshold",
                0.0, 1.0, 0.0, 0.05,
                key=f'{key_prefix}conf',
            )

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_date, max_date

    filtered = df[
        (df['date'] >= start_date) &
        (df['date'] <= end_date) &
        (df['category'].isin(categories)) &
        (df['source'].isin(sources)) &
        (df['confidence'] >= min_conf)
    ].copy()
    return filtered, start_date, end_date


def kpi_card(label, value, delta_text=''):
    return (
        f'<div class="kpi-card">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-delta">{delta_text}</div>'
        f'</div>'
    )


def get_monthly_budget_amount(budget_config, category, df_fallback):
    budget_amt = budget_config['categories'].get(category, {}).get('monthly_budget', 0)
    if budget_amt and budget_amt > 0:
        return float(budget_amt)
    hist = df_fallback[df_fallback['category'] == category].groupby('month')['amount'].sum()
    return float(hist.mean()) if len(hist) > 0 else 0.0


def budget_status_class(pct, cat_type):
    _, _, status_text = get_status_badge(pct, cat_type)
    if pct >= 100:
        return 'status-over', 'over', 'over', status_text
    if pct >= 80:
        return 'status-warn', 'warn', 'warn', status_text
    return 'status-ok', 'ok', 'ok', status_text


def build_budget_category_row(month_df, budget_config, df_all):
    cards = []
    on_track = 0
    total_actual = 0.0
    total_budget = 0.0

    for cat in BUDGET_CATEGORIES:
        actual = float(month_df[month_df['category'] == cat]['amount'].sum())
        budget_amt = get_monthly_budget_amount(budget_config, cat, df_all)
        cat_type = get_budget_type(budget_config, cat) or 'Need'

        if budget_amt <= 0:
            pct, bar_pct = 0, 0
            card_cls, fill_cls, stat_cls = 'status-ok', 'ok', 'ok'
            status_text, remain_text = 'Not started', 'Starts next semester'
            on_track += 1
        else:
            pct = actual / budget_amt * 100
            card_cls, fill_cls, stat_cls, status_text = budget_status_class(pct, cat_type)
            if pct < 100:
                on_track += 1
            bar_pct = min(pct, 100)
            remaining = budget_amt - actual
            remain_text = (
                f"¥{remaining:,.0f} left" if remaining >= 0
                else f"¥{abs(remaining):,.0f} over"
            )

        total_actual += actual
        total_budget += budget_amt
        short = CATEGORY_SHORT.get(cat, cat)
        type_cls = 'need' if cat_type == 'Need' else 'want'

        cards.append(f"""
        <div class="budget-cat-card {card_cls}">
            <div class="bc-top">
                <span class="bc-name">{short}</span>
                <span class="bc-type {type_cls}">{cat_type}</span>
            </div>
            <div class="bc-amount">¥{actual:,.0f}</div>
            <div class="bc-budget">of ¥{budget_amt:,.0f}</div>
            <div class="bc-bar"><div class="bc-fill {fill_cls}" style="width:{bar_pct:.0f}%"></div></div>
            <div class="bc-footer">
                <span class="bc-status {stat_cls}">{pct:.0f}% · {status_text}</span>
                <span>{remain_text}</span>
            </div>
        </div>""")

    summary = {
        'total_actual': total_actual,
        'total_budget': total_budget,
        'on_track': on_track,
        'total_cats': len(BUDGET_CATEGORIES),
        'overall_pct': (total_actual / total_budget * 100) if total_budget > 0 else 0,
    }
    return '<div class="budget-row">' + ''.join(cards) + '</div>', summary


def detect_anomalies(df_filtered):
    anomalies = []
    valid = df_filtered[~df_filtered['category'].isin(['???'])].copy()

    for cat in valid['category'].unique():
        cat_data = valid[valid['category'] == cat]
        if len(cat_data) == 0:
            continue
        q1, q3 = cat_data['amount'].quantile(0.25), cat_data['amount'].quantile(0.75)
        threshold = max(q3 + 1.5 * (q3 - q1), 150)
        high_value = cat_data[cat_data['amount'] > threshold].copy()
        high_value['flag_reason'] = f"High value (>{threshold:.0f}¥)"
        anomalies.append(high_value)

    merchant_counts = valid['merchant'].value_counts()
    one_off_merchants = merchant_counts[merchant_counts == 1].index
    one_off_all = valid[valid['merchant'].isin(one_off_merchants)].copy()
    if len(one_off_all) > 0:
        chunks = []
        for cat in one_off_all['category'].unique():
            cat_p90 = valid[valid['category'] == cat]['amount'].quantile(0.90)
            chunk = one_off_all[(one_off_all['category'] == cat) & (one_off_all['amount'] > cat_p90)]
            if len(chunk) > 0:
                chunks.append(chunk)
        if chunks:
            one_off = pd.concat(chunks, ignore_index=True)
            one_off['flag_reason'] = 'One-off merchant, high spend'
            anomalies.append(one_off)

    low_conf = valid[(valid['confidence'] < 0.50) & (valid['category'] != 'Other')].copy()
    if len(low_conf) > 0:
        low_conf['flag_reason'] = 'Low confidence (<50%)'
        anomalies.append(low_conf)

    if not anomalies:
        return pd.DataFrame()
    result = pd.concat(anomalies, ignore_index=True)
    return result.drop_duplicates(subset=['timestamp', 'merchant', 'amount'], keep='first')


def split_high_value_and_one_off(df_filtered):
    all_flags = detect_anomalies(df_filtered)
    if len(all_flags) == 0:
        return pd.DataFrame(), pd.DataFrame()
    high = all_flags[all_flags['flag_reason'].str.startswith('High value')].copy()
    one_off = all_flags[all_flags['flag_reason'].str.contains('One-off')].copy()
    return high, one_off


def compute_need_want_split(df_in, budget_config):
    want_cats = [
        c for c, info in budget_config['categories'].items()
        if info.get('type') == 'Want'
    ]
    total = df_in['amount'].sum()
    want = df_in[df_in['category'].isin(want_cats)]['amount'].sum()
    need = total - want
    return need, want, total


def cumulative_savings_series(df_in, monthly_income):
    monthly = df_in.groupby('month').agg(spend=('amount', 'sum')).reset_index()
    monthly['month_dt'] = monthly['month'].dt.to_timestamp()
    monthly['income'] = monthly_income
    monthly['savings'] = monthly['income'] - monthly['spend']
    monthly['cum_savings'] = monthly['savings'].cumsum()
    return monthly


def compute_efficiency_score(df_in, budget_config):
    """Share of months meeting the monthly savings goal."""
    want_cats = [c for c, i in budget_config['categories'].items() if i['type'] == 'Want']
    income = budget_config['income']
    goal = budget_config['saving_goal_monthly']
    months_met = 0
    rows = []
    for month in sorted(df_in['month'].unique()):
        mdf = df_in[df_in['month'] == month]
        total_s = mdf['amount'].sum()
        want_s = mdf[mdf['category'].isin(want_cats)]['amount'].sum()
        need_s = total_s - want_s
        monthly_savings = income - total_s
        savings_gap = max(0, goal - monthly_savings)
        met = monthly_savings >= goal
        months_met += int(met)
        rows.append({
            'month': str(month),
            'total_spend': total_s,
            'need_spend': need_s,
            'want_spend': want_s,
            'want_pct': (want_s / total_s * 100) if total_s > 0 else 0,
            'monthly_savings': monthly_savings,
            'savings_gap': savings_gap,
            'met_goal': met,
        })
    eff_df = pd.DataFrame(rows)
    n = len(eff_df)
    score = (months_met / n * 100) if n > 0 else 0
    return score, eff_df


def investment_readiness(df_in, budget_config):
    income = budget_config['income']
    goal = budget_config['saving_goal_monthly']
    months = sorted(df_in['month'].unique())[-3:]
    results = []
    for month in months:
        spend = df_in[df_in['month'] == month]['amount'].sum()
        savings = income - spend
        results.append({
            'month': str(month),
            'spend': spend,
            'savings': savings,
            'met_goal': savings >= goal,
        })
    met_count = sum(r['met_goal'] for r in results)
    avg_surplus = np.mean([r['savings'] for r in results]) if results else 0
    return {
        'months': results,
        'met_count': met_count,
        'total_months': len(results),
        'ready': met_count == len(results) and len(results) == 3,
        'avg_surplus': avg_surplus,
    }


def category_risk_from_forecast(forecast_df, category):
    cat_fc = forecast_df[forecast_df['category'] == category]
    if len(cat_fc) == 0:
        return 'Low'
    risk_order = {'High': 3, 'Medium': 2, 'Low': 1}
    worst = cat_fc['risk'].map(risk_order).max()
    for label, val in risk_order.items():
        if val == worst:
            return label
    return 'Low'


# ── Load data ────────────────────────────────────────────────────────────────
df = load_data(DATA_PATH.stat().st_mtime)
budget_config = load_budget_config('data/budget_config.json')

st.markdown(
    '<div class="dash-header"><h1>Personal Finance Dashboard</h1></div>',
    unsafe_allow_html=True,
)

tab_overview, tab_budget, tab_savings, tab_action, tab_labels, tab_reports = st.tabs([
    "📊 Overview",
    "💳 Budget & Forecast",
    "💰 Savings & Anomalies",
    "🎯 Action Plan",
    "🏷️ Label Queue",
    "📋 Reports",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
with tab_overview:
    df_filtered, start_date, end_date = render_filters(df, key_prefix='ov_')
    st.markdown(
        f'<div class="dash-subtitle">'
        f'{start_date.strftime("%b %d, %Y")} — {end_date.strftime("%b %d, %Y")} · '
        f'{len(df_filtered):,} transactions</div>',
        unsafe_allow_html=True,
    )

    total = df_filtered['amount'].sum()
    n_txn = len(df_filtered)
    days = max((df_filtered['timestamp'].max() - df_filtered['timestamp'].min()).days + 1, 1)
    avg_txn = total / n_txn if n_txn > 0 else 0
    daily_avg = total / days if days > 0 else 0
    cat_spend = df_filtered.groupby('category')['amount'].sum()
    if len(cat_spend) > 0:
        top_cat = cat_spend.idxmax()
        top_amt = cat_spend.max()
        top_delta = f"¥{top_amt:,.0f} ({top_amt / total * 100:.0f}% of period)" if total > 0 else ''
    else:
        top_cat, top_delta = '—', 'No data'

    kpi_html = '<div class="kpi-grid">' + ''.join([
        kpi_card('Total Spend', f'¥{total:,.0f}', f'{n_txn:,} transactions'),
        kpi_card('Avg Transaction', f'¥{avg_txn:,.0f}', 'per transaction'),
        kpi_card('Daily Avg Spend', f'¥{daily_avg:,.0f}', f'over {days} days'),
        kpi_card('Top Category', top_cat, top_delta),
    ]) + '</div>'
    st.markdown(kpi_html, unsafe_allow_html=True)

    st.markdown('<div class="section-title">Monthly Spending Trend</div>', unsafe_allow_html=True)
    monthly_total = df_filtered.groupby('month')['amount'].sum().reset_index()
    monthly_total['month_dt'] = monthly_total['month'].dt.to_timestamp()
    avg_monthly = monthly_total['amount'].mean()

    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=monthly_total['month_dt'], y=monthly_total['amount'],
        mode='lines+markers',
        line=dict(color='#7c6af7', width=2),
        marker=dict(size=8, color='#7c6af7', line=dict(width=2, color='#1a1d24')),
        fill='tozeroy', fillcolor='rgba(124, 106, 247, 0.1)',
        hovertemplate='%{x|%b %Y}<br>¥%{y:,.0f}<extra></extra>',
    ))
    if len(monthly_total) > 0:
        fig_trend.add_hline(
            y=avg_monthly, line_width=1, line_dash='dash', line_color='rgba(255,255,255,0.25)',
            annotation_text=f'Avg ¥{avg_monthly:,.0f}/mo', annotation_position='top left',
            annotation_font_color='#8899a6',
        )
        last = monthly_total.iloc[-1]
        fig_trend.add_annotation(
            x=last['month_dt'], y=last['amount'], text=f"¥{last['amount']:,.0f}",
            showarrow=False, yshift=18, font=dict(color='#e8eaed', size=12),
        )
    fig_trend.update_layout(xaxis_title='', yaxis_title='¥', showlegend=False)
    apply_chart_theme(fig_trend, height=340)
    st.plotly_chart(fig_trend, use_container_width=True)

    col_a, col_b = st.columns([3, 2])
    with col_a:
        st.markdown('<div class="section-title">Monthly Spend by Category</div>', unsafe_allow_html=True)
        monthly_cat = df_filtered.groupby(['month', 'category'])['amount'].sum().reset_index()
        monthly_cat['month'] = monthly_cat['month'].astype(str)
        fig_stack = px.bar(
            monthly_cat, x='month', y='amount', color='category',
            barmode='stack', color_discrete_sequence=CHART_COLORS,
        )
        apply_chart_theme(fig_stack, height=360)
        st.plotly_chart(fig_stack, use_container_width=True)

    with col_b:
        st.markdown('<div class="section-title">Category Breakdown</div>', unsafe_allow_html=True)
        cat_df = df_filtered.groupby('category')['amount'].sum().reset_index()
        fig_pie = px.pie(
            cat_df, values='amount', names='category',
            hole=0.55, color_discrete_sequence=CHART_COLORS,
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        apply_chart_theme(fig_pie, height=360)
        st.plotly_chart(fig_pie, use_container_width=True)

    col_c, col_d = st.columns(2)
    with col_c:
        st.markdown('<div class="section-title">Top 15 Merchants</div>', unsafe_allow_html=True)
        top_m = aggregate_merchants(df_filtered, n=15).sort_values('amount')
        fig_merch = px.bar(
            top_m, x='amount', y='merchant_display', orientation='h',
            color='amount', color_continuous_scale=[[0, '#1a1d24'], [1, '#7c6af7']],
        )
        fig_merch.update_layout(coloraxis_showscale=False, yaxis_title='')
        apply_chart_theme(fig_merch, height=400)
        st.plotly_chart(fig_merch, use_container_width=True)

    with col_d:
        st.markdown('<div class="section-title">Cumulative Spending</div>', unsafe_allow_html=True)
        daily = df_filtered.sort_values('timestamp').copy()
        daily['cumsum'] = daily['amount'].cumsum()
        fig_cum = go.Figure()
        fig_cum.add_trace(go.Scatter(
            x=daily['timestamp'], y=daily['cumsum'],
            mode='lines', line=dict(color='#4fc3f7', width=2),
            fill='tozeroy', fillcolor='rgba(79, 195, 247, 0.1)',
        ))
        apply_chart_theme(fig_cum, height=400)
        st.plotly_chart(fig_cum, use_container_width=True)

    st.markdown('<div class="section-title">Yearly &amp; Seasonal Trends</div>', unsafe_allow_html=True)
    MONTH_ORDER = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    summary = trend_summary(df_filtered)
    t1, t2 = st.columns(2)
    with t1:
        st.caption("Average spend by calendar month (seasonal profile, all years pooled)")
        profile = month_of_year_profile(df_filtered)
        fig_season = px.bar(
            profile, x='month_label', y='mean',
            category_orders={'month_label': MONTH_ORDER},
            color_discrete_sequence=[CHART_COLORS[1]],
        )
        fig_season.update_layout(yaxis_title='Avg ¥/month', xaxis_title='')
        apply_chart_theme(fig_season, height=300)
        st.plotly_chart(fig_season, use_container_width=True)
    with t2:
        if summary['multi_year_ready']:
            st.caption(f"Year-over-year total spend ({', '.join(map(str, summary['years']))})")
            yearly = yearly_totals(df_filtered)
            fig_yearly = px.bar(
                yearly, x='year', y='total_spend',
                color_discrete_sequence=[CHART_COLORS[0]],
            )
            fig_yearly.update_layout(xaxis=dict(type='category'), yaxis_title='¥', xaxis_title='')
            apply_chart_theme(fig_yearly, height=300)
            st.plotly_chart(fig_yearly, use_container_width=True)
            growth = year_over_year_growth(df_filtered)
            if growth is not None and len(growth) > 0:
                last = growth.iloc[-1]
                direction = 'up' if last['yoy_pct'] > 0 else 'down'
                st.caption(f"{int(last['year'])} vs {int(last['year']) - 1}: spend {direction} {abs(last['yoy_pct']):.1f}%")
        else:
            years = calendar_years_in_data(df_filtered)
            st.info(
                f"Year-over-year comparison unlocks with 2+ calendar years of data. "
                f"You currently have: {', '.join(map(str, years)) or 'no data in range'}."
            )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — BUDGET & FORECAST
# ══════════════════════════════════════════════════════════════════════════════
with tab_budget:
    if not budget_config:
        st.warning("Budget config not found. Run `python src/budget_loader.py` first.")
    else:
        month_options = sorted(df['month'].unique())
        selected_month = st.selectbox(
            "Budget month (actuals)",
            month_options,
            index=len(month_options) - 1,
            format_func=lambda m: str(m),
            key='budget_month_pick',
        )
        month_df = df[df['month'] == selected_month]

        st.markdown('<div class="section-title">Monthly Budget vs Actual</div>', unsafe_allow_html=True)
        row_html, summary = build_budget_category_row(month_df, budget_config, df)
        st.markdown(
            f'<div class="budget-summary-strip">'
            f'<span><strong>¥{summary["total_actual"]:,.0f}</strong> spent · '
            f'<strong>¥{summary["total_budget"]:,.0f}</strong> budget · '
            f'<strong>{summary["overall_pct"]:.0f}%</strong> used</span>'
            f'<span><strong>{summary["on_track"]}/{summary["total_cats"]}</strong> on track</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown(row_html, unsafe_allow_html=True)

        st.markdown('<div class="section-title">Variance & Risk by Category</div>', unsafe_allow_html=True)
        patterns = calculate_historical_patterns(df)
        fc_method = st.radio(
            "Forecast method",
            options=['seasonal', 'ewma'],
            format_func=lambda m: 'Seasonal + trend' if m == 'seasonal' else 'EWMA (recent-weighted)',
            horizontal=True,
            key='fc_method',
        )
        forecast_df = project_spending(
            df, patterns, budget_config, forecast_months=9, method=fc_method,
        )

        variance_rows = []
        for cat in BUDGET_CATEGORIES:
            if cat not in budget_config['categories']:
                continue
            actual = float(month_df[month_df['category'] == cat]['amount'].sum())
            budget_amt = get_monthly_budget_amount(budget_config, cat, df)
            variance = actual - budget_amt
            pct = (variance / budget_amt * 100) if budget_amt > 0 else 0
            risk = category_risk_from_forecast(forecast_df, cat)
            variance_rows.append({
                'Category': cat,
                'Type': get_budget_type(budget_config, cat) or '—',
                'Actual (¥)': actual,
                'Budget (¥)': budget_amt,
                'Variance (¥)': variance,
                'Variance (%)': pct,
                '9-mo Risk': risk,
            })
        var_df = pd.DataFrame(variance_rows)

        def _variance_style(row):
            v = row['Variance (¥)']
            if v > 0:
                return ['background-color: rgba(231,76,60,0.15)'] * len(row)
            if v < -budget_config['categories'].get(row['Category'], {}).get('monthly_budget', 1) * 0.1:
                return ['background-color: rgba(46,204,113,0.12)'] * len(row)
            return [''] * len(row)

        st.dataframe(
            var_df.style.format({
                'Actual (¥)': '¥{:,.0f}',
                'Budget (¥)': '¥{:,.0f}',
                'Variance (¥)': '¥{:+,.0f}',
                'Variance (%)': '{:+.1f}%',
            }).apply(_variance_style, axis=1),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown('<div class="section-title">Budget vs Actual (Selected Month)</div>', unsafe_allow_html=True)
        plot_df = var_df[var_df['Budget (¥)'] > 0].copy()
        fig_bva = go.Figure()
        fig_bva.add_trace(go.Bar(
            name='Budget', x=plot_df['Category'], y=plot_df['Budget (¥)'],
            marker_color='rgba(124, 106, 247, 0.45)',
        ))
        fig_bva.add_trace(go.Bar(
            name='Actual', x=plot_df['Category'], y=plot_df['Actual (¥)'],
            marker_color=[
                '#e74c3c' if a > b else '#2ecc71' if a < b * 0.9 else '#f39c12'
                for a, b in zip(plot_df['Actual (¥)'], plot_df['Budget (¥)'])
            ],
        ))
        fig_bva.update_layout(barmode='group', xaxis_title='', yaxis_title='¥')
        apply_chart_theme(fig_bva, height=380)
        st.plotly_chart(fig_bva, use_container_width=True)

        st.markdown('<div class="section-title">9-Month Forecast (Sep → May)</div>', unsafe_allow_html=True)
        cat_order = (
            forecast_df.groupby('category')['projected_spend']
            .sum().sort_values(ascending=False).index.tolist()
        )
        heatmap_data = forecast_df.pivot_table(
            values='pct_of_budget', index='category', columns='month', aggfunc='mean',
        ).reindex(cat_order)
        month_cols = [m for m in FORECAST_MONTHS if m in heatmap_data.columns]
        heatmap_data = heatmap_data[month_cols]
        fig_heat = go.Figure(data=go.Heatmap(
            z=heatmap_data.values,
            x=heatmap_data.columns, y=heatmap_data.index,
            colorscale=[[0, '#2ecc71'], [0.5, '#f39c12'], [1, '#e74c3c']],
            zmid=100, zmin=0, zmax=200,
            text=np.round(heatmap_data.values, 0),
            texttemplate='%{text}%', textfont=dict(size=10),
            colorbar=dict(title='% Budget'),
        ))
        apply_chart_theme(fig_heat, height=max(320, len(cat_order) * 36))
        st.plotly_chart(fig_heat, use_container_width=True)

        fc_col1, fc_col2 = st.columns([2, 1])
        with fc_col1:
            fc_detail = forecast_df.pivot_table(
                index='category', columns='month', values='projected_spend', aggfunc='sum',
            ).reindex(cat_order)[month_cols]
            st.caption("Projected spend (¥) by category and month")
            st.dataframe(
                fc_detail.style.format('¥{:,.0f}'),
                use_container_width=True,
            )
        with fc_col2:
            selected_fc = st.selectbox("Forecast month detail", FORECAST_MONTHS, key='fc_month')
            month_fc = forecast_df[forecast_df['month'] == selected_fc].set_index('category').reindex(cat_order)
            risk_counts = month_fc['risk'].dropna().value_counts()
            if len(risk_counts) > 0:
                fig_risk = px.pie(
                    values=risk_counts.values, names=risk_counts.index,
                    color_discrete_sequence=['#2ecc71', '#f39c12', '#e74c3c'],
                    hole=0.4,
                )
                apply_chart_theme(fig_risk, height=280)
                st.plotly_chart(fig_risk, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SAVINGS & ANOMALIES
# ══════════════════════════════════════════════════════════════════════════════
with tab_savings:
    if not budget_config:
        st.warning("Budget config required for savings analytics.")
    else:
        income = budget_config['income']
        savings = calculate_savings_projection(df, budget_config, monthly_income=income)
        goal = budget_config['saving_goal_annual']
        need, want, total_spend = compute_need_want_split(df, budget_config)
        days_span = max((df['timestamp'].max() - df['timestamp'].min()).days + 1, 1)
        burn_rate = df['amount'].sum() / days_span

        s1, s2, s3, s4, s5 = st.columns(5)
        s1.metric("Monthly Income", f"¥{income:,.0f}")
        s2.metric("YTD Savings", f"¥{savings['ytd_savings']:,.0f}",
                  f"{savings['ytd_savings_pct']:.1f}% rate")
        gap = goal - savings['projected_year_end_savings']
        s3.metric(
            "Year-End Projection",
            f"¥{savings['projected_year_end_savings']:,.0f}",
            f"¥{gap:,.0f} vs ¥{goal:,.0f} goal" if gap > 0 else "Goal met",
            delta_color="inverse" if gap > 0 else "normal",
        )
        s4.metric("Need vs Want", f"{need / total_spend * 100:.0f}% need" if total_spend else "—",
                  f"¥{want:,.0f} discretionary")
        s5.metric("Daily Burn Rate", f"¥{burn_rate:,.0f}", f"over {days_span} days")

        st.markdown('<div class="section-title">Cumulative Savings Trend</div>', unsafe_allow_html=True)
        cum_df = cumulative_savings_series(df, income)
        fig_sav = go.Figure()
        fig_sav.add_trace(go.Scatter(
            x=cum_df['month_dt'], y=cum_df['cum_savings'],
            mode='lines+markers', line=dict(color='#2ecc71', width=2.5),
            fill='tozeroy', fillcolor='rgba(46, 204, 113, 0.12)',
            name='Cumulative savings',
        ))
        fig_sav.add_hline(
            y=goal, line_dash='dash', line_color='#f39c12',
            annotation_text=f'Annual goal ¥{goal:,.0f}',
        )
        apply_chart_theme(fig_sav, height=340)
        st.plotly_chart(fig_sav, use_container_width=True)

        st.markdown('<div class="section-title">Anomalies</div>', unsafe_allow_html=True)
        high_val, one_off = split_high_value_and_one_off(df)
        a1, a2 = st.columns(2)
        with a1:
            st.caption(f"High-value outliers ({len(high_val)})")
            if len(high_val) > 0:
                show = add_display_names(high_val)[
                    ['timestamp', 'merchant_display', 'amount', 'category', 'flag_reason']
                ].rename(columns={'merchant_display': 'Merchant'})
                st.dataframe(show.sort_values('amount', ascending=False),
                             use_container_width=True, hide_index=True)
            else:
                st.info("No high-value outliers detected.")
        with a2:
            st.caption(f"One-off merchants worth flagging ({len(one_off)})")
            if len(one_off) > 0:
                show = add_display_names(one_off)[
                    ['timestamp', 'merchant_display', 'amount', 'category', 'flag_reason']
                ].rename(columns={'merchant_display': 'Merchant'})
                st.dataframe(show.sort_values('amount', ascending=False),
                             use_container_width=True, hide_index=True)
            else:
                st.info("No one-off high-spend merchants detected.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — ACTION PLAN
# ══════════════════════════════════════════════════════════════════════════════
with tab_action:
    if not budget_config:
        st.warning("Budget config required for action planning.")
    else:
        want_categories = [
            c for c, info in budget_config['categories'].items() if info['type'] == 'Want'
        ]
        efficiency_score, eff_df = compute_efficiency_score(df, budget_config)

        st.markdown('<div class="section-title">Need vs Want Efficiency</div>', unsafe_allow_html=True)
        e1, e2 = st.columns([1, 3])
        with e1:
            st.metric(
                "Efficiency Score",
                f"{efficiency_score:.0f}%",
                f"{int(eff_df['met_goal'].sum())}/{len(eff_df)} months met ¥{budget_config['saving_goal_monthly']:,.0f} goal",
            )
        with e2:
            fig_eff = go.Figure()
            fig_eff.add_trace(go.Bar(x=eff_df['month'], y=eff_df['need_spend'],
                                     name='Need', marker_color='#e74c3c'))
            fig_eff.add_trace(go.Bar(x=eff_df['month'], y=eff_df['want_spend'],
                                     name='Want', marker_color='#7c6af7'))
            fig_eff.add_trace(go.Bar(x=eff_df['month'], y=eff_df['savings_gap'],
                                     name='Savings gap', marker_color='#f39c12', opacity=0.5))
            fig_eff.update_layout(barmode='stack', hovermode='x unified')
            apply_chart_theme(fig_eff, height=320)
            st.plotly_chart(fig_eff, use_container_width=True)

        st.markdown('<div class="section-title">High-Impact Discretionary Transactions</div>', unsafe_allow_html=True)
        want_df = df[df['category'].isin(want_categories)].copy()
        if len(want_df) > 0:
            ranked = add_display_names(want_df).nlargest(15, 'amount')[
                ['timestamp', 'merchant_display', 'category', 'amount', 'confidence']
            ].rename(columns={'merchant_display': 'Merchant'})
            st.dataframe(ranked, use_container_width=True, hide_index=True)

            impacts = []
            months_in_data = max((df['timestamp'].max() - df['timestamp'].min()).days / 30, 1)
            for merchant in want_df['merchant'].unique():
                mtx = want_df[want_df['merchant'] == merchant]
                total_s = mtx['amount'].sum()
                impacts.append({
                    'merchant': merchant,
                    'monthly_impact': total_s / months_in_data,
                    'visits': len(mtx),
                    'total': total_s,
                })
            cut_df = pd.DataFrame(impacts).sort_values('monthly_impact', ascending=False)
            cut_df = add_display_names(cut_df)
            cut_df = (
                cut_df.groupby('merchant_display', as_index=False)
                .agg(monthly_impact=('monthly_impact', 'sum'), visits=('visits', 'sum'))
                .nlargest(10, 'monthly_impact')
            )
            fig_cut = px.bar(
                cut_df.sort_values('monthly_impact'),
                x='monthly_impact', y='merchant_display', orientation='h',
                color='monthly_impact',
                color_continuous_scale=[[0, '#1a1d24'], [1, '#f39c12']],
            )
            fig_cut.update_layout(coloraxis_showscale=False, yaxis_title='', xaxis_title='¥/month')
            apply_chart_theme(fig_cut, height=320)
            st.plotly_chart(fig_cut, use_container_width=True)

        st.markdown('<div class="section-title">Savings Gap Calculator</div>', unsafe_allow_html=True)
        base_savings = calculate_savings_projection(df, budget_config, monthly_income=budget_config['income'])
        remaining_months = max(12 - base_savings['months_passed'], 0)
        ytd_spend = base_savings['ytd_spend']
        income_annual = budget_config['income'] * 12
        goal_annual = budget_config['saving_goal_annual']

        cut_cols = st.columns(2)
        cuts = {}
        with cut_cols[0]:
            st.caption("Slide to simulate % cuts in Want categories (0–50%)")
            for cat in want_categories:
                cat_monthly = (
                    df[df['category'] == cat]['amount'].sum()
                    / max(base_savings['months_passed'], 1)
                )
                if cat_monthly <= 0:
                    continue
                cuts[cat] = st.slider(
                    f"{cat} (¥{cat_monthly:,.0f}/mo avg)",
                    0, 50, 0, 5,
                    key=f'cut_{cat}',
                )

        total_monthly_cut = sum(
            (df[df['category'] == cat]['amount'].sum() / max(base_savings['months_passed'], 1))
            * (cuts.get(cat, 0) / 100)
            for cat in want_categories
        )
        adjusted_avg = base_savings['avg_monthly_spend'] - total_monthly_cut
        adjusted_projected = income_annual - (ytd_spend + adjusted_avg * remaining_months)
        gap_to_goal = max(0, goal_annual - adjusted_projected)

        with cut_cols[1]:
            fig_gap = go.Figure()
            fig_gap.add_trace(go.Bar(
                x=['Current trajectory', 'With cuts'],
                y=[base_savings['projected_year_end_savings'], adjusted_projected],
                marker_color=['#4fc3f7', '#2ecc71'],
                text=[
                    f"¥{base_savings['projected_year_end_savings']:,.0f}",
                    f"¥{adjusted_projected:,.0f}",
                ],
                textposition='outside',
            ))
            fig_gap.add_hline(y=goal_annual, line_dash='dash', line_color='#f39c12',
                              annotation_text=f'Goal ¥{goal_annual:,.0f}')
            fig_gap.update_layout(yaxis_title='Projected year-end savings (¥)')
            apply_chart_theme(fig_gap, height=320)
            st.plotly_chart(fig_gap, use_container_width=True)
            if gap_to_goal > 0:
                st.caption(
                    f"To hit the ¥{goal_annual:,.0f} goal, cut **¥{gap_to_goal:,.0f}** total "
                    f"(~¥{gap_to_goal / max(remaining_months, 1):,.0f}/mo in remaining months)."
                )
            else:
                st.caption("Simulated cuts put you on track for the annual savings goal.")

        st.markdown('<div class="section-title">Investment Readiness</div>', unsafe_allow_html=True)
        readiness = investment_readiness(df, budget_config)
        if readiness['ready']:
            st.markdown(
                f'<div class="readiness-ready">'
                f'<strong>✅ Ready to Invest</strong><br>'
                f'All 3 recent months met the ¥{budget_config["saving_goal_monthly"]:,.0f}/mo savings goal. '
                f'Average surplus: <strong>¥{readiness["avg_surplus"]:,.0f}/mo</strong>.<br><br>'
                f'<em>Not financial advice.</em> Common next steps: emergency fund top-up, '
                f'low-cost index funds, or tax-advantaged accounts when eligible.'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="readiness-pending">'
                f'<strong>🟡 Keep Going</strong><br>'
                f'{readiness["met_count"]} of {readiness["total_months"]} recent months met the '
                f'¥{budget_config["saving_goal_monthly"]:,.0f}/mo goal. '
                f'Hit 3/3 consecutive months to unlock the readiness badge.'
                f'</div>',
                unsafe_allow_html=True,
            )
        rd = pd.DataFrame(readiness['months'])
        if len(rd) > 0:
            rd['Status'] = rd['met_goal'].map({True: '✅ Met', False: '❌ Below'})
            st.dataframe(
                rd.rename(columns={
                    'month': 'Month', 'spend': 'Spend (¥)',
                    'savings': 'Savings (¥)',
                }).style.format({'Spend (¥)': '¥{:,.0f}', 'Savings (¥)': '¥{:,.0f}'}),
                use_container_width=True,
                hide_index=True,
            )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — LABEL QUEUE
# ══════════════════════════════════════════════════════════════════════════════
with tab_labels:
    st.markdown('<div class="section-title">Merchants Needing a Category</div>', unsafe_allow_html=True)
    st.caption(
        "Rule-matched merchants are already categorized automatically. These aren't — "
        "pick a category for the ones you recognize, then apply to add rules, "
        "retrain, and reclassify everything."
    )

    if not TRANSACTIONS.exists():
        st.info("No parsed transactions yet. Run the CLI bootstrap or web wizard first.")
    elif not MERCHANTS_TO_LABEL.exists():
        st.info("No label queue yet.")
        if st.button("Generate label queue from current data"):
            df_raw = pd.read_csv(TRANSACTIONS)
            rules = load_merchant_rules(str(MERCHANT_RULES))
            export_merchants_to_label(df_raw, rules)
            st.rerun()
    else:
        queue_df = pd.read_csv(MERCHANTS_TO_LABEL)
        if queue_df.empty:
            st.success("All top merchants are already rule-matched. Nothing to label.")
        else:
            queue_df['suggested_category'] = queue_df['suggested_category'].astype(object).fillna('')
            queue_df['notes'] = queue_df.get('notes', pd.Series(dtype=object)).astype(object).fillna('')
            labels = [enrich_label_row(m, d) for m, d in zip(queue_df['merchant'], queue_df['sample_description'])]
            queue_df['merchant_label'] = [l['merchant_label'] for l in labels]
            queue_df['description_label'] = [l['description_label'] for l in labels]

            edited = st.data_editor(
                queue_df,
                column_order=[
                    'merchant_label', 'description_label', 'count',
                    'total_spend', 'suggested_category', 'notes',
                ],
                column_config={
                    'merchant_label': st.column_config.TextColumn('Merchant', disabled=True),
                    'description_label': st.column_config.TextColumn('Sample', disabled=True),
                    'count': st.column_config.NumberColumn('Txns', disabled=True),
                    'total_spend': st.column_config.NumberColumn('Total ¥', format='¥%.0f', disabled=True),
                    'suggested_category': st.column_config.SelectboxColumn(
                        'Category', options=[''] + ML_CATEGORIES, required=False,
                    ),
                    'notes': st.column_config.TextColumn('Notes'),
                },
                hide_index=True,
                use_container_width=True,
                key='label_queue_editor',
            )

            n_filled = int((edited['suggested_category'].astype(str).str.strip() != '').sum())
            st.caption(f"{n_filled} of {len(edited)} merchants categorized in this batch.")

            if st.button(f"Apply {n_filled} label(s) & retrain", disabled=n_filled == 0):
                to_save = edited.drop(columns=['merchant_label', 'description_label'])
                to_save.to_csv(MERCHANTS_TO_LABEL, index=False, encoding='utf-8-sig')
                with st.spinner("Adding rules, retraining if there's enough data, and reclassifying..."):
                    result = apply_label_queue_and_retrain()
                load_data.clear()
                if result['trainable']:
                    tr = result['train_result']
                    st.success(
                        f"Added {result['added_rules']} rule(s). Retrained: "
                        f"{tr['accuracy']:.1%} CV accuracy on {tr['n_samples']} samples. "
                        f"{result['remaining_unlabeled']} merchants still unlabeled."
                    )
                else:
                    st.success(
                        f"Added {result['added_rules']} rule(s) and reclassified. "
                        f"Not enough labeled data to retrain yet ({result['train_message']}). "
                        f"{result['remaining_unlabeled']} merchants still unlabeled."
                    )
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — REPORTS
# ══════════════════════════════════════════════════════════════════════════════
with tab_reports:
    st.markdown('<div class="section-title">Monthly Report</div>', unsafe_allow_html=True)
    month_options = sorted([str(m) for m in df['month'].unique()], reverse=True)
    selected_month = st.selectbox("Select month", month_options, key='report_month')
    month_df = df[df['month'].astype(str) == selected_month]

    summary = month_df.groupby('category').agg(
        Count=('amount', 'count'),
        Total=('amount', 'sum'),
        Average=('amount', 'mean'),
        Max=('amount', 'max'),
    ).reset_index().sort_values('Total', ascending=False)
    summary['% of Total'] = (summary['Total'] / summary['Total'].sum() * 100).round(1)

    st.dataframe(
        summary.style.format({
            'Total': '¥{:,.2f}',
            'Average': '¥{:,.2f}',
            'Max': '¥{:,.2f}',
            '% of Total': '{:.1f}%',
        }),
        use_container_width=True,
        hide_index=True,
    )

    total_month = summary['Total'].sum()
    st.caption(f"Month total: **¥{total_month:,.2f}** · {len(month_df):,} transactions")

    csv_bytes = summary.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="⬇️ Download CSV",
        data=csv_bytes,
        file_name=f'spend_report_{selected_month}.csv',
        mime='text/csv',
    )

st.markdown(
    '<div class="dash-footer">'
    'Personal Finance Categorizer · Logistic Regression · 96.2% accuracy'
    '</div>',
    unsafe_allow_html=True,
)
