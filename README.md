# SafeRoute V2

A route-comparison application that combines real routing data with transparent, evidence-based safety information.

## Quick Start

### Prerequisites

- **Node.js** ≥ 20 (for frontend)
- **Python** ≥ 3.12 (for backend)
- **PostgreSQL** ≥ 15 with PostGIS extension
- **Git**

### External API Keys Required

| Service | Purpose | Free Tier | Sign Up |
|---------|---------|-----------|---------|
| **Mapbox** | Maps, geocoding, directions | 100K requests/mo | [mapbox.com](https://account.mapbox.com/) |
| **Clerk** | User authentication | 10K MAU | [clerk.com](https://clerk.com/) |

### Setup

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd "SafeRoute v2.0"

# 2. Copy environment variables
cp .env.example .env
# Fill in your API keys in .env

# 3. Backend setup
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Frontend setup
cd ../frontend
npm install

# 5. Database setup
# Create the PostgreSQL database and enable PostGIS
# Then run migrations:
cd ../backend
alembic upgrade head

# 6. Start development servers
# Terminal 1 — Backend:
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend:
cd frontend
npm run dev
```

### Project Structure

```
├── frontend/     → Next.js application
├── backend/      → FastAPI application
├── docs/         → Architecture & API docs
├── scripts/      → Development utilities
└── .env.example  → Environment variable template
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — System design and technology choices
- [MVP Scope](docs/MVP_SCOPE.md) — Feature scope and milestone plan
- [API Contract](docs/API_CONTRACT.md) — API endpoint specifications
- [Testing Strategy](docs/TESTING_STRATEGY.md) — Test approach and structure

## License

MIT
