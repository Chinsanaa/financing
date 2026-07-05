"""Dashboard endpoints: stats, trends, category breakdowns."""
from fastapi import APIRouter, HTTPException, Request
from config import supabase_client
from datetime import datetime, timedelta
import pandas as pd

router = APIRouter()


@router.get("/summary")
async def get_summary(request: Request):
    """Overall summary: total transactions, labeled%, categories, total spend."""
    user_id = request.state.user_id

    try:
        # Total transactions
        total = supabase_client.table("transactions").select("id", count="exact").eq("user_id", user_id).execute()
        total_count = total.count if hasattr(total, 'count') else len(total.data)

        # Labeled count
        labeled = supabase_client.table("transactions").select("id", count="exact").eq("user_id", user_id).eq("labeled", True).execute()
        labeled_count = labeled.count if hasattr(labeled, 'count') else len(labeled.data)

        # Total spend
        all_transactions = supabase_client.table("transactions").select("amount").eq("user_id", user_id).execute()
        df = pd.DataFrame(all_transactions.data) if all_transactions.data else pd.DataFrame()
        total_spend = float(df['amount'].sum()) if not df.empty else 0.0

        return {
            "total_transactions": total_count,
            "labeled_transactions": labeled_count,
            "labeling_percentage": round(100 * labeled_count / total_count, 1) if total_count > 0 else 0,
            "total_spend": total_spend,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-category")
async def get_by_category(request: Request):
    """Spending breakdown by category (labeled transactions only)."""
    user_id = request.state.user_id

    try:
        # Fetch labeled transactions
        response = supabase_client.table("transactions").select("category,amount").eq("user_id", user_id).eq("labeled", True).execute()
        if not response.data:
            return {"categories": []}

        df = pd.DataFrame(response.data)
        breakdown = df.groupby('category')['amount'].agg(['sum', 'count']).reset_index()
        breakdown.columns = ['category', 'total_amount', 'count']

        return {
            "categories": [
                {
                    "category": row['category'],
                    "total_amount": float(row['total_amount']),
                    "transaction_count": int(row['count']),
                }
                for _, row in breakdown.iterrows()
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends")
async def get_trends(request: Request, days: int = 30):
    """Spending trends: daily/weekly spend over last N days."""
    user_id = request.state.user_id

    try:
        # Fetch transactions from last N days
        response = supabase_client.table("transactions").select("time,amount").eq("user_id", user_id).eq("labeled", True).execute()
        if not response.data:
            return {"trends": []}

        df = pd.DataFrame(response.data)
        if 'time' not in df.columns:
            df['time'] = pd.to_datetime('now')
        else:
            df['time'] = pd.to_datetime(df['time'])

        # Filter to last N days
        cutoff = datetime.now() - timedelta(days=days)
        df = df[df['time'] >= cutoff]

        # Group by date
        df['date'] = df['time'].dt.date
        daily = df.groupby('date')['amount'].sum().reset_index()

        return {
            "trends": [
                {
                    "date": str(row['date']),
                    "total_spend": float(row['amount']),
                }
                for _, row in daily.iterrows()
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/review-queue")
async def get_review_queue(request: Request):
    """Transactions needing review: needs_review=True, sorted by confidence."""
    user_id = request.state.user_id

    try:
        response = supabase_client.table("transactions").select("*").eq("user_id", user_id).eq("needs_review", True).order("confidence").limit(50).execute()
        if not response.data:
            return {"transactions": []}

        return {
            "transactions": response.data,
            "count": len(response.data),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/onboarding-status")
async def get_onboarding_status(request: Request):
    """Check user's onboarding progress."""
    user_id = request.state.user_id

    try:
        response = supabase_client.table("profiles").select("onboarding_phase").eq("user_id", user_id).execute()
        if not response.data:
            return {"onboarding_phase": "signup"}

        return {"onboarding_phase": response.data[0]['onboarding_phase']}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/onboarding-complete")
async def complete_onboarding(request: Request):
    """Mark onboarding as complete."""
    user_id = request.state.user_id

    try:
        supabase_client.table("profiles").update({
            "onboarding_phase": "complete"
        }).eq("user_id", user_id).execute()

        return {"message": "Onboarding complete"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
