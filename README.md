# Relationship Discovery & Network Analysis Engine

Backend-first implementation of RDNAE features from the PRD.

## Current Scope

- FastAPI backend with versioned `/api/v1` routes.
- Neo4j schema bootstrap for the PRD node and edge model.
- Redis runtime configuration.
- Deterministic synthetic seed data with 48 people, multi-community clusters, shared org/education/location evidence, common interactions, and explicit hidden-connection scenarios.
- Feature 1 endpoints for health, entity search, entity detail, and depth-1 ego graph.
- Feature 2 endpoints for friend/follower, following, friends, mutuals, and social summary analysis.
- Feature 3 endpoint for second-degree hidden connection discovery with Jaccard, Adamic-Adar, paths, and explanations.
- Feature 4 endpoint support for third-degree hidden connection discovery with Katz-style scoring and intermediate-node annotations.
- Feature 5 endpoint for shared organization detection with temporal overlap, role evidence, and organization importance scoring.
- Feature 6 endpoint for shared education detection with attendance overlap, degree/field matching, and co-attendance probability.
- Frontend integration guide in `docs/frontend-integration.md`.

## Run Locally

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Seed Neo4j after the services are healthy:

```powershell
docker compose exec backend python -m app.seed --reset
```

Preview the deterministic synthetic dataset without writing to Neo4j:

```powershell
$env:PYTHONPATH='backend'
python -m app.seed --summary
```

Or from the host after installing backend dependencies:

```powershell
python -m pip install -r backend/requirements.txt
$env:PYTHONPATH='backend'
python -m app.seed --reset
```

API docs are available at:

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Run Tests

```powershell
$env:PYTHONPATH='backend'
python -m pytest backend/tests
```
