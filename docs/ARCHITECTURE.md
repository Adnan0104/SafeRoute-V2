# SafeRoute V2 — Technical Architecture

## 1. System Overview

SafeRoute V2 is a route-comparison application that augments real routing data
with transparent, evidence-based safety information. Users search for routes
between two points and receive alternatives ranked by a combination of travel
time, distance, and an explainable safety score.

```
┌─────────────────────────────────────────────────────────┐
│                      Client (Browser)                    │
│  Next.js · TypeScript · Tailwind CSS · Mapbox GL JS     │
└──────────────────────┬──────────────────────────────────┘
                       │  HTTPS / JSON
┌──────────────────────▼──────────────────────────────────┐
│                   API Gateway (FastAPI)                   │
│  Python 3.12 · Pydantic v2 · Uvicorn                    │
│  ┌────────┐ ┌───────────┐ ┌──────────┐ ┌─────────────┐ │
│  │ Routes │ │  Safety   │ │Community │ │    Auth     │ │
│  │ Service│ │  Scoring  │ │ Reports  │ │  (Clerk)    │ │
│  └───┬────┘ └─────┬─────┘ └────┬─────┘ └──────┬──────┘ │
│      │            │            │               │        │
│  ┌───▼────────────▼────────────▼───────────────▼──────┐ │
│  │              PostgreSQL + PostGIS                    │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
         │                    │
    ┌────▼─────┐        ┌────▼──────┐
    │ Mapbox   │        │ Open Data │
    │ Directions│       │  Sources  │
    └──────────┘        └───────────┘
```

## 2. Monorepo Layout

```
SafeRoute v2.0/
├── frontend/              # Next.js application
│   ├── src/
│   │   ├── app/           # Next.js App Router pages
│   │   ├── components/    # Reusable UI components
│   │   ├── lib/           # Client utilities, API client, types
│   │   ├── hooks/         # Custom React hooks
│   │   └── styles/        # Global styles & Tailwind config
│   ├── public/            # Static assets
│   ├── __tests__/         # Frontend unit/integration tests
│   ├── e2e/               # Playwright end-to-end tests
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── package.json
│
├── backend/               # FastAPI application
│   ├── app/
│   │   ├── api/           # Route handlers (versioned: v1/)
│   │   │   └── v1/
│   │   ├── core/          # Config, security, dependencies
│   │   ├── models/        # SQLAlchemy + Pydantic models
│   │   ├── services/      # Business logic layer
│   │   ├── schemas/       # Request/response Pydantic schemas
│   │   └── main.py        # FastAPI app entry point
│   ├── alembic/           # Database migrations
│   ├── tests/             # Pytest test suite
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── pyproject.toml
│
├── docs/                  # Architecture, API contracts, ADRs
├── scripts/               # Dev tooling, seed data, CI helpers
├── .env.example           # Environment variable template
├── .gitignore
└── README.md
```

## 3. Technology Decisions

| Layer         | Choice            | Rationale                                         |
|---------------|-------------------|---------------------------------------------------|
| Frontend      | Next.js 14+       | App Router, SSR, API routes for BFF if needed     |
| Language      | TypeScript        | Type safety across the frontend                   |
| Styling       | Tailwind CSS      | Utility-first, easy dark-mode, responsive         |
| Maps          | Mapbox GL JS      | Vector tiles, directions API, free tier available  |
| Backend       | FastAPI           | Async, auto-docs, Pydantic validation             |
| ORM           | SQLAlchemy 2.0    | Mature, async support, PostGIS via GeoAlchemy2    |
| Database      | PostgreSQL+PostGIS| Spatial queries for incident/route data           |
| Auth          | Clerk             | Managed auth, JWT verification on backend         |
| Migrations    | Alembic           | Standard SQLAlchemy migration tool                |
| Testing       | Pytest + Vitest + Playwright | Unit, integration, e2e               |
| Deployment    | Vercel + Render   | Vercel for Next.js, Render for FastAPI+Postgres   |

## 4. Data Flow — Route Search

1. User enters origin & destination in the frontend.
2. Frontend calls `POST /api/v1/routes/search` on the backend.
3. Backend calls the Mapbox Directions API to fetch candidate routes.
4. For each route geometry, the safety service queries PostGIS for
   nearby historical incidents within a configurable corridor.
5. A safety score is computed per route with full transparency:
   - Data sources used
   - Confidence level (based on data density)
   - Individual factor breakdown
6. Routes are returned with geometry, duration, distance, and safety info.
7. Frontend renders routes on the map with safety indicators.

## 5. Safety Scoring Philosophy

- **Transparency first**: Every score shows what data contributed to it.
- **Confidence disclosure**: Low-data areas display a "limited data" badge
  rather than a falsely precise score.
- **No fabrication**: If no safety data exists, the system states that
  explicitly rather than inventing a score.
- **Explainability**: Each factor (lighting, incident density, road type)
  is shown individually so users understand the recommendation.

## 6. Authentication & Authorization

- **Clerk** handles user registration, login, and session management.
- The frontend uses Clerk's React SDK for auth UI.
- The backend verifies Clerk JWTs on protected endpoints.
- Public endpoints (route search) require no authentication.
- Community reporting requires authentication.
- Moderation requires an admin role.

## 7. Database Schema (High-Level)

- `users` — synced from Clerk webhook, stores user preferences
- `routes_cache` — cached route geometries (TTL-based)
- `safety_reports` — community-submitted incident reports (PostGIS point)
- `safety_data` — aggregated safety data from open sources
- `moderation_queue` — reports pending review

## 8. Deployment Architecture

```
                    Vercel
                 ┌──────────┐
  Users ────────►│ Next.js  │
                 │ Frontend │
                 └────┬─────┘
                      │ HTTPS
                 ┌────▼─────┐
                 │  Render   │
                 │  FastAPI  │
                 │  Backend  │
                 └────┬─────┘
                      │
                 ┌────▼─────┐
                 │  Render   │
                 │ PostgreSQL│
                 │ + PostGIS │
                 └──────────┘
```

## 9. Security Considerations

- All API keys stored server-side only (never in frontend bundle).
- CORS restricted to known frontend origins.
- Rate limiting on all public endpoints.
- Input validation via Pydantic on every request.
- SQL injection prevention via parameterized queries (SQLAlchemy).
- HTTPS enforced in production.
- Clerk webhook signature verification.
