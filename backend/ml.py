"""Per-user model loading and bulk transaction classification.

This is the glue the product was missing: uploads insert unlabeled rows and
training uploads artifacts to Storage, but nothing ever LOADED a model to
classify anything. Now:

- `classify_user_transactions(user_id)` runs after every upload (rules-only
  when the user has no trained model yet) and after every successful
  training run.
- Rules (global + user merchant_rules) are trusted: category applied,
  needs_review=False.
- Model predictions are suggestions: stored on category_id + confidence with
  needs_review=True (the review queue renders category_id as
  "suggested_category"), EXCEPT calibrated two-model agreement
  (label_source='model_agreed'), which auto-applies per src/classify.py's
  graduated-trust gate.
- Rows still unclassified after rules + model (label_source='none' — no rule
  matched and no trained model exists yet) get one more, most-expensive
  fallback pass: a batched LLM call (src/llm_classify.py, Groq's free-tier
  API) using the user's CURRENT category names, so it works for merchant
  vocabulary this codebase has never seen and is immune to category renames.
  LLM results are always suggestions (label_source='llm', needs_review=True)
  — never auto-applied.

Model bundles are cached in-process per (user_id, model_run_id); a new
training run invalidates the cache via `invalidate_user_bundle`.
"""
import tempfile
import threading
from pathlib import Path
from typing import Optional

import pandas as pd

from config import settings, supabase_client
from errors import logger

from src.classify import classify_all, load_model_bundle, ModelBundle  # noqa: E402
from src.llm_classify import classify_with_llm  # noqa: E402

# Safety valve: cap how many distinct merchants one classification pass will
# send to the LLM, so one big/weird upload can't spike cost in a single call.
# Anything beyond the cap is simply left for the next pass / manual review,
# same as if this fallback tier didn't run at all.
_LLM_MERCHANT_CAP = 40

# Artifact file names, keyed the same way training.py's paths dict is.
ARTIFACT_FILES = {
    'classifier': 'classifier.pkl',
    'vectorizer': 'tfidf_vectorizer.pkl',
    'vectorizer_hybrid': 'tfidf_vectorizer_hybrid.pkl',
    'vectorizer_config': 'vectorizer_config.pkl',
    'semantic_model': 'semantic_classifier.pkl',
    'semantic_index': 'semantic_index.pkl',
    'semantic_calibrator': 'semantic_calibrator.pkl',
    'tfidf_calibrator': 'tfidf_calibrator.pkl',
    'ensemble_config': 'ensemble_config.json',
}

# In-process bundle cache: user_id -> (model_run_id, ModelBundle, temp_dir).
# The temp dir must outlive the bundle (semantic encoder may lazy-read).
_bundle_cache: dict = {}
_cache_lock = threading.Lock()
_MAX_CACHED_USERS = 8


def invalidate_user_bundle(user_id: str) -> None:
    with _cache_lock:
        _bundle_cache.pop(user_id, None)


# --- Classification scheduling: at most one worker thread per user ---
#
# A multi-file upload batch fires one schedule request per file. Each one
# used to spawn its own daemon thread rescanning the user's *entire*
# needs_review set, so N files meant N redundant full-table passes racing
# each other. Instead: if a worker is already running for this user, just
# flag that it should run once more when it finishes, rather than starting
# a second thread. This coalesces per *process* — if the backend ever runs
# multiple worker processes, each could hold one thread — but it's still
# strictly better than one thread per file, and the underlying updates are
# idempotent (same input always produces the same label), so an occasional
# extra concurrent pass is wasteful, not corrupting.
_classify_lock = threading.Lock()
_running_users: set = set()   # users with a live classification worker
_rerun_users: set = set()     # users who asked again while that worker ran


def request_classification(user_id: str) -> bool:
    """Ask for `user_id`'s pending rows to be classified in the background.

    Returns True if this call started a new worker thread, False if a
    worker was already running (in which case it will simply loop once
    more before exiting, and will see this request's rows because uploads
    commit their transactions before calling this).
    """
    with _classify_lock:
        if user_id in _running_users:
            _rerun_users.add(user_id)
            return False
        _running_users.add(user_id)

    try:
        threading.Thread(
            target=_classification_worker, args=(user_id,),
            name=f"classify-{user_id[:8]}", daemon=True,
        ).start()
    except Exception:
        # Thread failed to start — don't leave the user permanently
        # locked out of classification.
        with _classify_lock:
            _running_users.discard(user_id)
            _rerun_users.discard(user_id)
        raise
    return True


def _classification_worker(user_id: str) -> None:
    try:
        while True:
            classify_user_transactions(user_id)  # never raises; catches internally
            with _classify_lock:
                if user_id in _rerun_users:
                    _rerun_users.discard(user_id)
                    continue
                _running_users.discard(user_id)
                return
    except BaseException:
        # Defensive: a crash here must not wedge this user out of
        # classification forever.
        with _classify_lock:
            _running_users.discard(user_id)
            _rerun_users.discard(user_id)
        raise


def _latest_succeeded_run(user_id: str) -> Optional[dict]:
    resp = (
        supabase_client.table("model_runs")
        .select("id, artifact_version")
        .eq("user_id", user_id)
        .eq("status", "succeeded")
        .order("finished_at", desc=True)
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else None


def get_user_bundle(user_id: str) -> Optional[ModelBundle]:
    """Load (with caching) the user's latest trained model bundle from
    Storage. Returns None when the user has no successful training run —
    callers then classify rules-only."""
    run = _latest_succeeded_run(user_id)
    if not run or not run.get("artifact_version"):
        return None

    run_id = run["id"]
    with _cache_lock:
        cached = _bundle_cache.get(user_id)
        if cached and cached[0] == run_id:
            return cached[1]

    prefix = run["artifact_version"].rstrip("/")
    temp_dir = tempfile.mkdtemp(prefix=f"bundle_{user_id[:8]}_")
    paths = {key: Path(temp_dir) / fname for key, fname in ARTIFACT_FILES.items()}

    storage = supabase_client.storage.from_("model_artifacts")
    downloaded = 0
    for key, fname in ARTIFACT_FILES.items():
        try:
            content = storage.download(f"{prefix}/{fname}")
            paths[key].write_bytes(content)
            downloaded += 1
        except Exception:
            # Optional artifact (e.g. no semantic model) — bundle degrades
            # gracefully, exactly like the CLI path.
            continue

    if downloaded == 0:
        logger.warning("No artifacts found in Storage for user %s run %s", user_id, run_id)
        return None

    bundle = load_model_bundle(paths)
    if bundle.classifier is None:
        logger.warning("Artifacts for user %s run %s did not contain a usable classifier", user_id, run_id)
        return None

    with _cache_lock:
        if len(_bundle_cache) >= _MAX_CACHED_USERS:
            _bundle_cache.pop(next(iter(_bundle_cache)))
        _bundle_cache[user_id] = (run_id, bundle, temp_dir)
    return bundle


def _fetch_rules(user_id: str) -> dict:
    """Global + user merchant rules as {pattern: category_name}. User rules
    override global ones on pattern collisions."""
    resp = (
        supabase_client.table("merchant_rules")
        .select("user_id, merchant_pattern, category_name")
        .or_(f"user_id.is.null,user_id.eq.{user_id}")
        .execute()
    )
    rules: dict = {}
    user_patterns = set()
    for row in resp.data or []:
        pattern = str(row["merchant_pattern"]).strip().lower()
        if row["user_id"] is not None:
            rules[pattern] = row["category_name"]
            user_patterns.add(pattern)
        elif pattern not in user_patterns:
            rules.setdefault(pattern, row["category_name"])
    return rules


def _fetch_categories(user_id: str) -> tuple:
    """-> (name -> id map, valid category names, catch-all name)."""
    resp = (
        supabase_client.table("categories")
        .select("id, name, is_catch_all")
        .eq("user_id", user_id)
        .execute()
    )
    name_to_id = {row["name"]: row["id"] for row in resp.data or []}
    catch_all = next((row["name"] for row in (resp.data or []) if row["is_catch_all"]), "Other")
    return name_to_id, list(name_to_id.keys()), catch_all


def _llm_fallback_suggestions(result, categories: list[str]) -> dict:
    """Rows classify_all left as label_source='none' (no rule, no trained
    model) get one more try via the LLM, keyed by transaction id.

    Cost controls: skipped entirely if no API key is configured; deduped so
    each distinct merchant string costs one line-item in ONE batched call,
    not one call per transaction; capped at _LLM_MERCHANT_CAP distinct
    merchants per pass. Every LLM answer is a suggestion only — the caller
    still sets needs_review=True and never auto-applies it.
    """
    if not settings.groq_api_key or not categories:
        return {}

    none_rows = result[result["label_source"] == "none"]
    if none_rows.empty:
        return {}

    unique_merchants = none_rows["merchant"].astype(str).str.strip().unique().tolist()
    if len(unique_merchants) > _LLM_MERCHANT_CAP:
        unique_merchants = unique_merchants[:_LLM_MERCHANT_CAP]

    # One representative description per merchant keeps the batch small.
    items = []
    for merchant in unique_merchants:
        sample = none_rows[none_rows["merchant"].astype(str).str.strip() == merchant].iloc[0]
        items.append({"merchant": merchant, "description": sample.get("description", "")})

    answers = classify_with_llm(items, categories)

    merchant_to_answer = {
        m: a for m, a in zip(unique_merchants, answers) if a is not None
    }
    if not merchant_to_answer:
        return {}

    suggestions = {}
    for _, row in none_rows.iterrows():
        merchant = str(row["merchant"]).strip()
        answer = merchant_to_answer.get(merchant)
        if answer is not None:
            suggestions[row["id"]] = answer
    return suggestions


def classify_user_transactions(user_id: str) -> int:
    """Classify all of a user's pending-review, not-manually-labeled rows.

    Returns the number of rows updated. Never raises — this runs in
    background threads where an exception would just vanish.
    """
    try:
        return _classify_user_transactions(user_id)
    except Exception as e:
        logger.exception("Classification failed for user %s: %s", user_id, e)
        return 0


def _classify_user_transactions(user_id: str) -> int:
    from db import fetch_all

    rows = fetch_all(
        lambda: supabase_client.table("transactions")
        .select("id, timestamp, merchant, description, amount")
        .eq("user_id", user_id)
        .eq("needs_review", True)
        .eq("is_manually_labeled", False)
    )
    if not rows:
        return 0

    df = pd.DataFrame(rows)
    df["merchant"] = df["merchant"].fillna("")
    df["description"] = df["description"].fillna("")

    name_to_id, valid_categories, catch_all = _fetch_categories(user_id)
    if not name_to_id:
        logger.warning("User %s has no categories; skipping classification", user_id)
        return 0

    rules = _fetch_rules(user_id)
    bundle = get_user_bundle(user_id)

    result = classify_all(
        df,
        bundle=bundle,
        rules=rules or None,
        valid_categories=valid_categories,
        catch_all=catch_all,
    )

    llm_categories = [c for c in valid_categories if c != catch_all]
    llm_suggestions = _llm_fallback_suggestions(result, llm_categories)

    updated = 0
    for _, row in result.iterrows():
        label_source = row["label_source"]
        category_name = row.get("category")
        category_id = name_to_id.get(category_name)

        if label_source in ("rule", "override", "model_agreed") and category_id:
            update = {
                "category_id": category_id,
                "confidence": _clip_confidence(row.get("confidence")),
                "label_source": label_source,
                "needs_review": False,
            }
        elif label_source == "model" and category_id:
            # Suggestion: category_id doubles as suggested_category in the
            # review queue while needs_review stays True.
            update = {
                "category_id": category_id,
                "confidence": _clip_confidence(row.get("confidence")),
                "label_source": "model",
                "needs_review": True,
            }
        elif label_source == "none" and row["id"] in llm_suggestions:
            suggestion = llm_suggestions[row["id"]]
            category_id = name_to_id.get(suggestion["category"])
            if not category_id:
                continue
            update = {
                "category_id": category_id,
                "confidence": _clip_confidence(suggestion["confidence"]),
                "label_source": "llm",
                "needs_review": True,
            }
        else:
            # No rule matched and no model/LLM suggestion available — leave
            # for manual review.
            continue

        try:
            supabase_client.table("transactions").update(update).eq("id", row["id"]).eq("user_id", user_id).execute()
            updated += 1
        except Exception as e:
            logger.warning("Failed to update transaction %s: %s", row["id"], e)

    logger.info("Classified %d/%d pending transactions for user %s (model=%s)",
                updated, len(result), user_id, "yes" if bundle else "rules-only")
    return updated


def _clip_confidence(value) -> Optional[float]:
    """transactions.confidence is numeric(3,2) — clamp to [0, 1]."""
    try:
        return round(min(max(float(value), 0.0), 1.0), 2)
    except (TypeError, ValueError):
        return None
