# firefly-ai-finance

> AI-powered personal finance tracker built on **Firefly III** with **Claude** categorization, spending pattern detection, and a **React** dashboard.

---

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Bank CSV  │────►│ FastAPI AI  │────►│ Firefly III  │
│  / Email   │     │   Service   │     │  (port 8080) │
└─────────────┘     └─────────────┘     └─────────────┘
                          │                   │
                          ▼                   ▼
                    ┌───────────┐     ┌──────────┐
                    │  Claude /  │     │  React   │
                    │  OpenAI    │     │Dashboard │
                    └───────────┘     └──────────┘
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Firefly III | 8080 | Core finance app (double-entry bookkeeping) |
| Data Importer | 8081 | CSV import UI |
| AI Service (FastAPI) | 8000 | Claude categorization + pattern detection |
| React Dashboard | 3000 | Insights, charts, and AI sync UI |
| PostgreSQL | 5432 | Database |

---

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/bookwormpublish/firefly-ai-finance.git
cd firefly-ai-finance
cp .env.example .env
```

Edit `.env` and fill in:
- `APP_KEY` - generate with: `head /dev/urandom | LC_ALL=C tr -dc 'A-Za-z0-9' | head -c 32`
- `DB_PASSWORD` - choose a strong password
- `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`
- `STATIC_CRON_TOKEN` - generate with same command as APP_KEY

### 2. Start all services

```bash
docker compose up -d
```

### 3. First-time Firefly setup

1. Open http://localhost:8080
2. Create your admin account
3. Go to **Options → Profile → OAuth → Personal Access Tokens**
4. Create a token and add it to `.env` as `FIREFLY_III_ACCESS_TOKEN`
5. Restart: `docker compose restart ai-service importer`

### 4. Import your bank transactions

1. Export CSV from your bank (RBC, TD, Tangerine, etc.)
2. Open http://localhost:8081 (Data Importer)
3. Upload CSV and map columns
4. Complete the import

### 5. Run AI categorization

```bash
# Option A: Use the dashboard (http://localhost:3000 → AI Sync tab)
# Option B: Call the API directly
curl -X POST http://localhost:8000/sync-categories?pages=3
```

### 6. View insights

Open **http://localhost:3000** for the full dashboard.

---

## AI Service API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/sync-categories` | POST | Categorize uncategorized transactions |
| `/insights` | GET | AI spending analysis + anomalies |
| `/categories/summary` | GET | Category breakdown (no AI) |
| `/categorize/single` | POST | Test categorize a single description |

**Interactive docs:** http://localhost:8000/docs

---

## Dashboard Features

- **Overview**: Total spending, daily average, donut chart, bar chart by category
- **AI Insights**: Claude-generated natural language analysis of your spending
- **Anomaly Detection**: Transactions flagged as unusually high vs. your history
- **Patterns**: Recurring subscriptions/bills, month-over-month trends
- **AI Sync**: Manual trigger to run categorization with confidence scores

---

## Custom Categories

Edit `CUSTOM_CATEGORIES` in `.env`:

```env
CUSTOM_CATEGORIES=Food,Groceries,Transportation,Entertainment,Subscriptions,Housing,Utilities,Healthcare,Shopping,Chess,SaaS Tools,Income,Transfer,Other
```

Add any category that fits your life (e.g., `Chess`, `Kids Activities`, `Home Reno`).

---

## Project Structure

```
firefly-ai-finance/
├── docker-compose.yml       # All services
├── .env.example             # Configuration template
├── ai-service/
│   ├── main.py               # FastAPI app + endpoints + scheduler
│   ├── categorizer.py        # Claude/OpenAI batch categorization
│   ├── patterns.py           # Recurring + anomaly detection
│   ├── requirements.txt
│   └── Dockerfile
└── dashboard/
    ├── package.json          # React + Vite + Recharts + Tailwind
    └── src/
        ├── App.tsx
        ├── components/
        │   ├── Dashboard.tsx
        │   ├── Header.tsx
        │   ├── OverviewTab.tsx   # Charts + AI insights + anomalies
        │   ├── CategoriesTab.tsx
        │   ├── PatternsTab.tsx
        │   └── SyncTab.tsx       # Manual AI sync trigger
        └── hooks/
            └── useFinanceData.ts # Data fetching hook
```

---

## Canadian Bank CSV Support

Firefly's Data Importer accepts CSV from any bank. Common column mappings:

| Bank | Date col | Amount col | Description col |
|------|----------|------------|------------------|
| RBC | `Transaction Date` | `CAD$` | `Description 1` |
| TD | `Date` | `Amount` | `Description` |
| Tangerine | `Date` | `Amount` | `Name` |
| BMO | `Transaction Date` | `Amount` | `Description` |

---

## Roadmap

- [ ] Email parser for real-time transaction ingestion (imaplib)
- [ ] Weekly AI pattern report email digest
- [ ] Budget vs. actual tracking per category
- [ ] RRSP/TFSA account tagging
- [ ] Mobile-friendly PWA dashboard
- [ ] Ollama integration for fully offline AI

---

## Tech Stack

- **Backend**: Python 3.12, FastAPI, httpx, APScheduler
- **AI**: Anthropic Claude (`claude-3-5-sonnet`) or OpenAI (`gpt-4o-mini`)
- **Finance Core**: Firefly III (PHP/Laravel)
- **Database**: PostgreSQL 16
- **Frontend**: React 18, TypeScript, Vite, Recharts, Tailwind CSS
- **Infrastructure**: Docker Compose, Nginx

---

## License

MIT
- **Frontend**: React 18, TypeScript, Vite, Recharts, Tailwind CSS
- **Infrastructure**: Docker Compose
