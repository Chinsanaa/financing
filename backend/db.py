"""Small Supabase/PostgREST helpers shared by routes and ml.py."""
from typing import Callable, List
import httpx
from starlette.concurrency import run_in_threadpool

PAGE_SIZE = 1000  # PostgREST's default max-rows cap per request


def _call_with_retry(build_query: Callable, retries: int = 1):
    """Call `build_query()`, retrying once on a dropped connection.

    The shared `supabase_client` (config.py) is created once at process
    startup and its httpx connection pool lives for the process's whole
    lifetime. When a pooled connection sits idle long enough, Supabase's
    edge (or Render's network layer) can close it server-side without
    telling the client; the *next* request to reuse that connection dies
    immediately with `httpx.RemoteProtocolError: Server disconnected`
    instead of transparently opening a fresh one. That single stale-socket
    failure was surfacing as a real 500 to users (e.g. dashboard/training
    tabs showing "Failed to load data") even though the query itself was
    fine. `build_query` must be a zero-arg callable safe to invoke more
    than once (rebuilds its own filter chain each call).
    """
    for attempt in range(retries + 1):
        try:
            return build_query()
        except httpx.TransportError:
            if attempt == retries:
                raise


async def run_query(build_query: Callable):
    """Run a PostgREST query builder off the event loop.

    `supabase-py` is a synchronous (httpx) client; calling `.execute()`
    directly inside an `async def` route blocks the whole event loop —
    under the single uvicorn worker this app runs, that freezes every other
    concurrent request until Supabase responds. `build_query` must be a
    zero-arg callable that builds AND executes the query (e.g.
    `lambda: supabase_client.table(...).select(...).execute()`).
    """
    return await run_in_threadpool(_call_with_retry, build_query)


def fetch_all(make_query: Callable, page_size: int = PAGE_SIZE) -> List[dict]:
    """Fetch every row of a query, paging past PostgREST's silent row cap.

    `make_query` must return a FRESH filter builder each call (builders are
    single-use once executed). Loops .range() pages until a short page.

    Sync — safe to call from ml.py's background thread (no event loop
    present there). Route handlers on the request path should use
    `fetch_all_async` instead so the paging loop doesn't block the loop.
    """
    rows: List[dict] = []
    offset = 0
    while True:
        page = _call_with_retry(
            lambda: make_query().range(offset, offset + page_size - 1).execute()
        ).data or []
        rows.extend(page)
        if len(page) < page_size:
            return rows
        offset += page_size


async def fetch_all_async(make_query: Callable, page_size: int = PAGE_SIZE) -> List[dict]:
    """Async counterpart of `fetch_all`, for use inside `async def` routes.

    Runs each page's `.execute()` in a threadpool via `run_query` so paging
    through a large table doesn't block the event loop for other requests.
    """
    rows: List[dict] = []
    offset = 0
    while True:
        result = await run_query(lambda: make_query().range(offset, offset + page_size - 1).execute())
        page = result.data or []
        rows.extend(page)
        if len(page) < page_size:
            return rows
        offset += page_size
