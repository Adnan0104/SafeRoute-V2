# SafeRoute V2 — Deployment Prerequisites

## Required External Services

### 1. Mapbox (Maps & Routing)
- **What**: Provides map tiles, geocoding, and directions API
- **Sign up**: [mapbox.com](https://account.mapbox.com/)
- **Free tier**: 100,000 map loads/mo, 100,000 direction requests/mo
- **Keys needed**:
  - Public access token (`pk.xxx`) — used in frontend for map rendering
  - Secret access token (`sk.xxx`) — used in backend for Directions API
- **Setup steps**:
  1. Create a Mapbox account
  2. Go to Access Tokens page
  3. Copy the default public token
  4. Create a new secret token with `directions:read` scope

### 2. Clerk (Authentication)
- **What**: Managed authentication (sign up, login, session management)
- **Sign up**: [clerk.com](https://clerk.com/)
- **Free tier**: 10,000 monthly active users
- **Keys needed**:
  - Publishable key (`pk_test_xxx`) — used in frontend
  - Secret key (`sk_test_xxx`) — used in backend for JWT verification
  - Webhook signing secret (`whsec_xxx`) — for user sync webhooks
- **Setup steps**:
  1. Create a Clerk application
  2. Copy publishable and secret keys from the dashboard
  3. Configure webhook endpoint: `https://your-api.com/api/v1/webhooks/clerk`
  4. Copy the webhook signing secret

### 3. PostgreSQL + PostGIS (Database)
- **Local development**: Install PostgreSQL 15+ and enable PostGIS extension
- **Production**: Use Render's managed PostgreSQL (free tier: 1GB, 90-day expiry)
- **Setup steps**:
  1. Create database: `createdb saferoute_dev`
  2. Enable PostGIS: `CREATE EXTENSION postgis;`
  3. Create test database: `createdb saferoute_test`

### 4. Vercel (Frontend Hosting)
- **What**: Hosts the Next.js frontend
- **Sign up**: [vercel.com](https://vercel.com/)
- **Free tier**: Hobby plan (sufficient for MVP)
- **Setup steps**:
  1. Connect GitHub repository
  2. Set root directory to `frontend/`
  3. Add environment variables in Vercel dashboard:
     - `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
     - `NEXT_PUBLIC_MAPBOX_TOKEN`
     - `NEXT_PUBLIC_API_URL`

### 5. Render (Backend Hosting)
- **What**: Hosts FastAPI backend and PostgreSQL database
- **Sign up**: [render.com](https://render.com/)
- **Free tier**: Web service (spins down after inactivity), PostgreSQL (90-day)
- **Setup steps**:
  1. Create a new Web Service, connect GitHub repo
  2. Set root directory to `backend/`
  3. Build command: `pip install -r requirements.txt`
  4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
  5. Add environment variables in Render dashboard

## Environment Variable Checklist

| Variable | Where | Required For |
|----------|-------|-------------|
| `DATABASE_URL` | Backend (Render) | Database connection |
| `MAPBOX_ACCESS_TOKEN` | Backend | Route directions |
| `MAPBOX_SECRET_TOKEN` | Backend | Server-side map API |
| `NEXT_PUBLIC_MAPBOX_TOKEN` | Frontend (Vercel) | Map rendering |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Frontend (Vercel) | Auth UI |
| `CLERK_SECRET_KEY` | Backend (Render) | JWT verification |
| `CLERK_WEBHOOK_SECRET` | Backend (Render) | Webhook validation |
| `NEXT_PUBLIC_API_URL` | Frontend (Vercel) | API calls |
| `CORS_ORIGINS` | Backend (Render) | CORS whitelist |
| `SECRET_KEY` | Backend (Render) | Session security |

## Pre-Deployment Checklist

- [ ] All API keys obtained and tested locally
- [ ] Database created and migrations applied
- [ ] Health check endpoint responds correctly
- [ ] Frontend builds without errors (`npm run build`)
- [ ] Backend runs without errors (`uvicorn app.main:app`)
- [ ] CORS configured for production frontend URL
- [ ] Environment variables set in hosting providers
- [ ] `.env` file is NOT committed to Git
