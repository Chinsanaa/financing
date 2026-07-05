"""Model training: trigger retraining with labeled data.

Calls src/retrain.py::retrain_model() with user's labeled transactions
and user's categories. Model artifacts uploaded to Supabase Storage.
"""
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from config import supabase_client
from datetime import datetime
import pandas as pd
from pathlib import Path
import sys
from uuid import uuid4
import tempfile
import shutil
import traceback

router = APIRouter()

# Add src to path so we can import retrain
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from retrain import retrain_model


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
        # Fetch user's labeled transactions
        response = supabase_client.table("transactions").select("*").eq("user_id", user_id).eq("labeled", True).execute()
        if not response.data:
            raise HTTPException(status_code=400, detail="No labeled transactions to train on")

        df_labeled = pd.DataFrame(response.data)

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
            "created_at": datetime.utcnow().isoformat(),
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
            "status": "queued",
            "message": "Training started in background"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{model_run_id}")
async def get_training_status(request: Request, model_run_id: str):
    """Poll training status."""
    user_id = request.state.user_id
    try:
        response = supabase_client.table("model_runs").select("*").eq("id", model_run_id).eq("user_id", user_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Training run not found")
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_training_runs(request: Request):
    """List all training runs for the user."""
    user_id = request.state.user_id
    try:
        response = supabase_client.table("model_runs").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return {"training_runs": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Background Task ---

async def run_training(user_id: str, model_run_id: str, df_labeled: pd.DataFrame, user_categories: list):
    """Background task: train model, upload to Supabase Storage, update status.

    1. Create temporary directory for model artifacts
    2. Call retrain_model() with user's categories
    3. Upload artifacts to Supabase Storage (user/{user_id}/models/{model_run_id}/)
    4. Update model_runs table with status=complete + metrics
    5. Clean up temp directory
    """
    temp_dir = None
    try:
        print(f"[Training {model_run_id}] Starting with {len(df_labeled)} samples and {len(user_categories)} categories")

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

        print(f"[Training {model_run_id}] Training complete. Uploading artifacts...")

        # Upload artifacts to Supabase Storage
        storage_path_prefix = f"models/{user_id}/{model_run_id}"
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
                        print(f"  [OK] {artifact_path.name}")
                    except Exception as e:
                        print(f"  [WARN] Failed to upload {artifact_path.name}: {e}")

        print(f"[Training {model_run_id}] Uploaded {len(uploaded_files)} artifacts")

        # Update model_runs table with status=complete
        supabase_client.table("model_runs").update({
            "status": "complete",
            "metrics": {
                "accuracy": round(results['accuracy'], 4),
                "f1_macro": round(results['f1_macro'], 4),
                "n_samples": results['n_samples'],
                "n_features": results['n_features'],
            },
            "storage_path": storage_path_prefix,
            "completed_at": datetime.utcnow().isoformat(),
        }).eq("id", model_run_id).execute()

        print(f"[Training {model_run_id}] Complete (accuracy: {results['accuracy']:.1%})")

    except Exception as e:
        print(f"[Training {model_run_id}] Failed: {e}")
        traceback.print_exc()
        try:
            supabase_client.table("model_runs").update({
                "status": "failed",
                "error": str(e),
            }).eq("id", model_run_id).execute()
        except Exception as db_err:
            print(f"[Training {model_run_id}] Also failed to update database: {db_err}")

    finally:
        # Clean up temp directory
        if temp_dir and Path(temp_dir).exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"[Training {model_run_id}] Cleaned up temp directory")
