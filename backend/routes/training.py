"""Model training: trigger retraining with labeled data.

Calls src/retrain.py::retrain_model() with user's labeled transactions
and user's categories. Model artifacts uploaded to Supabase Storage.
"""
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from pathlib import Path
from config import supabase_client
from errors import internal_error, logger
from datetime import datetime
import pandas as pd
from uuid import uuid4
import tempfile
import shutil
import traceback

router = APIRouter()

from src.retrain import retrain_model


class TrainRequest(BaseModel):
    """Trigger training on user's labeled data."""
    pass


@router.post("/retrain")
async def trigger_retrain(request: Request, background_tasks: BackgroundTasks):
    """Trigger model retraining in background.

    Reads user's labeled transactions, extracts their valid categories,
    runs retrain_model() with parameterized categories, stores model
    artifacts in user's path in Supabase Storage (future), and records
    the training run.

    Returns model_run_id for polling progress.
    """
    user_id = request.state.user_id

    try:
        # Fetch user's labeled transactions, joining categories for the
        # category *name* (retrain_model works on category names, but
        # transactions only store category_id)
        response = (
            supabase_client.table("transactions")
            .select("*, categories(name)")
            .eq("user_id", user_id)
            .eq("is_manually_labeled", True)
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=400, detail="No labeled transactions to train on")

        df_labeled = pd.DataFrame(response.data)
        df_labeled['category'] = df_labeled['categories'].apply(
            lambda c: c['name'] if c else None
        )

        # Fetch user's categories
        categories_response = supabase_client.table("categories").select("name").eq("user_id", user_id).execute()
        user_categories = [cat['name'] for cat in categories_response.data] if categories_response.data else ['Other']

        # Create model_run record
        model_run_id = str(uuid4())
        supabase_client.table("model_runs").insert({
            "id": model_run_id,
            "user_id": user_id,
            "status": "running",
            "trigger": "manual",
            "n_labeled_samples": len(df_labeled),
            "started_at": datetime.utcnow().isoformat(),
        }).execute()

        # Queue background task to train
        background_tasks.add_task(
            run_training,
            user_id,
            model_run_id,
            df_labeled,
            user_categories
        )

        return {
            "model_run_id": model_run_id,
            "status": "running",
            "message": "Training started in background"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "training/trigger_retrain")


@router.get("/{model_run_id}")
async def get_training_status(request: Request, model_run_id: str):
    """Poll training status."""
    user_id = request.state.user_id
    try:
        response = supabase_client.table("model_runs").select("*").eq("id", model_run_id).eq("user_id", user_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Training run not found")
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "training/get_training_status")


@router.get("/")
async def list_training_runs(request: Request):
    """List all training runs for the user."""
    user_id = request.state.user_id
    try:
        response = (
            supabase_client.table("model_runs")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        return {"training_runs": response.data}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "training/list_training_runs")


# --- Background Task ---

def run_training(user_id: str, model_run_id: str, df_labeled: pd.DataFrame, user_categories: list):
    """Background task: train model, upload to Supabase Storage, update status.

    Deliberately a sync `def`: FastAPI runs sync background tasks in the
    threadpool. As an `async def` this CPU-bound sklearn work ran directly
    on the event loop and froze every other request for the whole training run.

    1. Create temporary directory for model artifacts
    2. Call retrain_model() with user's categories
    3. Upload artifacts to Supabase Storage ({user_id}/models/{model_run_id}/)
    4. Update model_runs table with status=succeeded + metrics
    5. Re-classify the user's unlabeled transactions with the new model
    6. Clean up temp directory
    """
    temp_dir = None
    try:
        logger.info("[Training %s] Starting with %d samples and %d categories",
                    model_run_id, len(df_labeled), len(user_categories))

        # Create temporary directory for model artifacts
        temp_dir = tempfile.mkdtemp(prefix=f"training_{model_run_id}_")
        paths = {
            'classifier': Path(temp_dir) / 'classifier.pkl',
            'vectorizer': Path(temp_dir) / 'tfidf_vectorizer.pkl',
            'vectorizer_hybrid': Path(temp_dir) / 'tfidf_vectorizer_hybrid.pkl',
            'vectorizer_config': Path(temp_dir) / 'vectorizer_config.pkl',
            'semantic_model': Path(temp_dir) / 'semantic_classifier.pkl',
            'semantic_index': Path(temp_dir) / 'semantic_index.pkl',
            'semantic_calibrator': Path(temp_dir) / 'semantic_calibrator.pkl',
            'tfidf_calibrator': Path(temp_dir) / 'tfidf_calibrator.pkl',
            'ensemble_config': Path(temp_dir) / 'ensemble_config.json',
            'report': Path(temp_dir) / 'TRAINING_REPORT.txt',
        }

        # Call retrain_model with user's data and categories
        results = retrain_model(
            df_labeled=df_labeled,
            valid_categories=user_categories,
            paths=paths,
            use_hybrid=True
        )

        logger.info("[Training %s] Training complete. Uploading artifacts...", model_run_id)

        # Upload artifacts to Supabase Storage. First path segment MUST be
        # the user_id: the bucket's RLS policies key on foldername[1] and
        # account deletion cleans the {user_id}/ prefix.
        storage_path_prefix = f"{user_id}/models/{model_run_id}"
        uploaded_files = []

        for artifact_name, artifact_path in paths.items():
            if artifact_path.exists():
                with open(artifact_path, 'rb') as f:
                    file_content = f.read()
                remote_path = f"{storage_path_prefix}/{artifact_path.name}"
                try:
                    supabase_client.storage.from_("model_artifacts").upload(
                        remote_path,
                        file_content,
                    )
                    uploaded_files.append(artifact_path.name)
                except Exception as e:
                    logger.warning("[Training %s] Failed to upload %s: %s",
                                   model_run_id, artifact_path.name, e)

        logger.info("[Training %s] Uploaded %d artifacts", model_run_id, len(uploaded_files))

        # Mark the run succeeded, using the columns model_runs actually has.
        # (The old code wrote status='complete' — not a model_run_status enum
        # value — plus nonexistent metrics/storage_path/completed_at columns,
        # so the update always failed and every run stayed 'running' forever.)
        supabase_client.table("model_runs").update({
            "status": "succeeded",
            "cv_accuracy": round(results['accuracy'], 4),
            "f1_macro": round(results['f1_macro'], 4),
            "n_labeled_samples": results['n_samples'],
            "artifact_version": storage_path_prefix,
            "finished_at": datetime.utcnow().isoformat(),
        }).eq("id", model_run_id).execute()

        logger.info("[Training %s] Succeeded (accuracy: %.1f%%)",
                    model_run_id, results['accuracy'] * 100)

        # A fresh model exists: re-classify this user's still-unlabeled rows
        # so suggestions show up without another upload.
        try:
            from ml import invalidate_user_bundle, classify_user_transactions
            invalidate_user_bundle(user_id)
            classify_user_transactions(user_id)
        except Exception as e:
            logger.warning("[Training %s] Post-training classification failed: %s",
                           model_run_id, e)

    except Exception as e:
        logger.error("[Training %s] Failed: %s", model_run_id, e)
        traceback.print_exc()
        try:
            supabase_client.table("model_runs").update({
                "status": "failed",
                "error_message": str(e),
                "finished_at": datetime.utcnow().isoformat(),
            }).eq("id", model_run_id).execute()
        except Exception as db_err:
            logger.error("[Training %s] Also failed to update database: %s", model_run_id, db_err)

    finally:
        # Clean up temp directory
        if temp_dir and Path(temp_dir).exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
