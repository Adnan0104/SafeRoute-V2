# SafeRoute V2 — Testing Strategy

## Overview

Testing is organized into three layers. The goal is to catch real bugs early
without creating a brittle test suite that slows down a small team.

## Test Pyramid

```
         ┌──────────┐
         │   E2E    │  ← Playwright: critical user journeys only
         │  (few)   │
         ├──────────┤
         │Integration│  ← API tests with test DB, component tests
         │ (moderate)│
         ├──────────┤
         │   Unit    │  ← Pure functions, services, utilities
         │  (many)  │
         └──────────┘
```

## Backend Testing (Pytest)

### Structure
```
backend/tests/
├── conftest.py           # Shared fixtures (test DB, test client)
├── unit/
│   ├── test_safety_scoring.py
│   ├── test_schemas.py
│   └── test_utils.py
├── integration/
│   ├── test_routes_api.py
│   ├── test_reports_api.py
│   └── test_health.py
└── factories/
    └── factories.py      # Test data factories
```

### Key Practices
- **Test database**: Use a separate PostgreSQL database (or SQLite for unit
  tests where PostGIS is not needed).
- **Fixtures**: Shared fixtures in `conftest.py` for DB sessions, test client,
  authenticated headers.
- **No mocking routing APIs in integration tests**: Use recorded responses
  (VCR cassettes) or a thin mock that returns realistic data shapes.
- **Safety scoring tests**: Verify that scores are computed correctly and
  that "no data" cases return null/disclaimer — never fabricated scores.

### Running
```bash
cd backend
pytest                       # all tests
pytest tests/unit            # unit tests only
pytest -x --tb=short         # stop on first failure
pytest --cov=app             # with coverage
```

## Frontend Testing (Vitest + React Testing Library)

### Structure
```
frontend/__tests__/
├── components/
│   ├── RouteCard.test.tsx
│   ├── SearchBar.test.tsx
│   └── SafetyIndicator.test.tsx
├── hooks/
│   └── useRouteSearch.test.ts
└── lib/
    └── api-client.test.ts
```

### Key Practices
- **Component tests**: Verify rendering, user interactions, accessibility.
- **Hook tests**: Test custom hooks in isolation using `renderHook`.
- **API client tests**: Mock fetch responses, verify request shapes.
- **No snapshot tests**: They add noise without catching real bugs.

### Running
```bash
cd frontend
npm test                     # run all tests
npm run test:watch           # watch mode during development
npm run test:coverage        # with coverage report
```

## End-to-End Testing (Playwright)

### Structure
```
frontend/e2e/
├── route-search.spec.ts     # Search and view routes
├── report-submit.spec.ts    # Submit a safety report
└── auth-flow.spec.ts        # Login / logout
```

### Key Practices
- **Critical paths only**: Don't E2E test every edge case.
- **Stable selectors**: Use `data-testid` attributes, not CSS classes.
- **Test against staging**: E2E runs against a deployed staging environment.
- **Visual testing**: Optional; screenshot comparison for key pages.

### Running
```bash
cd frontend
npx playwright test          # run all e2e tests
npx playwright test --ui     # interactive mode
```

## CI Integration

- **On every PR**: Unit + integration tests (backend & frontend).
- **On merge to main**: Full test suite including E2E.
- **Coverage gate**: Aim for >70% line coverage on backend services,
  >60% on frontend components. Not enforced initially.

## What We Don't Test (MVP)

- Performance / load testing
- Security penetration testing
- Visual regression testing
- Accessibility automation (manual checks only in MVP)
