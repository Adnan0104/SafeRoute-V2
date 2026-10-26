# SafeRoute V2 — API Contract

Base URL: `https://api.saferoute.app/api/v1`

All responses follow a consistent envelope:

```json
{
  "status": "ok" | "error",
  "data": { ... },
  "error": { "code": "...", "message": "..." }  // only on error
}
```

---

## 1. Route Search

### `POST /routes/search`

Search for routes between two points with safety information.

**Auth**: None (public endpoint)

**Request Body**:
```json
{
  "origin": {
    "lat": 40.7128,
    "lng": -74.0060
  },
  "destination": {
    "lat": 40.7580,
    "lng": -73.9855
  },
  "mode": "driving",           // "driving" | "walking" | "cycling"
  "alternatives": true,        // request alternative routes
  "safety_corridor_m": 200     // optional, default 200m corridor for safety data
}
```

**Response** `200 OK`:
```json
{
  "status": "ok",
  "data": {
    "routes": [
      {
        "id": "route_abc123",
        "geometry": {
          "type": "LineString",
          "coordinates": [[lng, lat], ...]
        },
        "duration_seconds": 1845,
        "distance_meters": 8200,
        "summary": "via Broadway and 7th Ave",
        "safety": {
          "score": 72,                    // 0-100 or null if no data
          "confidence": "medium",         // "low" | "medium" | "high" | "none"
          "data_coverage": {
            "reports_in_corridor": 14,
            "corridor_width_m": 200,
            "most_recent_report": "2026-10-20T14:30:00Z",
            "oldest_report": "2026-06-15T09:00:00Z"
          },
          "factors": [
            {
              "name": "incident_density",
              "label": "Reported Incidents",
              "value": 14,
              "unit": "reports per km",
              "impact": "negative",       // "positive" | "negative" | "neutral"
              "description": "14 community reports within 200m of this route"
            }
          ],
          "disclaimer": "Safety information is based on community reports and may not reflect current conditions."
        },
        "trade_offs": {
          "vs_fastest": {
            "extra_duration_seconds": 0,
            "extra_distance_meters": 0
          },
          "vs_safest": {
            "extra_duration_seconds": 120,
            "extra_distance_meters": 400
          }
        }
      }
    ],
    "metadata": {
      "origin_address": "New York, NY",
      "destination_address": "Times Square, NY",
      "routing_provider": "mapbox",
      "computed_at": "2026-10-26T15:30:00Z"
    }
  }
}
```

**Error Responses**:

| Status | Code                    | Description                        |
|--------|-------------------------|------------------------------------|
| 400    | `invalid_coordinates`   | Lat/lng out of valid range         |
| 400    | `invalid_mode`          | Unsupported travel mode            |
| 422    | `validation_error`      | Pydantic validation failure        |
| 502    | `routing_provider_error`| Mapbox API returned an error       |
| 429    | `rate_limited`          | Too many requests                  |

---

## 2. Safety Reports

### `POST /reports`

Submit a community safety report.

**Auth**: Required (Clerk JWT)

**Request Body**:
```json
{
  "location": {
    "lat": 40.7300,
    "lng": -74.0000
  },
  "category": "poor_lighting",   // enum: see below
  "severity": "moderate",        // "low" | "moderate" | "high"
  "description": "Unlit alley between Main St and 2nd Ave",
  "occurred_at": "2026-10-25T22:30:00Z"   // optional
}
```

**Report Categories** (enum):
- `poor_lighting`
- `traffic_hazard`
- `pedestrian_safety`
- `crime_incident`
- `road_condition`
- `construction`
- `flooding`
- `other`

**Response** `201 Created`:
```json
{
  "status": "ok",
  "data": {
    "report_id": "rpt_xyz789",
    "status": "pending_review",
    "created_at": "2026-10-26T15:35:00Z"
  }
}
```

### `GET /reports`

Retrieve approved safety reports within a bounding box.

**Auth**: None (public)

**Query Parameters**:
- `bbox` (required): `min_lng,min_lat,max_lng,max_lat`
- `category` (optional): filter by category
- `since` (optional): ISO 8601 datetime, only reports after this date
- `limit` (optional): max results, default 100, max 500

**Response** `200 OK`:
```json
{
  "status": "ok",
  "data": {
    "reports": [
      {
        "id": "rpt_xyz789",
        "location": { "lat": 40.73, "lng": -74.00 },
        "category": "poor_lighting",
        "severity": "moderate",
        "description": "Unlit alley...",
        "occurred_at": "2026-10-25T22:30:00Z",
        "created_at": "2026-10-26T15:35:00Z"
      }
    ],
    "total": 1,
    "limit": 100
  }
}
```

---

## 3. Report Moderation

### `PATCH /admin/reports/{report_id}`

**Auth**: Required (admin role)

**Request Body**:
```json
{
  "status": "approved",           // "approved" | "rejected"
  "moderation_note": "Verified"   // optional
}
```

**Response** `200 OK`:
```json
{
  "status": "ok",
  "data": {
    "report_id": "rpt_xyz789",
    "status": "approved",
    "moderated_at": "2026-10-26T16:00:00Z"
  }
}
```

---

## 4. Health Check

### `GET /health`

**Auth**: None

**Response** `200 OK`:
```json
{
  "status": "ok",
  "data": {
    "version": "0.1.0",
    "database": "connected",
    "routing_provider": "configured"
  }
}
```
