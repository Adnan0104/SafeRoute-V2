# SafeRoute V2 — MVP Scope

## MVP (14-Day Target)

### Core Features

| # | Feature                          | Acceptance Criteria                                              |
|---|----------------------------------|------------------------------------------------------------------|
| 1 | Route search (origin/destination)| User can enter two locations, backend returns real routes         |
| 2 | Alternative route display        | At least 2–3 routes shown on map with geometry                   |
| 3 | Route comparison cards           | Duration, distance, and safety summary for each route            |
| 4 | Basic safety indicators          | Each route shows a safety level with data-coverage disclosure    |
| 5 | Community incident reporting     | Authenticated users can submit a safety report with location     |
| 6 | Report moderation (admin)        | Admin can approve/reject community reports                       |
| 7 | User authentication              | Sign up, log in, log out via Clerk                               |
| 8 | Responsive layout                | Usable on desktop and mobile viewports                           |
| 9 | API documentation                | Auto-generated OpenAPI docs at `/docs`                           |
|10 | Basic test coverage              | Critical paths covered by unit + integration tests               |
|11 | Production deployment            | Frontend on Vercel, backend on Render, database provisioned      |

### Safety Scoring — MVP Approach

- Safety score is computed from **community-reported incidents** near each
  route corridor.
- If no data exists for a corridor, the UI shows "No safety data available"
  instead of a fabricated score.
- Each score card shows:
  - Number of reports within the corridor
  - Data freshness (most recent report date)
  - Confidence level: Low / Medium / High based on report density

### Out of MVP — Explicitly Deferred

| Feature                              | Target Phase | Notes                                   |
|--------------------------------------|-------------|------------------------------------------|
| Predictive risk analysis (ML)        | Phase 2     | Requires data collection + model eval    |
| Real-time incident alerts            | Phase 2     | Needs WebSocket infrastructure           |
| Open-data crime/accident integration | Phase 2     | Depends on city-specific data sources    |
| Multi-modal routing (transit/bike)   | Phase 3     | Mapbox supports this, but scope creep    |
| Social features (saved routes, share)| Phase 3     | Nice-to-have                             |
| Offline support / PWA                | Phase 3     | Low priority                             |
| Advanced moderation (ML-assisted)    | Phase 3     | Overkill for MVP                         |
| Internationalization (i18n)          | Phase 3     | English-only for MVP                     |
| Accessibility audit (WCAG AA)        | Phase 2     | Basic a11y in MVP, formal audit later    |

## Milestone Breakdown

### Week 1 (Days 1–7)
- **M1**: Foundation (monorepo, CI, architecture) ← **current**
- **M2**: Backend scaffold (FastAPI, DB models, migrations)
- **M3**: Route search API (Mapbox integration, real routes)
- **M4**: Frontend scaffold (Next.js, map, search UI)

### Week 2 (Days 8–14)
- **M5**: Safety scoring service + safety indicators
- **M6**: Community reporting (submit + display + moderate)
- **M7**: Authentication integration (Clerk)
- **M8**: Polish, testing, deployment

## Definition of Done (per feature)

1. Acceptance criteria pass.
2. Unit/integration tests pass.
3. No TypeScript or Python type errors.
4. No exposed secrets.
5. Documented in OpenAPI (backend) or component docs (frontend).
