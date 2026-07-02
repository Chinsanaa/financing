"""Per-user session workspace paths for the web onboarding flow."""
import json
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from paths import ROOT, STARTER_RULES, BUDGET_EXAMPLE, TEMPLATES

SESSIONS_ROOT = ROOT / 'data' / 'sessions'
TARGET_ACCURACY = 0.70
WEB_MIN_LABELED = 25
MAX_LABEL_ROUNDS = 15


@dataclass
class SessionContext:
    session_id: str
    root: Path

    @classmethod
    def create(cls) -> 'SessionContext':
        SESSIONS_ROOT.mkdir(parents=True, exist_ok=True)
        session_id = uuid.uuid4().hex[:12]
        root = SESSIONS_ROOT / session_id
        ctx = cls(session_id=session_id, root=root)
        ctx.init_workspace()
        return ctx

    @classmethod
    def load(cls, session_id: str) -> 'SessionContext':
        root = SESSIONS_ROOT / session_id
        if not root.exists():
            raise FileNotFoundError(f'Session not found: {session_id}')
        return cls(session_id=session_id, root=root)

    def init_workspace(self):
        for sub in ('raw', 'labeled', 'processed', 'exports', 'reports'):
            (self.root / sub).mkdir(parents=True, exist_ok=True)
        shutil.copy(STARTER_RULES, self.merchant_rules)
        shutil.copy(BUDGET_EXAMPLE, self.budget_config)
        self.save_categories(self.default_categories())
        self.save_meta({'iteration': 0, 'phase': 'upload', 'accuracy': None})

    @staticmethod
    def default_categories() -> List[str]:
        return [
            'Groceries', 'Transportation', 'Utilities & Services',
            'Eating Out', 'Shopping', 'Transfers & Gifts', 'Other',
        ]

    @property
    def meta_path(self) -> Path:
        return self.root / 'session.json'

    @property
    def categories_path(self) -> Path:
        return self.root / 'categories.json'

    @property
    def raw_dir(self) -> Path:
        return self.root / 'raw'

    @property
    def alipay_path(self) -> Path:
        return self.raw_dir / 'alipay.csv'

    @property
    def wechat_path(self) -> Path:
        return self.raw_dir / 'raw-wechat.xlsx'

    @property
    def merchant_rules(self) -> Path:
        return self.root / 'labeled' / 'merchant_rules_expanded.csv'

    @property
    def labeled_txns(self) -> Path:
        return self.root / 'labeled' / 'labeled_transactions.csv'

    @property
    def transactions(self) -> Path:
        return self.root / 'processed' / 'transactions.csv'

    @property
    def transactions_classified(self) -> Path:
        return self.root / 'processed' / 'transactions_classified.csv'

    @property
    def classifier(self) -> Path:
        return self.root / 'processed' / 'classifier.pkl'

    @property
    def vectorizer(self) -> Path:
        return self.root / 'processed' / 'tfidf_vectorizer.pkl'

    @property
    def budget_config(self) -> Path:
        return self.root / 'budget_config.json'

    def load_meta(self) -> dict:
        if not self.meta_path.exists():
            return {}
        with open(self.meta_path, encoding='utf-8') as f:
            return json.load(f)

    def save_meta(self, updates: dict):
        meta = self.load_meta()
        meta.update(updates)
        with open(self.meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2)

    def load_categories(self) -> List[str]:
        if not self.categories_path.exists():
            return self.default_categories()
        with open(self.categories_path, encoding='utf-8') as f:
            data = json.load(f)
        cats = data.get('categories', self.default_categories())
        return [c for c in cats if str(c).strip()]

    def save_categories(self, categories: List[str]):
        cleaned = [str(c).strip() for c in categories if str(c).strip()]
        if not cleaned:
            cleaned = self.default_categories()
        with open(self.categories_path, 'w', encoding='utf-8') as f:
            json.dump({'categories': cleaned}, f, indent=2, ensure_ascii=False)

    def sync_to_project_data(self):
        """Copy session artifacts to data/ for Streamlit dashboard."""
        from paths import DATA, LABELED, PROCESSED, BUDGET_CONFIG as GLOBAL_BUDGET
        for d in (DATA / 'raw', LABELED, PROCESSED):
            d.mkdir(parents=True, exist_ok=True)
        if self.alipay_path.exists():
            shutil.copy(self.alipay_path, DATA / 'raw' / 'alipay.csv')
        if self.wechat_path.exists():
            shutil.copy(self.wechat_path, DATA / 'raw' / 'raw-wechat.xlsx')
        if self.merchant_rules.exists():
            shutil.copy(self.merchant_rules, LABELED / 'merchant_rules_expanded.csv')
        if self.labeled_txns.exists():
            shutil.copy(self.labeled_txns, LABELED / 'labeled_transactions.csv')
        for name in ('transactions.csv', 'transactions_classified.csv'):
            src = self.root / 'processed' / name
            if src.exists():
                shutil.copy(src, PROCESSED / name)
        for name in ('classifier.pkl', 'tfidf_vectorizer.pkl'):
            src = self.root / 'processed' / name
            if src.exists():
                shutil.copy(src, PROCESSED / name)
        if self.budget_config.exists():
            shutil.copy(self.budget_config, GLOBAL_BUDGET)
