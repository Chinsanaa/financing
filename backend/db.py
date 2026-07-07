"""Small Supabase/PostgREST helpers shared by routes and ml.py."""
from typing import Callable, List

PAGE_SIZE = 1000  # PostgREST's default max-rows cap per request


def fetch_all(make_query: Callable, page_size: int = PAGE_SIZE) -> List[dict]:
    """Fetch every row of a query, paging past PostgREST's silent row cap.

    `make_query` must return a FRESH filter builder each call (builders are
    single-use once executed). Loops .range() pages until a short page.
    """
    rows: List[dict] = []
    offset = 0
    while True:
        page = make_query().range(offset, offset + page_size - 1).execute().data or []
        rows.extend(page)
        if len(page) < page_size:
            return rows
        offset += page_size
