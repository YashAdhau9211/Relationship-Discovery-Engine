# RDNAE Frontend Integration Guide

This guide covers Feature 1 only: health, entity search, entity detail, and depth-1 ego graph.

## Environment

- Local API base URL: `http://localhost:8000`
- Versioned API prefix: `/api/v1`
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI schema: `http://localhost:8000/openapi.json`

Auth is not enforced in Feature 1. Build the frontend API client with this future header shape so RBAC can be enabled later without refactoring:

```http
Authorization: Bearer <jwt>
```

## Stable DTOs

Use the generated OpenAPI schema as the source of truth. The Feature 1 frontend should rely on these stable models:

- `EntitySummary`: compact entity for search results.
- `EntityDetail`: full entity profile.
- `GraphNode`: graph visualization node.
- `GraphEdge`: graph visualization edge.
- `GraphResponse`: graph-ready `nodes[]`, `edges[]`, and `statistics`.
- `ApiError`: standard error wrapper.

## Endpoints

### Health

```http
GET /api/v1/health
```

Use this for environment banners or diagnostics.

Example response:

```json
{
  "status": "ok",
  "service": "RDNAE Backend",
  "environment": "local",
  "version": "0.1.0"
}
```

### Entity Search

```http
GET /api/v1/entities/search?q=alice&limit=25
```

Use this for the main entity search box. Treat an empty `results[]` as a normal empty state, not an error.

Example response:

```json
{
  "query": "alice",
  "count": 1,
  "results": [
    {
      "id": "person:alice-chen",
      "label": "Person",
      "display_name": "Alice Chen",
      "properties": {
        "canonical_id": "person:alice-chen",
        "name": "Alice Chen"
      }
    }
  ]
}
```

### Entity Detail

```http
GET /api/v1/entities/person:alice-chen
```

Use this for the entity profile header and metadata panel.

Example response:

```json
{
  "id": "person:alice-chen",
  "label": "Person",
  "display_name": "Alice Chen",
  "aliases": ["A. Chen"],
  "source_ids": ["crm:1001", "social:alice"],
  "properties": {
    "canonical_id": "person:alice-chen",
    "name": "Alice Chen",
    "nationality": "US",
    "er_confidence": 0.99
  }
}
```

### Ego Graph

```http
GET /api/v1/entities/person:alice-chen/graph?depth=1
```

Use this for the first graph visualization. Feature 1 supports `depth=1` only.

The response is compatible with Cytoscape.js or D3. Map `nodes[].id` to the renderer node ID. Map `edges[].source` and `edges[].target` to links.

Example response:

```json
{
  "center_id": "person:alice-chen",
  "depth": 1,
  "nodes": [
    {
      "id": "person:alice-chen",
      "label": "Person",
      "display_name": "Alice Chen",
      "properties": {}
    },
    {
      "id": "person:ben-ortiz",
      "label": "Person",
      "display_name": "Ben Ortiz",
      "properties": {}
    }
  ],
  "edges": [
    {
      "id": "edge:1",
      "source": "person:alice-chen",
      "target": "person:ben-ortiz",
      "type": "FOLLOWS",
      "directed": true,
      "properties": {
        "weight": 0.8
      }
    }
  ],
  "statistics": {
    "node_count": 2,
    "edge_count": 1,
    "depth": 1
  }
}
```

## Error Handling

All backend errors use this wrapper:

```json
{
  "error": {
    "code": "entity_not_found",
    "message": "Entity 'person:missing' was not found.",
    "details": {
      "entity_id": "person:missing"
    }
  }
}
```

Recommended frontend states:

- `404 entity_not_found`: show a not-found panel with the searched ID.
- `422 validation_error`: show inline form/query validation.
- `500 internal_error`: show a retryable system error.
- Empty search results: show a neutral empty state.

## Recommended Feature 1 Screens

- Entity search page with result list grouped by `label`.
- Entity profile page using `EntityDetail`.
- Ego graph panel using `GraphResponse`.
- Developer diagnostics page linking to `/docs` and showing `/api/v1/health`.

## Deterministic Complex Seed Data

The backend seed is intentionally larger than a tiny demo. It is designed to mimic messy real-world relationship intelligence data:

- 48 people across seven overlapping communities.
- 12 organizations, including companies, NGOs, logistics firms, vendors, and holding companies.
- 8 education institutions with overlapping attendance windows.
- 12 physical and virtual locations, including an IP/ASN location.
- 12 events used for co-occurrence and common-interaction analysis.
- 426 relationships spanning follow/friend edges, org/education/location affiliation, event co-occurrence, direct interactions, and predicted hidden links.

Use these stable IDs for frontend mocks and demos after seed loading:

- `person:alice-chen`
- `person:ben-ortiz`
- `person:carla-singh`
- `person:david-kim`
- `person:farah-al-mansour`
- `person:boris-volkov`
- `person:elena-petrova`
- `person:rafael-costa`
- `person:hugo-martinez`
- `person:uri-cohen`
- `org:novus-labs`
- `org:civic-data-trust`
- `org:atlas-logistics`
- `org:quantum-bridge-capital`
- `edu:stanford`
- `edu:iit-delhi`
- `loc:san-francisco`
- `loc:asn-64512`
- `loc:dubai-freezone-warehouse`
- `event:graph-summit-2026`
- `event:encrypted-call-alpha`
- `event:dubai-shipment-exception`
- `community:graph-intelligence`
- `community:hidden-brokers`

Suggested demo narratives for frontend screens:

- Third-degree hidden path: `person:alice-chen -> person:ben-ortiz -> person:carla-singh -> person:david-kim`.
- Shared education: `person:alice-chen` and `person:david-kim` both connect to `edu:stanford`.
- Shared organization: `person:farah-al-mansour` and `person:boris-volkov` both connect to `org:atlas-logistics`.
- Shared location/IP signal: multiple bridge entities connect through `loc:asn-64512`.
- Common interaction/event signal: `event:encrypted-call-alpha` links Alice, David, Boris, and Farah without requiring direct friendship.
