"""In-memory fake of the tiny slice of the Supabase/postgrest-py query
builder the routes under test actually use.

Deliberately NOT a MagicMock. A mock configured to "return some data" would
make every isolation test pass regardless of whether a route handler
actually filters by user_id — it would test nothing. This fake stores real
rows and applies the recorded .eq()/.neq()/.is_() filters for real, so if a
route ever drops a `.eq("user_id", user_id)` filter, the fake DB genuinely
returns the wrong rows and the test genuinely fails.

Only supports the operations exercised by backend/tests/*.py. Extend as
more routes get covered.
"""
import itertools
from datetime import datetime, timezone
from typing import Any, Optional


class FakeResponse:
    def __init__(self, data: list, count: Optional[int] = None):
        self.data = data
        self.count = count


class _NotFilter:
    """Returned by `FakeQueryBuilder.not_` — negates the next filter call."""

    def __init__(self, qb: "FakeQueryBuilder"):
        self._qb = qb

    def is_(self, col: str, val: Any):
        self._qb._filters.append(("not_is", col, val))
        return self._qb


class FakeQueryBuilder:
    def __init__(self, table: "FakeTable"):
        self._table = table
        self._op = "select"
        self._filters: list[tuple[str, str, Any]] = []
        self._or_filter: Optional[str] = None
        self._count_mode: Optional[str] = None
        self._payload: Optional[dict] = None
        self._on_conflict: Optional[str] = None
        self._ignore_duplicates: bool = False
        self._order: Optional[tuple] = None

    # --- filters ---
    def select(self, columns: str = "*", count: Optional[str] = None):
        self._count_mode = count
        return self

    def eq(self, col: str, val: Any):
        self._filters.append(("eq", col, val))
        return self

    def neq(self, col: str, val: Any):
        self._filters.append(("neq", col, val))
        return self

    def is_(self, col: str, val: Any):
        self._filters.append(("is", col, val))
        return self

    def gte(self, col: str, val: Any):
        self._filters.append(("gte", col, val))
        return self

    def lte(self, col: str, val: Any):
        self._filters.append(("lte", col, val))
        return self

    def lt(self, col: str, val: Any):
        self._filters.append(("lt", col, val))
        return self

    def ilike(self, col: str, pattern: str):
        """Only supports the '%substring%' shape this codebase actually
        generates — not general SQL LIKE wildcard positions."""
        self._filters.append(("ilike", col, pattern))
        return self

    def in_(self, col: str, values: list):
        self._filters.append(("in", col, list(values)))
        return self

    @property
    def not_(self) -> "_NotFilter":
        """postgrest-py exposes `.not_` as a PROPERTY (not a method) whose
        methods negate the next filter, e.g. `.not_.is_("category_id", "null")`.
        See the module docstring in backend/routes/dashboard.py for why this
        matters — calling `.not_(...)` raises TypeError on the real client."""
        return _NotFilter(self)

    def or_(self, filter_str: str):
        """Supports the one shape this codebase actually uses:
        'col.is.null,col.eq.value' — PostgREST's comma-separated OR syntax.
        Matches if ANY listed condition is true (ANDed with other filters)."""
        self._or_filter = filter_str
        return self

    def order(self, col: str, desc: bool = False, foreign_table: Optional[str] = None):
        self._order = (col, desc, foreign_table)
        return self

    def range(self, start: int, end: int):
        return self

    def limit(self, n: int):
        return self

    # --- mutations ---
    def insert(self, row):
        """`row` is a single dict, or a list of dicts (bulk insert)."""
        self._op = "insert"
        self._payload = row
        return self

    def update(self, data: dict):
        self._op = "update"
        self._payload = data
        return self

    def upsert(self, data: dict, on_conflict: Optional[str] = None, ignore_duplicates: bool = False):
        self._op = "upsert"
        self._payload = data
        self._on_conflict = on_conflict
        self._ignore_duplicates = ignore_duplicates
        return self

    def delete(self):
        self._op = "delete"
        return self

    # --- terminal ---
    def execute(self) -> FakeResponse:
        return self._table._run(self)

    def _matches(self, row: dict) -> bool:
        for kind, col, val in self._filters:
            if kind == "eq" and row.get(col) != val:
                return False
            if kind == "neq" and row.get(col) == val:
                return False
            if kind == "is" and val == "null" and row.get(col) is not None:
                return False
            if kind == "not_is" and val == "null" and row.get(col) is None:
                return False
            if kind == "gte" and not (row.get(col) is not None and row.get(col) >= val):
                return False
            if kind == "lte" and not (row.get(col) is not None and row.get(col) <= val):
                return False
            if kind == "lt" and not (row.get(col) is not None and row.get(col) < val):
                return False
            if kind == "ilike" and not _ilike_matches(row.get(col), val):
                return False
            if kind == "in" and row.get(col) not in val:
                return False
        if self._or_filter:
            conditions = self._or_filter.split(",")
            if not any(self._or_condition_matches(row, cond) for cond in conditions):
                return False
        return True

    @staticmethod
    def _or_condition_matches(row: dict, condition: str) -> bool:
        if ".not.is." in condition:
            # PostgREST's negated-is inside an OR clause, e.g.
            # "category_id.not.is.null" — must be checked before the generic
            # 3-way split below, since naively splitting on "." would parse
            # this as op="not" and misroute it.
            col, val = condition.split(".not.is.")
            return row.get(col) is not None if val == "null" else row.get(col) is None
        col, op, val = condition.split(".", 2)
        if op == "is":
            return row.get(col) is None if val == "null" else row.get(col) is not None
        if op == "eq":
            if val in ("true", "false"):
                return row.get(col) is (val == "true")
            return str(row.get(col)) == val
        if op == "ilike":
            return _ilike_matches(row.get(col), val)
        return False


def _ilike_matches(value: Any, pattern: str) -> bool:
    """Case-insensitive '%substring%' match — the only ilike shape this
    codebase generates (backend/routes/dashboard.py's reports `search`)."""
    if value is None:
        return False
    needle = pattern.strip("%").lower()
    return needle in str(value).lower()


class FakeTable:
    _id_counter = itertools.count(1)

    def __init__(self, name: str):
        self.name = name
        self.rows: list[dict] = []

    def query(self) -> FakeQueryBuilder:
        return FakeQueryBuilder(self)

    def _run(self, qb: FakeQueryBuilder) -> FakeResponse:
        if qb._op == "select":
            matched = [r for r in self.rows if qb._matches(r)]
            count = len(matched) if qb._count_mode == "exact" else None
            if qb._order:
                col, desc, foreign_table = qb._order

                def sort_key(row):
                    value = (row.get(foreign_table) or {}).get(col) if foreign_table else row.get(col)
                    return (value is None, value)

                matched = sorted(matched, key=sort_key, reverse=desc)
            return FakeResponse(data=matched, count=count)

        if qb._op == "insert":
            payload = qb._payload if isinstance(qb._payload, list) else [qb._payload]
            inserted = []
            for item in payload:
                row = dict(item)
                row.setdefault("id", f"{self.name}-{next(self._id_counter)}")
                # Real Postgres tables default created_at to now() — mirror
                # that here since some routes read it back (e.g. the
                # duplicate-upload message quotes the earlier upload's date).
                row.setdefault("created_at", datetime.now(timezone.utc).isoformat())
                self.rows.append(row)
                inserted.append(row)
            return FakeResponse(data=inserted)

        if qb._op == "update":
            matched = [r for r in self.rows if qb._matches(r)]
            for r in matched:
                r.update(qb._payload)
            return FakeResponse(data=matched)

        if qb._op == "upsert":
            key_cols = [c.strip() for c in qb._on_conflict.split(",")] if qb._on_conflict else []
            payload = qb._payload if isinstance(qb._payload, list) else [qb._payload]
            upserted = []
            for item in payload:
                existing = next(
                    (
                        r for r in self.rows
                        if key_cols and all(r.get(c) == item.get(c) for c in key_cols)
                    ),
                    None,
                )
                if existing is not None:
                    if qb._ignore_duplicates:
                        # ON CONFLICT DO NOTHING: existing row is untouched
                        # and NOT included in the returned/RETURNING rows —
                        # callers use an empty response to detect "already
                        # existed" vs "just inserted" (see budget_alerts
                        # de-dup in backend/alerts.py).
                        continue
                    existing.update(item)
                    upserted.append(existing)
                else:
                    row = dict(item)
                    row.setdefault("id", f"{self.name}-{next(self._id_counter)}")
                    self.rows.append(row)
                    upserted.append(row)
            return FakeResponse(data=upserted)

        if qb._op == "delete":
            matched = [r for r in self.rows if qb._matches(r)]
            self.rows = [r for r in self.rows if r not in matched]
            return FakeResponse(data=matched)

        raise NotImplementedError(qb._op)


class FakeBucket:
    def __init__(self, name: str):
        self.name = name
        self.removed_paths: list[str] = []
        self.objects: dict[str, bytes] = {}

    def list(self, prefix: str = ""):
        return []

    # No `list[str]` annotation here on purpose: the `list` method defined
    # just above shadows the builtin `list` in this class body, so a
    # `paths: list[str]` signature annotation would raise
    # "'function' object is not subscriptable" the moment this class is
    # defined.
    def remove(self, paths):
        self.removed_paths.extend(paths)
        for p in paths:
            self.objects.pop(p, None)
        return paths

    def upload(self, path: str, content: bytes):
        self.objects[path] = content
        return {"path": path}


class FakeStorage:
    def __init__(self):
        self.buckets: dict[str, FakeBucket] = {}

    def from_(self, bucket_name: str) -> FakeBucket:
        return self.buckets.setdefault(bucket_name, FakeBucket(bucket_name))


class FakeUser:
    def __init__(self, email: Optional[str]):
        self.email = email


class FakeUserResponse:
    def __init__(self, user: Optional[FakeUser]):
        self.user = user


class FakeAuthAdmin:
    def __init__(self):
        self.deleted_user_ids: list[str] = []
        # user_id -> email, set via seed_user_email() in tests that need
        # get_user_by_id (e.g. budget-alert emails looking up the recipient).
        self.emails: dict[str, str] = {}

    def delete_user(self, user_id: str):
        self.deleted_user_ids.append(user_id)

    def get_user_by_id(self, user_id: str) -> FakeUserResponse:
        return FakeUserResponse(FakeUser(self.emails.get(user_id)))


class FakeAuth:
    def __init__(self):
        self.admin = FakeAuthAdmin()


class FakeRPCCall:
    def __init__(self, client: "FakeSupabaseClient", name: str, params: dict):
        self._client = client
        self._name = name
        self._params = params

    def execute(self) -> FakeResponse:
        handler = self._client.rpc_handlers.get(self._name)
        data = handler(self._params) if handler else None
        return FakeResponse(data=data)


class FakeSupabaseClient:
    """Drop-in replacement for the real `supabase_client` in route modules."""

    def __init__(self):
        self._tables: dict[str, FakeTable] = {}
        self.storage = FakeStorage()
        self.auth = FakeAuth()
        # name -> callable(params) -> data, for supabase_client.rpc(name, params).
        # spend_by_category_for_user gets a real default (computed from seeded
        # rows, mirroring the SQL RPC's union-then-aggregate logic) since it
        # backs heavily-tested budget/action endpoints — every other RPC here
        # (sum_user_transactions, monthly_spend_by_user, get_email_for_username)
        # has no such default and tests register per-test lambdas instead,
        # because nothing in this suite currently exercises those endpoints
        # heavily enough to need one.
        self.rpc_handlers: dict[str, Any] = {
            "spend_by_category_for_user": self._default_spend_by_category_for_user,
        }

    def table(self, name: str) -> FakeQueryBuilder:
        return self._tables.setdefault(name, FakeTable(name)).query()

    def _default_spend_by_category_for_user(self, params: dict) -> list:
        user_id = params.get("p_user_id")
        start = params.get("p_start")
        end = params.get("p_end")

        def in_window(timestamp: Optional[str]) -> bool:
            if timestamp is None:
                return False
            if start and timestamp < start:
                return False
            if end and timestamp >= end:
                return False
            return True

        categories = self._tables.get("categories")
        cat_name_by_id = {c["id"]: c["name"] for c in categories.rows} if categories else {}

        contributions: list[tuple[str, float]] = []

        transactions = self._tables.get("transactions")
        if transactions:
            for t in transactions.rows:
                if t.get("user_id") != user_id or t.get("is_split") or not t.get("category_id"):
                    continue
                if not in_window(t.get("timestamp")):
                    continue
                contributions.append((t["category_id"], float(t.get("amount", 0))))

            splits = self._tables.get("transaction_splits")
            if splits:
                txn_by_id = {t["id"]: t for t in transactions.rows}
                for s in splits.rows:
                    if s.get("user_id") != user_id:
                        continue
                    parent = txn_by_id.get(s.get("transaction_id"))
                    if not parent or not in_window(parent.get("timestamp")):
                        continue
                    contributions.append((s["category_id"], float(s.get("amount", 0))))

        totals: dict[str, float] = {}
        counts: dict[str, int] = {}
        for cat_id, amount in contributions:
            totals[cat_id] = totals.get(cat_id, 0) + amount
            counts[cat_id] = counts.get(cat_id, 0) + 1

        return [
            {
                "category_id": cat_id,
                "category_name": cat_name_by_id.get(cat_id, "Unknown"),
                "amount": total,
                "txn_count": counts[cat_id],
            }
            for cat_id, total in totals.items()
        ]

    def rpc(self, name: str, params: dict) -> FakeRPCCall:
        return FakeRPCCall(self, name, params)

    def seed(self, table_name: str, rows: list[dict]):
        """Test helper: pre-populate a table with rows."""
        table = self._tables.setdefault(table_name, FakeTable(table_name))
        table.rows.extend(dict(r) for r in rows)

    def seed_user_email(self, user_id: str, email: str):
        """Test helper: make auth.admin.get_user_by_id(user_id) resolve an email."""
        self.auth.admin.emails[user_id] = email
