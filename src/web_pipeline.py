"""Pipeline orchestration for the web onboarding wizard."""
import json
import shutil
from typing import Dict, List, Optional, Tuple

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import StratifiedKFold

from bootstrap import (
    dedupe_labeled,
    merge_labeled,
    normalize_category,
)
from categories import CATEGORY_NORMALIZE
from classify import apply_description_overrides, classify_all
from label import apply_merchant_rules, load_merchant_rules
from parse import load_transactions, save_processed
from segment import LR_HYPERPARAMS, build_vectorizer, clean_text, vectorize
from session_context import (
    MAX_LABEL_ROUNDS,
    TARGET_ACCURACY,
    WEB_MIN_LABELED,
    SessionContext,
)
from translate import enrich_label_row


def _empty_labeled_df() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        'timestamp', 'merchant', 'description', 'amount', 'source', 'category', 'labeled',
    ])


def _normalize_df(df: pd.DataFrame, ml_categories: List[str]) -> pd.DataFrame:
    df = df.copy()
    df['category'] = df['category'].replace(CATEGORY_NORMALIZE)
    unknown = ~df['category'].isin(ml_categories)
    if unknown.any():
        fallback = 'Other' if 'Other' in ml_categories else ml_categories[0]
        df.loc[unknown, 'category'] = fallback
    return df


def classify_session(ctx: SessionContext) -> pd.DataFrame:
    ml_categories = ctx.load_categories()
    df = pd.read_csv(ctx.transactions)
    rules = load_merchant_rules(str(ctx.merchant_rules))

    vectorizer, classifier = None, None
    if ctx.vectorizer.exists() and ctx.classifier.exists():
        vectorizer = joblib.load(ctx.vectorizer)
        classifier = joblib.load(ctx.classifier)

    df_classified = classify_all(df, vectorizer, classifier, rules=rules)
    df_classified = _normalize_df(df_classified, ml_categories)
    ctx.root.joinpath('processed').mkdir(parents=True, exist_ok=True)
    df_classified.to_csv(ctx.transactions_classified, index=False)
    return df_classified


def seed_labeled_for_categories(
    df: pd.DataFrame, rules: dict, ml_categories: List[str],
) -> pd.DataFrame:
    ruled = apply_merchant_rules(df, rules)
    matched = ruled[ruled['labeled'] == True].copy()
    matched['category'] = matched['category'].map(normalize_category)
    matched = matched[matched['category'].isin(ml_categories)]
    seed = matched[['timestamp', 'merchant', 'description', 'amount', 'source', 'category']].copy()
    seed['labeled'] = True
    return seed


def parse_uploads(ctx: SessionContext) -> dict:
    if not ctx.alipay_path.exists() and not ctx.wechat_path.exists():
        raise ValueError('Upload at least one file (Alipay CSV and/or WeChat XLSX).')

    df = load_transactions(
        str(ctx.alipay_path) if ctx.alipay_path.exists() else None,
        str(ctx.wechat_path) if ctx.wechat_path.exists() else None,
        raw_dir=ctx.raw_dir,
    )
    save_processed(df, str(ctx.transactions))

    rules = load_merchant_rules(str(ctx.merchant_rules))
    ml_categories = ctx.load_categories()
    seed = seed_labeled_for_categories(df, rules, ml_categories)

    existing = (
        pd.read_csv(ctx.labeled_txns)
        if ctx.labeled_txns.exists()
        else _empty_labeled_df()
    )
    merged = merge_labeled(existing, seed)
    merged.to_csv(ctx.labeled_txns, index=False)

    df_classified = classify_session(ctx)
    rule_hits = int((df_classified['confidence'] == 1.0).sum())

    ctx.save_meta({
        'phase': 'categories',
        'transaction_count': len(df),
        'rule_matches': rule_hits,
    })
    return {
        'transaction_count': len(df),
        'rule_matches': rule_hits,
        'total_spend': round(float(df['amount'].sum()), 2),
    }


def retrain_session(ctx: SessionContext) -> dict:
    ml_categories = ctx.load_categories()
    df = pd.read_csv(ctx.labeled_txns)
    df_labeled = df[df['labeled'] == True].copy()
    df_labeled['category'] = df_labeled['category'].replace(CATEGORY_NORMALIZE)
    df_labeled = df_labeled[df_labeled['category'].isin(ml_categories)]

    n = len(df_labeled)
    if n < WEB_MIN_LABELED:
        return {
            'trainable': False,
            'accuracy': None,
            'message': f'Need {WEB_MIN_LABELED}+ labeled rows (have {n}). Keep labeling merchants.',
            'labeled_count': n,
        }

    counts = df_labeled['category'].value_counts()
    if (counts < 2).any():
        thin = counts[counts < 2].index.tolist()
        return {
            'trainable': False,
            'accuracy': None,
            'message': f'Need 2+ examples per category. Thin: {thin}',
            'labeled_count': n,
        }

    df_labeled['text'] = df_labeled.apply(
        lambda r: clean_text(r['merchant'], r['description']), axis=1,
    )
    vectorizer = build_vectorizer(df_labeled['text'].tolist())
    X = vectorize(df_labeled['text'].tolist(), vectorizer)
    y = df_labeled['category']

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = []
    for train_idx, test_idx in skf.split(X, y):
        clf_fold = LogisticRegression(**LR_HYPERPARAMS)
        clf_fold.fit(X[train_idx], y.iloc[train_idx])
        cv_scores.append(accuracy_score(y.iloc[test_idx], clf_fold.predict(X[test_idx])))

    clf = LogisticRegression(**LR_HYPERPARAMS)
    clf.fit(X, y)
    joblib.dump(vectorizer, ctx.vectorizer)
    joblib.dump(clf, ctx.classifier)

    accuracy = sum(cv_scores) / len(cv_scores)
    return {
        'trainable': True,
        'accuracy': round(accuracy, 4),
        'labeled_count': n,
        'message': f'CV accuracy {accuracy:.1%}',
    }


def get_label_queue(ctx: SessionContext, limit: int = 10) -> List[dict]:
    df = pd.read_csv(ctx.transactions)
    rules = load_merchant_rules(str(ctx.merchant_rules))
    ruled = apply_merchant_rules(df, rules)
    unlabeled = ruled[ruled['labeled'] == False]
    if unlabeled.empty:
        return []

    stats = (
        unlabeled.groupby('merchant')
        .agg(
            count=('amount', 'size'),
            total_spend=('amount', 'sum'),
            sample_description=('description', 'first'),
        )
        .sort_values('count', ascending=False)
        .head(limit)
        .reset_index()
    )
    out: List[dict] = []
    for _, row in stats.iterrows():
        base = enrich_label_row(row['merchant'], str(row['sample_description']))
        out.append({
            'merchant': base['merchant'],  # id only; UI must use merchant_label
            'merchant_label': base['merchant_label'],
            'description_label': base['description_label'],
            'count': int(row['count']),
            'total_spend': round(float(row['total_spend']), 2),
        })
    return out


def apply_merchant_labels(ctx: SessionContext, labels: List[Dict[str, str]]) -> dict:
    """labels: [{merchant, category}, ...]"""
    ml_categories = ctx.load_categories()
    rules_df = pd.read_csv(ctx.merchant_rules)
    df_txn = pd.read_csv(ctx.transactions)

    labeled_parts = []
    if ctx.labeled_txns.exists():
        labeled_parts.append(pd.read_csv(ctx.labeled_txns))

    added_rules = 0
    added_rows = 0
    new_batches = []
    for item in labels:
        merchant = str(item.get('merchant', '')).strip()
        category = normalize_category(str(item.get('category', '')).strip())
        if not merchant or category not in ml_categories:
            continue

        if merchant not in rules_df['merchant_pattern'].values:
            rules_df = pd.concat([
                rules_df,
                pd.DataFrame([{'merchant_pattern': merchant, 'category': category}]),
            ], ignore_index=True)
            added_rules += 1

        mask = df_txn['merchant'] == merchant
        batch = df_txn.loc[mask, [
            'timestamp', 'merchant', 'description', 'amount', 'source',
        ]].copy()
        batch['category'] = category
        batch['labeled'] = True
        new_batches.append(batch)
        added_rows += len(batch)

    rules_df.to_csv(ctx.merchant_rules, index=False)
    existing = labeled_parts[0] if labeled_parts else _empty_labeled_df()
    if new_batches:
        merged = merge_labeled(existing, pd.concat(new_batches, ignore_index=True))
    else:
        merged = existing
    merged.to_csv(ctx.labeled_txns, index=False)

    train_result = retrain_session(ctx)
    df_classified = classify_session(ctx)

    meta = ctx.load_meta()
    iteration = int(meta.get('iteration', 0)) + 1
    accuracy = train_result.get('accuracy')
    high_conf = float((df_classified['confidence'] >= 0.7).mean()) if len(df_classified) else 0.0

    effective_accuracy = accuracy if accuracy is not None else high_conf
    done = (
        effective_accuracy is not None
        and effective_accuracy >= TARGET_ACCURACY
    ) or iteration >= MAX_LABEL_ROUNDS

    ctx.save_meta({
        'iteration': iteration,
        'accuracy': effective_accuracy,
        'phase': 'dashboard' if done else 'label',
        'labeled_merchants': int(meta.get('labeled_merchants', 0)) + len(labels),
    })

    if done:
        _finalize_budget(ctx, df_classified)

    return {
        'added_rules': added_rules,
        'added_rows': added_rows,
        'train': train_result,
        'accuracy': effective_accuracy,
        'high_confidence_rate': round(high_conf, 4),
        'done': done,
        'iteration': iteration,
        'remaining_merchants': len(get_label_queue(ctx, limit=100)),
    }


def run_iteration(ctx: SessionContext) -> dict:
    """Retrain + classify without new labels (e.g. after category edit)."""
    train_result = retrain_session(ctx)
    df_classified = classify_session(ctx)
    accuracy = train_result.get('accuracy')
    high_conf = float((df_classified['confidence'] >= 0.7).mean())
    effective = accuracy if accuracy is not None else high_conf
    done = effective is not None and effective >= TARGET_ACCURACY
    if done:
        _finalize_budget(ctx, df_classified)
        ctx.save_meta({'phase': 'dashboard', 'accuracy': effective})
    return {
        'train': train_result,
        'accuracy': effective,
        'done': done,
        'queue': get_label_queue(ctx),
    }


def _finalize_budget(ctx: SessionContext, df_classified: pd.DataFrame):
    meta = ctx.load_meta()
    income = meta.get('monthly_income', 8000.0)
    with open(ctx.budget_config, encoding='utf-8') as f:
        config = json.load(f)
    config['income'] = float(income)
    df = df_classified.copy()
    df['month'] = pd.to_datetime(df['timestamp']).dt.to_period('M')
    monthly = df.groupby(['month', 'category'])['amount'].sum().unstack(fill_value=0)
    for cat in ctx.load_categories():
        if cat not in config.get('categories', {}):
            config.setdefault('categories', {})[cat] = {
                'type': 'Want', 'avg_monthly': 0, 'monthly_budget': 200,
                'annual_budget': 2400, 'monthly': [],
            }
        entry = config['categories'][cat]
        if cat in monthly.columns and monthly[cat].sum() > 0:
            avg = float(monthly[cat].mean())
            budget = round(avg * 1.1, 0)
        else:
            avg = 0.0
            budget = entry.get('monthly_budget', 200)
        entry['avg_monthly'] = avg
        entry['monthly_budget'] = budget
        entry['annual_budget'] = budget * 12
    with open(ctx.budget_config, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    ctx.sync_to_project_data()


def get_session_status(ctx: SessionContext) -> dict:
    meta = ctx.load_meta()
    status = {
        'session_id': ctx.session_id,
        'phase': meta.get('phase', 'upload'),
        'iteration': meta.get('iteration', 0),
        'accuracy': meta.get('accuracy'),
        'target_accuracy': TARGET_ACCURACY,
        'categories': ctx.load_categories(),
        'transaction_count': meta.get('transaction_count', 0),
    }
    if ctx.transactions_classified.exists():
        df = pd.read_csv(ctx.transactions_classified)
        status['transaction_count'] = len(df)
        status['high_confidence_rate'] = round(float((df['confidence'] >= 0.7).mean()), 4)
    return status
