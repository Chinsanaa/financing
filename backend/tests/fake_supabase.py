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

    def order(self, col: str, desc: bool = False):
        return self

    def range(self, start: int, end: int):
        return self

    def limit(self, n: int):
        return self

    # --- mutations ---
    def insert(self, row: dict):
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
        return True


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
            row = dict(qb._payload)
            row.setdefault("id", f"{self.name}-{next(self._id_counter)}")
            self.rows.append(row)
            return FakeResponse(data=[row])

        if qb._op == "update":
            matched = [r for r in self.rows if qb._matches(r)]
            for r in matched:
                r.update(qb._payload)
            return FakeResponse(data=matched)

        if qb._op == "upsert":
            key_col = qb._on_conflict
            existing = next(
                (r for r in self.rows if key_col and r.get(key_col) == qb._payload.get(key_col)),
                None,
            )
            if existing is not None:
                existing.update(qb._payload)
                return FakeResponse(data=[existing])
            row = dict(qb._payload)
            row.setdefault("id", f"{self.name}-{next(self._id_counter)}")
            self.rows.append(row)
            return FakeResponse(data=[row])

        if qb._op == "delete":
            matched = [r for r in self.rows if qb._matches(r)]
            self.rows = [r for r in self.rows if r not in matched]
            return FakeResponse(data=matched)

        raise NotImplementedError(qb._op)


class FakeBucket:
    def __init__(self, name: str):
        self.name = name
        self.removed_paths: list[str] = []

    def list(self, prefix: str = ""):
        return []

    def remove(self, paths: list[str]):
        self.removed_paths.extend(paths)
        return paths


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


class FakeSupabaseClient:
    """Drop-in replacement for the real `supabase_client` in route modules."""

    def __init__(self):
        self._tables: dict[str, FakeTable] = {}
        self.storage = FakeStorage()
        self.auth = FakeAuth()

    def table(self, name: str) -> FakeQueryBuilder:
        return self._tables.setdefault(name, FakeTable(name)).query()

    def seed(self, table_name: str, rows: list[dict]):
        """Test helper: pre-populate a table with rows."""
        table = self._tables.setdefault(table_name, FakeTable(table_name))
        table.rows.extend(dict(r) for r in rows)
