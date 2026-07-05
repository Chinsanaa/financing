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

        # Labeled count (has category_id set)
        labeled = supabase_client.table("transactions").select("id", count="exact").eq("user_id", user_id).not_("category_id", "is", None).execute()
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
    """Spending breakdown by category (transactions with category_id set)."""
    user_id = request.state.user_id

    try:
        # Fetch transactions with categories joined
        response = supabase_client.table("transactions").select(
            "amount, category_id, categories(name)"
        ).eq("user_id", user_id).not_("category_id", "is", None).execute()

        if not response.data:
            return {"categories": []}

        df = pd.DataFrame(response.data)
        # Extract category name from nested object
        df['category_name'] = df['categories'].apply(lambda x: x['name'] if x else 'Unknown')

        breakdown = df.groupby('category_name')['amount'].agg(['sum', 'count']).reset_index()
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
    """Spending trends: daily spend over last N days."""
    user_id = request.state.user_id

    try:
        # Fetch transactions from last N days
        response = supabase_client.table("transactions").select(
            "timestamp, amount"
        ).eq("user_id", user_id).not_("category_id", "is", None).execute()

        if not response.data:
            return {"trends": []}

        df = pd.DataFrame(response.data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Filter to last N days
        cutoff = datetime.now() - timedelta(days=days)
        df = df[df['timestamp'] >= cutoff]

        # Group by date
        df['date'] = df['timestamp'].dt.date
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


@router.get("/budget")
async def get_budget(request: Request):
    """Budget info: limits by category, current spend vs budget."""
    user_id = request.state.user_id

    try:
        # Get budget config
        budget_resp = supabase_client.table("budget_config").select("*").eq("user_id", user_id).execute()
        budget_config = budget_resp.data[0] if budget_resp.data else None

        # Get category budgets
        cat_budget_resp = supabase_client.table("budget_category_config").select(
            "*, categories(name)"
        ).eq("user_id", user_id).execute()

        if not cat_budget_resp.data:
            return {"budget_config": budget_config, "category_budgets": []}

        df = pd.DataFrame(cat_budget_resp.data)
        df['category_name'] = df['categories'].apply(lambda x: x['name'] if x else 'Unknown')

        # Get current spending by category
        spending_resp = supabase_client.table("transactions").select(
            "amount, category_id, categories(name)"
        ).eq("user_id", user_id).not_("category_id", "is", None).execute()

        spending_df = pd.DataFrame(spending_resp.data) if spending_resp.data else pd.DataFrame()
        if not spending_df.empty:
            spending_df['category_name'] = spending_df['categories'].apply(lambda x: x['name'] if x else 'Unknown')
            spending_by_cat = spending_df.groupby('category_name')['amount'].sum().to_dict()
        else:
            spending_by_cat = {}

        # Build response with current vs budget
        category_budgets = []
        for _, row in df.iterrows():
            cat_name = row['category_name']
            category_budgets.append({
                "category": cat_name,
                "monthly_budget": float(row['monthly_budget']) if row['monthly_budget'] else 0,
                "current_spend": float(spending_by_cat.get(cat_name, 0)),
                "type": row['type'],
            })

        return {
            "budget_config": {
                "monthly_income": float(budget_config['income']) if budget_config and budget_config['income'] else 0,
                "currency": budget_config['currency'] if budget_config else "CNY",
            } if budget_config else None,
            "category_budgets": category_budgets,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/savings")
async def get_savings(request: Request):
    """Savings info: goals, current savings, anomalies."""
    user_id = request.state.user_id

    try:
        # Get budget config for savings goal
        budget_resp = supabase_client.table("budget_config").select("*").eq("user_id", user_id).execute()
        budget_config = budget_resp.data[0] if budget_resp.data else None

        # Get current monthly spend (this month only)
        now = datetime.now()
        month_start = datetime(now.year, now.month, 1)

        spending_resp = supabase_client.table("transactions").select(
            "amount"
        ).eq("user_id", user_id).gte("timestamp", month_start.isoformat()).execute()

        current_spend = sum(float(t['amount']) for t in spending_resp.data) if spending_resp.data else 0

        # Simple anomaly detection: compare to average of last 3 months
        three_months_ago = datetime(now.year if now.month >= 4 else now.year - 1,
                                     now.month - 3 if now.month >= 4 else now.month + 9, 1)

        historical_resp = supabase_client.table("transactions").select(
            "timestamp, amount"
        ).eq("user_id", user_id).gte("timestamp", three_months_ago.isoformat()).lt("timestamp", month_start.isoformat()).execute()

        historical_df = pd.DataFrame(historical_resp.data) if historical_resp.data else pd.DataFrame()
        avg_monthly = 0
        if not historical_df.empty:
            historical_df['month'] = pd.to_datetime(historical_df['timestamp']).dt.to_period('M')
            monthly_totals = historical_df.groupby('month')['amount'].sum()
            avg_monthly = float(monthly_totals.mean()) if len(monthly_totals) > 0 else 0

        savings_goal = float(budget_config['saving_goal_monthly']) if budget_config and budget_config['saving_goal_monthly'] else 0
        income = float(budget_config['income']) if budget_config and budget_config['income'] else 0

        return {
            "savings_goal_monthly": savings_goal,
            "income": income,
            "current_spend": float(current_spend),
            "projected_savings": max(0, income - current_spend),
            "average_monthly_spend": avg_monthly,
            "is_anomaly": current_spend > (avg_monthly * 1.3) if avg_monthly > 0 else False,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/action")
async def get_action(request: Request):
    """Action items: over-budget categories, spending spikes, review queue count."""
    user_id = request.state.user_id

    try:
        actions = []

        # 1. Over-budget categories
        cat_budget_resp = supabase_client.table("budget_category_config").select(
            "*, categories(name)"
        ).eq("user_id", user_id).execute()

        if cat_budget_resp.data:
            # Get current spending
            spending_resp = supabase_client.table("transactions").select(
                "amount, category_id, categories(name)"
            ).eq("user_id", user_id).not_("category_id", "is", None).execute()

            spending_df = pd.DataFrame(spending_resp.data) if spending_resp.data else pd.DataFrame()
            if not spending_df.empty:
                spending_df['category_name'] = spending_df['categories'].apply(lambda x: x['name'] if x else 'Unknown')
                spending_by_cat = spending_df.groupby('category_name')['amount'].sum().to_dict()

                for budget_row in cat_budget_resp.data:
                    cat_name = budget_row['categories']['name'] if budget_row['categories'] else 'Unknown'
                    budget = float(budget_row['monthly_budget']) if budget_row['monthly_budget'] else 0
                    spend = float(spending_by_cat.get(cat_name, 0))

                    if budget > 0 and spend > budget:
                        actions.append({
                            "type": "over_budget",
                            "category": cat_name,
                            "current": spend,
                            "limit": budget,
                            "overage": spend - budget,
                        })

        # 2. Review queue count
        review_resp = supabase_client.table("transactions").select(
            "id", count="exact"
        ).eq("user_id", user_id).eq("needs_review", True).execute()

        review_count = review_resp.count if hasattr(review_resp, 'count') else len(review_resp.data)
        if review_count > 0:
            actions.append({
                "type": "pending_review",
                "count": review_count,
                "message": f"{review_count} transactions need review",
            })

        return {"actions": actions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports")
async def get_reports(request: Request):
    """Detailed reports: transactions list, export metadata."""
    user_id = request.state.user_id

    try:
        # Get all transactions with category names, sorted by date desc
        response = supabase_client.table("transactions").select(
            "timestamp, merchant, description, amount, category_id, categories(name), label_source"
        ).eq("user_id", user_id).not_("category_id", "is", None).order("timestamp", desc=True).limit(100).execute()

        if not response.data:
            return {"transactions": [], "total_count": 0}

        transactions = []
        for txn in response.data:
            transactions.append({
                "date": txn['timestamp'],
                "merchant": txn['merchant'],
                "description": txn['description'],
                "amount": float(txn['amount']),
                "category": txn['categories']['name'] if txn['categories'] else 'Unknown',
                "label_source": txn['label_source'],
            })

        # Get total count
        count_resp = supabase_client.table("transactions").select(
            "id", count="exact"
        ).eq("user_id", user_id).not_("category_id", "is", None).execute()
        total_count = count_resp.count if hasattr(count_resp, 'count') else len(count_resp.data)

        return {
            "transactions": transactions,
            "total_count": total_count,
            "page": 1,
            "per_page": 100,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/review-queue")
async def get_review_queue(request: Request):
    """Transactions needing review: needs_review=True, sorted by confidence."""
    user_id = request.state.user_id

    try:
        response = supabase_client.table("transactions").select(
            "id, timestamp, merchant, description, amount, confidence, category_id, categories(name)"
        ).eq("user_id", user_id).eq("needs_review", True).order("confidence").limit(50).execute()

        if not response.data:
            return {"transactions": []}

        transactions = []
        for txn in response.data:
            transactions.append({
                "id": txn['id'],
                "date": txn['timestamp'],
                "merchant": txn['merchant'],
                "description": txn['description'],
                "amount": float(txn['amount']),
                "confidence": float(txn['confidence']) if txn['confidence'] else 0,
                "suggested_category": txn['categories']['name'] if txn['categories'] else None,
            })

        return {
            "transactions": transactions,
            "count": len(transactions),
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
