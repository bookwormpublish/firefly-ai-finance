"""
Firefly AI Finance - AI Categorization & Insights Service
FastAPI backend that connects Firefly III with Claude/OpenAI for
automatic transaction categorization and spending pattern detection.
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import List, Optional
from datetime import datetime, timedelta
from collections import defaultdict

import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from categorizer import Categorizer
from patterns import PatternDetector

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ─── Config ─────────────────────────────────────────────────────────────────
FIREFLY_URL = os.getenv("FIREFLY_URL", "http://localhost:8080")
FIREFLY_TOKEN = os.getenv("FIREFLY_TOKEN", "")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "20"))

# ─── Shared HTTP client ──────────────────────────────────────────────────────
http_client: Optional[httpx.AsyncClient] = None
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client
    http_client = httpx.AsyncClient(
        base_url=FIREFLY_URL,
        headers={"Authorization": f"Bearer {FIREFLY_TOKEN}", "Accept": "application/json"},
        timeout=30.0,
    )
    # Schedule auto-categorization every hour
    scheduler.add_job(auto_categorize_job, CronTrigger(minute=0), id="auto_categorize")
    # Schedule weekly pattern report every Sunday at 8am
    scheduler.add_job(weekly_pattern_job, CronTrigger(day_of_week="sun", hour=8), id="weekly_patterns")
    scheduler.start()
    log.info("AI service started. Scheduler running.")
    yield
    await http_client.aclose()
    scheduler.shutdown()


app = FastAPI(
    title="Firefly AI Finance Service",
    description="AI-powered transaction categorization and spending insights",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

categorizer = Categorizer()
pattern_detector = PatternDetector()


# ─── Pydantic models ─────────────────────────────────────────────────────────
class CategoryResult(BaseModel):
    transaction_id: str
    description: str
    amount: float
    category: str
    confidence: float
    needs_review: bool


class SyncResponse(BaseModel):
    processed: int
    categorized: int
    flagged_for_review: int
    results: List[CategoryResult]


class InsightResponse(BaseModel):
    period_start: str
    period_end: str
    total_spending: float
    top_categories: dict
    ai_insights: str
    anomalies: List[dict]
    recurring_transactions: List[dict]


# ─── Firefly helpers ─────────────────────────────────────────────────────────
async def fetch_uncategorized(page: int = 1) -> List[dict]:
    """Fetch transactions without a category from Firefly III."""
    r = await http_client.get(
        "/api/v1/transactions",
        params={"page": page, "limit": BATCH_SIZE, "type": "withdrawal"},
    )
    r.raise_for_status()
    data = r.json()["data"]
    # Filter to only uncategorized
    return [tx for tx in data if not tx["attributes"]["transactions"][0].get("category_name")]


async def fetch_all_transactions(days: int = 90) -> List[dict]:
    """Fetch all transactions for the past N days."""
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    all_txs = []
    page = 1
    while True:
        r = await http_client.get(
            "/api/v1/transactions",
            params={"page": page, "limit": 100, "start": start_date, "type": "withdrawal"},
        )
        r.raise_for_status()
        data = r.json()
        txs = data["data"]
        if not txs:
            break
        all_txs.extend(txs)
        if page >= data["meta"]["pagination"]["total_pages"]:
            break
        page += 1
    return all_txs


async def update_transaction_category(tx_id: str, category: str) -> bool:
    """Push a category back to Firefly III."""
    try:
        r = await http_client.put(
            f"/api/v1/transactions/{tx_id}",
            json={"transactions": [{"category_name": category}]},
        )
        r.raise_for_status()
        return True
    except Exception as e:
        log.error(f"Failed to update transaction {tx_id}: {e}")
        return False


# ─── Background jobs ─────────────────────────────────────────────────────────
async def auto_categorize_job():
    """Hourly job: fetch uncategorized transactions and tag them."""
    log.info("[CRON] Running auto-categorization...")
    try:
        txs = await fetch_uncategorized()
        if not txs:
            log.info("[CRON] No uncategorized transactions found.")
            return
        results = await categorizer.categorize_batch(txs)
        for result in results:
            if not result.needs_review:
                await update_transaction_category(result.transaction_id, result.category)
        log.info(f"[CRON] Categorized {len(results)} transactions.")
    except Exception as e:
        log.error(f"[CRON] Auto-categorize failed: {e}")


async def weekly_pattern_job():
    """Weekly job: detect patterns and log findings."""
    log.info("[CRON] Running weekly pattern analysis...")
    try:
        txs = await fetch_all_transactions(days=90)
        patterns = await pattern_detector.analyze(txs)
        log.info(f"[CRON] Pattern analysis complete. Found {len(patterns.get('anomalies', []))} anomalies.")
    except Exception as e:
        log.error(f"[CRON] Pattern analysis failed: {e}")


# ─── API Endpoints ────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "service": "firefly-ai", "timestamp": datetime.now().isoformat()}


@app.post("/sync-categories", response_model=SyncResponse)
async def sync_categories(background_tasks: BackgroundTasks, pages: int = 1):
    """
    Fetch uncategorized transactions from Firefly III,
    run AI categorization, and push results back.
    """
    all_txs = []
    for page in range(1, pages + 1):
        batch = await fetch_uncategorized(page)
        all_txs.extend(batch)

    if not all_txs:
        return SyncResponse(processed=0, categorized=0, flagged_for_review=0, results=[])

    results = await categorizer.categorize_batch(all_txs)

    categorized = 0
    flagged = 0
    for result in results:
        if result.needs_review:
            flagged += 1
        else:
            background_tasks.add_task(update_transaction_category, result.transaction_id, result.category)
            categorized += 1

    return SyncResponse(
        processed=len(results),
        categorized=categorized,
        flagged_for_review=flagged,
        results=results,
    )


@app.get("/insights", response_model=InsightResponse)
async def get_insights(days: int = 30):
    """
    Fetch all transactions for the past N days and return
    AI-generated insights, top categories, and spending anomalies.
    """
    txs = await fetch_all_transactions(days=days)
    if not txs:
        raise HTTPException(status_code=404, detail="No transactions found for the given period.")

    # Aggregate spending by category
    category_totals: dict = defaultdict(float)
    for tx in txs:
        t = tx["attributes"]["transactions"][0]
        cat = t.get("category_name") or "Uncategorized"
        category_totals[cat] += float(t["amount"])

    total = sum(category_totals.values())
    top_categories = dict(sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:10])

    # AI analysis
    analysis = await pattern_detector.analyze(txs)

    # Generate natural language insights
    ai_insights = await categorizer.generate_insights(
        total_spending=total,
        top_categories=top_categories,
        anomalies=analysis.get("anomalies", []),
        recurring=analysis.get("recurring_transactions", []),
        days=days,
    )

    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")

    return InsightResponse(
        period_start=start_date,
        period_end=end_date,
        total_spending=round(total, 2),
        top_categories={k: round(v, 2) for k, v in top_categories.items()},
        ai_insights=ai_insights,
        anomalies=analysis.get("anomalies", []),
        recurring_transactions=analysis.get("recurring_transactions", []),
    )


@app.get("/categories/summary")
async def categories_summary(days: int = 30):
    """Quick category breakdown without AI analysis."""
    txs = await fetch_all_transactions(days=days)
    totals: dict = defaultdict(float)
    counts: dict = defaultdict(int)
    for tx in txs:
        t = tx["attributes"]["transactions"][0]
        cat = t.get("category_name") or "Uncategorized"
        totals[cat] += float(t["amount"])
        counts[cat] += 1
    return {
        "period_days": days,
        "categories": [
            {"name": k, "total": round(totals[k], 2), "count": counts[k]}
            for k in sorted(totals, key=totals.get, reverse=True)
        ],
    }


@app.post("/categorize/single")
async def categorize_single(description: str, amount: float):
    """Categorize a single transaction description (for testing)."""
    result = await categorizer.categorize_one(description, amount, "tx_test")
    return result
