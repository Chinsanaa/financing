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

Model bundles are cached in-process per (user_id, model_run_id); a new
training run invalidates the cache via `invalidate_user_bundle`.
"""
import sys
import tempfile
import threading
from pathlib import Path
from typing import Optional

import pandas as pd

from config import supabase_client
from errors import logger

# Add src to path so we can import the ML pipeline
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from classify import classify_all, load_model_bundle, ModelBundle  # noqa: E402

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
    resp = (
        supabase_client.table("transactions")
        .select("id, timestamp, merchant, description, amount")
        .eq("user_id", user_id)
        .eq("needs_review", True)
        .eq("is_manually_labeled", False)
        .execute()
    )
    if not resp.data:
        return 0

    df = pd.DataFrame(resp.data)
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
        else:
            # No rule matched and no model available — leave for manual review.
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
