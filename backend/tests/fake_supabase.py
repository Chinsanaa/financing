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


class FakeQueryBuilder:
    def __init__(self, table: "FakeTable"):
        self._table = table
        self._op = "select"
        self._filters: list[tuple[str, str, Any]] = []
        self._or_filter: Optional[str] = None
        self._count_mode: Optional[str] = None
        self._payload: Optional[dict] = None
        self._on_conflict: Optional[str] = None

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

    def or_(self, filter_str: str):
        """Supports the one shape this codebase actually uses:
        'col.is.null,col.eq.value' — PostgREST's comma-separated OR syntax.
        Matches if ANY listed condition is true (ANDed with other filters)."""
        self._or_filter = filter_str
        return self

    def order(self, col: str, desc: bool = False):
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

    def upsert(self, data: dict, on_conflict: Optional[str] = None):
        self._op = "upsert"
        self._payload = data
        self._on_conflict = on_conflict
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
            if kind == "gte" and not (row.get(col) is not None and row.get(col) >= val):
                return False
            if kind == "lte" and not (row.get(col) is not None and row.get(col) <= val):
                return False
        if self._or_filter:
            conditions = self._or_filter.split(",")
            if not any(self._or_condition_matches(row, cond) for cond in conditions):
                return False
        return True

    @staticmethod
    def _or_condition_matches(row: dict, condition: str) -> bool:
        col, op, val = condition.split(".", 2)
        if op == "is":
            return row.get(col) is None if val == "null" else row.get(col) is not None
        if op == "eq":
            return str(row.get(col)) == val
        return False


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


class FakeAuthAdmin:
    def __init__(self):
        self.deleted_user_ids: list[str] = []

    def delete_user(self, user_id: str):
        self.deleted_user_ids.append(user_id)


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
        # name -> callable(params) -> data, for supabase_client.rpc(name, params)
        self.rpc_handlers: dict[str, Any] = {}

    def table(self, name: str) -> FakeQueryBuilder:
        return self._tables.setdefault(name, FakeTable(name)).query()

    def rpc(self, name: str, params: dict) -> FakeRPCCall:
        return FakeRPCCall(self, name, params)

    def seed(self, table_name: str, rows: list[dict]):
        """Test helper: pre-populate a table with rows."""
        table = self._tables.setdefault(table_name, FakeTable(table_name))
        table.rows.extend(dict(r) for r in rows)
