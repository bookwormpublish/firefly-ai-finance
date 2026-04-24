"""
categorizer.py - AI-powered transaction categorization using Claude or OpenAI.

Supports:
- Batch categorization (efficient token use)
- Confidence scoring
- Fallback to OpenAI if Anthropic is unavailable
- Natural language insight generation
"""

import os
import json
import logging
from typing import List, Optional

log = logging.getLogger(__name__)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-3-5-sonnet-20241022")
CONFIDENCE_THRESHOLD = float(os.getenv("CATEGORY_CONFIDENCE_THRESHOLD", "0.7"))

RAW_CATEGORIES = os.getenv(
    "CUSTOM_CATEGORIES",
    "Food,Groceries,Transportation,Entertainment,Subscriptions,Housing,Utilities,Healthcare,Shopping,Chess,SaaS Tools,Income,Transfer,Other",
)
CATEGORIES = [c.strip() for c in RAW_CATEGORIES.split(",")]


class CategoryResult:
    def __init__(self, transaction_id: str, description: str, amount: float,
                 category: str, confidence: float):
        self.transaction_id = transaction_id
        self.description = description
        self.amount = amount
        self.category = category
        self.confidence = confidence
        self.needs_review = confidence < CONFIDENCE_THRESHOLD

    def dict(self):
        return {
            "transaction_id": self.transaction_id,
            "description": self.description,
            "amount": self.amount,
            "category": self.category,
            "confidence": self.confidence,
            "needs_review": self.needs_review,
        }


class Categorizer:
    def __init__(self):
        self.provider = LLM_PROVIDER
        self._setup_client()

    def _setup_client(self):
        if self.provider == "anthropic":
            try:
                import anthropic
                self.client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
                log.info("Categorizer using Anthropic Claude.")
            except ImportError:
                log.warning("anthropic not installed, falling back to OpenAI.")
                self.provider = "openai"
        if self.provider == "openai":
            import openai
            self.client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            log.info("Categorizer using OpenAI.")

    def _build_batch_prompt(self, transactions: List[dict]) -> str:
        categories_str = ", ".join(CATEGORIES)
        tx_lines = []
        for i, tx in enumerate(transactions):
            t = tx["attributes"]["transactions"][0]
            desc = t.get("description", "Unknown")
            amount = float(t.get("amount", 0))
            date = t.get("date", "")[:10]
            tx_lines.append(f"{i+1}. [{date}] {desc} | ${amount:.2f}")

        tx_block = "\n".join(tx_lines)
        return f"""You are a personal finance AI. Categorize each transaction into exactly one category.

Available categories: {categories_str}

Transactions:
{tx_block}

Respond with a JSON array only. Each item must have:
- "index": the transaction number (1-based)
- "category": one of the available categories above
- "confidence": a float from 0.0 to 1.0

Example: [{"index": 1, "category": "Groceries", "confidence": 0.95}]

JSON array:"""

    async def _call_llm(self, prompt: str) -> str:
        if self.provider == "anthropic":
            response = await self.client.messages.create(
                model=LLM_MODEL,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        else:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
            )
            return response.choices[0].message.content

    async def categorize_batch(self, transactions: List[dict]) -> List[CategoryResult]:
        """Categorize a list of Firefly transactions in a single LLM call."""
        if not transactions:
            return []

        prompt = self._build_batch_prompt(transactions)
        results = []

        try:
            raw = await self._call_llm(prompt)
            # Extract JSON from response
            raw = raw.strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            parsed = json.loads(raw)

            for item in parsed:
                idx = item["index"] - 1
                if idx >= len(transactions):
                    continue
                tx = transactions[idx]
                t = tx["attributes"]["transactions"][0]
                category = item["category"] if item["category"] in CATEGORIES else "Other"
                confidence = float(item.get("confidence", 0.5))
                results.append(CategoryResult(
                    transaction_id=str(tx["id"]),
                    description=t.get("description", "Unknown"),
                    amount=float(t.get("amount", 0)),
                    category=category,
                    confidence=confidence,
                ))
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            log.error(f"Failed to parse LLM batch response: {e}")
            # Fallback: categorize individually
            for tx in transactions:
                t = tx["attributes"]["transactions"][0]
                result = await self.categorize_one(
                    t.get("description", "Unknown"),
                    float(t.get("amount", 0)),
                    str(tx["id"]),
                )
                results.append(result)

        return results

    async def categorize_one(self, description: str, amount: float, tx_id: str) -> CategoryResult:
        """Categorize a single transaction."""
        categories_str = ", ".join(CATEGORIES)
        prompt = f"""Categorize this bank transaction into exactly one category.

Categories: {categories_str}

Transaction: "{description}" | ${amount:.2f}

Respond with JSON only: {{"category": "...", "confidence": 0.0}}"""

        try:
            raw = await self._call_llm(prompt)
            raw = raw.strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
            category = data["category"] if data["category"] in CATEGORIES else "Other"
            confidence = float(data.get("confidence", 0.5))
        except Exception as e:
            log.error(f"Failed to categorize single transaction: {e}")
            category = "Other"
            confidence = 0.0

        return CategoryResult(tx_id, description, amount, category, confidence)

    async def generate_insights(self, total_spending: float, top_categories: dict,
                                anomalies: list, recurring: list, days: int) -> str:
        """Generate natural language spending insights using AI."""
        top_str = "\n".join([
            f"  - {k}: ${v:.2f} ({(v/total_spending*100):.1f}%)"
            for k, v in top_categories.items()
        ])
        anomaly_str = "\n".join([
            f"  - {a.get('merchant', 'Unknown')}: ${a.get('amount', 0):.2f} (normally ~${a.get('avg_amount', 0):.2f})"
            for a in anomalies[:5]
        ]) or "  - None detected"
        recurring_str = "\n".join([
            f"  - {r.get('merchant', 'Unknown')}: ~${r.get('avg_amount', 0):.2f}/month"
            for r in recurring[:5]
        ]) or "  - None detected"

        prompt = f"""You are a personal finance advisor. Analyze this {days}-day spending summary and provide 3-4 concise, actionable insights. Be specific, friendly, and data-driven.

Total spending: ${total_spending:.2f} over {days} days (${total_spending/days:.2f}/day average)

Top categories:
{top_str}

Spending anomalies (unusually high):
{anomaly_str}

Recurring subscriptions/bills:
{recurring_str}

Provide insights that:
1. Highlight the biggest spending area and whether it seems normal
2. Call out any anomalies worth investigating
3. Note subscription creep if applicable
4. Give one actionable saving tip based on the data

Keep it under 200 words, conversational tone."""

        try:
            return await self._call_llm(prompt)
        except Exception as e:
            log.error(f"Failed to generate insights: {e}")
            return f"Spending analysis for the past {days} days: Total ${total_spending:.2f}. Top category: {list(top_categories.keys())[0] if top_categories else 'N/A'}."
