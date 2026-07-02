"""Flask web app: upload, label, iterate, dashboard."""
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from dashboard_data import build_dashboard_tab
from session_context import SessionContext
from translate import description_label_english, merchant_label_english
from web_pipeline import (
    apply_merchant_labels,
    get_label_queue,
    get_session_status,
    parse_uploads,
    run_iteration,
)

WEB_ROOT = Path(__file__).resolve().parent.parent / 'web'

app = Flask(
    __name__,
    template_folder=str(WEB_ROOT / 'templates'),
    static_folder=str(WEB_ROOT / 'static'),
)
app.secret_key = 'finance-categorizer-dev-change-in-production'


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/sessions', methods=['POST'])
def create_session():
    ctx = SessionContext.create()
    return jsonify({'session_id': ctx.session_id})


@app.route('/api/sessions/<session_id>/upload', methods=['POST'])
def upload_files(session_id):
    try:
        ctx = SessionContext.load(session_id)
    except FileNotFoundError:
        return jsonify({'error': 'Session not found'}), 404

    alipay = request.files.get('alipay')
    wechat = request.files.get('wechat')
    if not alipay and not wechat:
        return jsonify({'error': 'Provide alipay.csv and/or wechat .xlsx'}), 400

    ctx.raw_dir.mkdir(parents=True, exist_ok=True)
    if alipay and alipay.filename:
        alipay.save(ctx.alipay_path)
    if wechat and wechat.filename:
        wechat.save(ctx.wechat_path)

    income = request.form.get('monthly_income', type=float) or 8000.0
    ctx.save_meta({'monthly_income': income})

    try:
        result = parse_uploads(ctx)
    except Exception as exc:
        return jsonify({'error': str(exc)}), 400

    return jsonify(result)


@app.route('/api/sessions/<session_id>/categories', methods=['GET', 'PUT'])
def categories(session_id):
    try:
        ctx = SessionContext.load(session_id)
    except FileNotFoundError:
        return jsonify({'error': 'Session not found'}), 404

    if request.method == 'GET':
        return jsonify({'categories': ctx.load_categories()})

    body = request.get_json(force=True) or {}
    cats = body.get('categories', [])
    ctx.save_categories(cats)
    ctx.save_meta({'phase': 'label'})
    return jsonify({'categories': ctx.load_categories()})


@app.route('/api/sessions/<session_id>/label-queue')
def label_queue(session_id):
    try:
        ctx = SessionContext.load(session_id)
    except FileNotFoundError:
        return jsonify({'error': 'Session not found'}), 404
    return jsonify({'merchants': get_label_queue(ctx, limit=10)})


@app.route('/api/sessions/<session_id>/labels', methods=['POST'])
def submit_labels(session_id):
    try:
        ctx = SessionContext.load(session_id)
    except FileNotFoundError:
        return jsonify({'error': 'Session not found'}), 404

    body = request.get_json(force=True) or {}
    labels = body.get('labels', [])
    if not labels:
        return jsonify({'error': 'No labels provided'}), 400

    try:
        result = apply_merchant_labels(ctx, labels)
    except Exception as exc:
        return jsonify({'error': str(exc)}), 400

    return jsonify(result)


@app.route('/api/sessions/<session_id>/iterate', methods=['POST'])
def iterate(session_id):
    try:
        ctx = SessionContext.load(session_id)
    except FileNotFoundError:
        return jsonify({'error': 'Session not found'}), 404
    return jsonify(run_iteration(ctx))


@app.route('/api/sessions/<session_id>/status')
def status(session_id):
    try:
        ctx = SessionContext.load(session_id)
    except FileNotFoundError:
        return jsonify({'error': 'Session not found'}), 404
    return jsonify(get_session_status(ctx))


@app.route('/api/sessions/<session_id>/dashboard/<tab>')
def dashboard_tab(session_id, tab):
    try:
        ctx = SessionContext.load(session_id)
    except FileNotFoundError:
        return jsonify({'error': 'Session not found'}), 404
    if ctx.load_meta().get('phase') != 'dashboard':
        return jsonify({'error': 'Complete labeling first'}), 400
    try:
        return jsonify(build_dashboard_tab(ctx, tab))
    except Exception as exc:
        return jsonify({'error': str(exc)}), 400


@app.route('/api/sessions/<session_id>/export')
def export_csv(session_id):
    try:
        ctx = SessionContext.load(session_id)
    except FileNotFoundError:
        return jsonify({'error': 'Session not found'}), 404
    if not ctx.transactions_classified.exists():
        return jsonify({'error': 'No classified data'}), 404
    # Export English-only CSV for non-Chinese users
    df = pd.read_csv(ctx.transactions_classified)
    df['merchant_en'] = df['merchant'].map(merchant_label_english)
    df['description_en'] = df['description'].map(description_label_english)

    keep_cols = [
        'timestamp',
        'merchant_en',
        'description_en',
        'amount',
        'source',
        'category',
    ]
    if 'confidence' in df.columns:
        keep_cols.append('confidence')
    if 'needs_review' in df.columns:
        keep_cols.append('needs_review')

    df_out = df[[c for c in keep_cols if c in df.columns]].copy()
    export_path = ctx.root / 'exports' / 'transactions_classified_en.csv'
    export_path.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(export_path, index=False, encoding='utf-8-sig')

    return send_file(export_path, as_attachment=True, download_name='transactions_classified_en.csv')


if __name__ == '__main__':
    print('Finance Categorizer UI: http://127.0.0.1:5000')
    # use_reloader=False — avoids mid-request restarts during sklearn/jieba imports
    app.run(host='127.0.0.1', port=5000, debug=True, use_reloader=False)
