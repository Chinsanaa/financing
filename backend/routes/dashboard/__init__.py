"""Dashboard endpoints: stats, trends, category breakdowns.

Notes on postgrest-py usage: negated filters use the `.not_` PROPERTY
(e.g. `.not_.is_("category_id", "null")`). Calling `.not_(...)` raises
TypeError — it is not a method.

Package layout: every route group decorates the single shared `router`
defined in `_shared.py`; importing the submodules below registers the
routes. All 19 routes have distinct static paths, so import order cannot
change which handler matches a request.
"""
from ._shared import router  # noqa: F401  (included by main.py)
from . import overview, planning, notifications, reports, tour  # noqa: F401  (registers routes)

# Names other modules/tests historically imported from `routes.dashboard`.
from .reports import _sanitize_search  # noqa: F401
from budget import _month_start, _now_cn  # noqa: F401
