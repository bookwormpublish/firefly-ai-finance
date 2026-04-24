"""
patterns.py - Spending pattern detection engine.

Detects:
- Recurring transactions (subscriptions, bills)
- Spending anomalies (unusually high amounts vs. historical average)
- Month-over-month trends per category
- Subscription creep (new recurring charges)
"""

import logging
from typing import List, Dict, Any
from collections import defaultdict
from datetime import datetime
import os

log = logging.getLogger(__name__)

RECURRING_VARIANCE = float(os.getenv("RECURRING_VARIANCE_PERCENT", "10")) / 100
ANOMALY_MULTIPLIER = 1.5  # Flag if amount is >1.5x the historical average


def _parse_amount(tx: dict) -> float:
    try:
        return float(tx["attributes"]["transactions"][0]["amount"])
    except (KeyError, ValueError):
        return 0.0


def _parse_description(tx: dict) -> str:
    try:
        return tx["attributes"]["transactions"][0].get("description", "Unknown")
    except (KeyError, TypeError):
        return "Unknown"


def _parse_date(tx: dict) -> str:
    try:
        return tx["attributes"]["transactions"][0].get("date", "")[:10]
    except (KeyError, TypeError):
        return ""


def _normalize_merchant(desc: str) -> str:
    """Normalize merchant name by removing extra characters and lowercasing."""
    # Strip common suffixes: #1234, *ONLINE, location codes
    import re
    desc = re.sub(r'\s*#\d+', '', desc)
    desc = re.sub(r'\s*\*\w+', '', desc)
    desc = re.sub(r'\s{2,}', ' ', desc)
    return desc.strip().lower()


class PatternDetector:
    async def analyze(self, transactions: List[dict]) -> Dict[str, Any]:
        """
        Run all pattern analyses on a list of Firefly transactions.
        Returns:
        - recurring_transactions: list of detected recurring charges
        - anomalies: list of transactions with unusually high amounts
        - category_trends: month-over-month spending by category
        """
        if not transactions:
            return {"recurring_transactions": [], "anomalies": [], "category_trends": {}}

        recurring = self._detect_recurring(transactions)
        anomalies = self._detect_anomalies(transactions)
        trends = self._category_trends(transactions)

        return {
            "recurring_transactions": recurring,
            "anomalies": anomalies,
            "category_trends": trends,
        }

    def _detect_recurring(self, transactions: List[dict]) -> List[dict]:
        """
        Group transactions by normalized merchant name.
        Flag as recurring if the same merchant appears 2+ times with
        amounts within RECURRING_VARIANCE of each other.
        """
        merchant_groups: Dict[str, List[float]] = defaultdict(list)

        for tx in transactions:
            merchant = _normalize_merchant(_parse_description(tx))
            amount = _parse_amount(tx)
            if amount > 0:
                merchant_groups[merchant].append(amount)

        recurring = []
        for merchant, amounts in merchant_groups.items():
            if len(amounts) < 2:
                continue
            avg = sum(amounts) / len(amounts)
            # Check if all amounts are within variance band
            within_band = all(abs(a - avg) / avg <= RECURRING_VARIANCE for a in amounts)
            if within_band:
                recurring.append({
                    "merchant": merchant,
                    "occurrences": len(amounts),
                    "avg_amount": round(avg, 2),
                    "amounts": [round(a, 2) for a in amounts],
                    "type": "subscription" if avg < 50 else "bill",
                })

        # Sort by avg_amount descending
        return sorted(recurring, key=lambda x: x["avg_amount"], reverse=True)

    def _detect_anomalies(self, transactions: List[dict]) -> List[dict]:
        """
        For each merchant, compute historical average.
        Flag any transaction where amount > ANOMALY_MULTIPLIER * avg.
        """
        merchant_history: Dict[str, List[float]] = defaultdict(list)
        tx_merchant_map = []

        for tx in transactions:
            merchant = _normalize_merchant(_parse_description(tx))
            amount = _parse_amount(tx)
            tx_merchant_map.append((tx, merchant, amount))
            merchant_history[merchant].append(amount)

        anomalies = []
        for tx, merchant, amount in tx_merchant_map:
            history = merchant_history[merchant]
            if len(history) < 2:
                continue
            avg = sum(history) / len(history)
            if avg > 0 and amount > avg * ANOMALY_MULTIPLIER and amount != avg:
                anomalies.append({
                    "merchant": merchant,
                    "amount": round(amount, 2),
                    "avg_amount": round(avg, 2),
                    "multiplier": round(amount / avg, 2),
                    "date": _parse_date(tx),
                    "category": tx["attributes"]["transactions"][0].get("category_name", "Uncategorized"),
                })

        # Deduplicate and sort by multiplier descending
        seen = set()
        unique_anomalies = []
        for a in sorted(anomalies, key=lambda x: x["multiplier"], reverse=True):
            key = (a["merchant"], a["amount"])
            if key not in seen:
                seen.add(key)
                unique_anomalies.append(a)

        return unique_anomalies[:10]  # Return top 10 anomalies

    def _category_trends(self, transactions: List[dict]) -> Dict[str, Dict[str, float]]:
        """
        Compute monthly spending totals per category.
        Returns: {"category": {"YYYY-MM": total_amount}}
        """
        trends: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

        for tx in transactions:
            t = tx["attributes"]["transactions"][0]
            category = t.get("category_name") or "Uncategorized"
            amount = float(t.get("amount", 0))
            date_str = t.get("date", "")[:7]  # YYYY-MM
            if date_str:
                trends[category][date_str] += amount

        # Convert defaultdicts to regular dicts and round values
        return {
            cat: {month: round(total, 2) for month, total in months.items()}
            for cat, months in trends.items()
        }
