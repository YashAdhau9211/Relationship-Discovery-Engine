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

## Feature 2: Social Analysis

Use these endpoints for friend/follower and following analysis panels.

### Social Summary

```http
GET /api/v1/entities/person:alice-chen/social?limit=10
```

Use this for a compact social overview card plus top-list panels.

Example response:

```json
{
  "entity_id": "person:alice-chen",
  "follower_count": 0,
  "following_count": 1,
  "friend_count": 3,
  "mutual_count": 0,
  "follow_ratio": 0.0,
  "platform_distribution": {
    "synthetic-social": 3,
    "bridge-follow": 1
  },
  "top_followers": [],
  "top_following": [],
  "friends": []
}
```

### Followers

```http
GET /api/v1/entities/person:alice-chen/followers?limit=50
```

Shows incoming directed `FOLLOWS` relationships. Render arrows toward the profile entity.

### Following

```http
GET /api/v1/entities/person:alice-chen/following?limit=50
```

Shows outgoing directed `FOLLOWS` relationships. Render arrows away from the profile entity.

### Friends

```http
GET /api/v1/entities/person:alice-chen/friends?limit=50
```

Shows undirected `FRIENDS_WITH` relationships. Render as non-arrow mutual/social ties.

### Mutual Connections

```http
GET /api/v1/entities/person:alice-chen/mutuals?target=person:carla-singh&limit=50
```

Shows shared social neighbors between two people. Use this for "people connecting both sides" panels before Feature 3 path ranking is available.

### SocialConnection Shape

All social list endpoints return `SocialConnection` items:

```json
{
  "entity": {
    "id": "person:ben-ortiz",
    "label": "Person",
    "display_name": "Ben Ortiz",
    "properties": {}
  },
  "relationship_type": "FOLLOWS",
  "direction": "outgoing",
  "weight": 0.88,
  "platform": "bridge-follow",
  "timestamp": "2026-02-01T00:00:00Z",
  "properties": {
    "weight": 0.88,
    "platform": "bridge-follow"
  }
}
```

Frontend rendering rules:

- `direction: "incoming"`: follower edge points from result entity to current profile.
- `direction: "outgoing"`: following edge points from current profile to result entity.
- `direction: "undirected"`: render as mutual/friend/shared-neighbor tie.
- `follow_ratio: null`: show "N/A" or an empty state when the person follows nobody.
- Empty `results[]`: show a neutral empty state, not an error.

## Feature 3: Second-Degree Connections

Use this endpoint to discover people who are not directly connected to the source, but are reachable through exactly one shared social neighbor.

```http
GET /api/v1/entities/person:alice-chen/connections?degree=2&limit=50
```

Example response:

```json
{
  "entity_id": "person:alice-chen",
  "degree": 2,
  "count": 1,
  "results": [
    {
      "entity": {
        "id": "person:carla-singh",
        "label": "Person",
        "display_name": "Carla Singh",
        "properties": {}
      },
      "degree": 2,
      "score": 0.83,
      "shared_neighbor_count": 1,
      "jaccard": 0.2,
      "adamic_adar": 0.721348,
      "shared_neighbors": [
        {
          "id": "person:ben-ortiz",
          "label": "Person",
          "display_name": "Ben Ortiz",
          "properties": {}
        }
      ],
      "paths": [
        ["person:alice-chen", "person:ben-ortiz", "person:carla-singh"]
      ],
      "explanation": {
        "summary": "Alice Chen is connected to Carla Singh through Ben Ortiz.",
        "algorithms": ["bounded_bfs_depth_2", "jaccard_coefficient", "adamic_adar"],
        "evidence": [
          {
            "type": "shared_social_neighbor",
            "shared_neighbor_ids": ["person:ben-ortiz"],
            "path_count": 1
          }
        ]
      }
    }
  ]
}
```

Frontend rendering rules:

- Show `score` as the main ranking strength.
- Show `shared_neighbor_count`, `jaccard`, and `adamic_adar` in an evidence/details panel.
- Render each `paths[]` entry as source -> shared neighbor -> candidate.
- Do not show direct first-degree people as second-degree candidates; the backend already excludes them.
- Use empty `results[]` as a normal "no second-degree candidates found" state.

## Feature 4: Third-Degree Connections

Use `degree=3` to discover people exactly three social hops away. These candidates are not direct connections and are not second-degree candidates.

```http
GET /api/v1/entities/person:alice-chen/connections?degree=3&limit=50
```

Example response:

```json
{
  "entity_id": "person:alice-chen",
  "degree": 3,
  "count": 1,
  "results": [
    {
      "entity": {
        "id": "person:david-kim",
        "label": "Person",
        "display_name": "David Kim",
        "properties": {}
      },
      "degree": 3,
      "score": 0.71,
      "path_count": 1,
      "katz_score": 0.000000125,
      "paths": [
        ["person:alice-chen", "person:ben-ortiz", "person:carla-singh", "person:david-kim"]
      ],
      "intermediate_nodes": [
        {
          "id": "person:ben-ortiz",
          "label": "Person",
          "display_name": "Ben Ortiz",
          "centrality_rank": 1,
          "social_degree": 4,
          "properties": {}
        }
      ],
      "explanation": {
        "summary": "Alice Chen is connected to David Kim through Ben Ortiz and Carla Singh.",
        "algorithms": ["bounded_bfs_depth_3", "katz_beta_0.005", "path_diversity", "intermediate_social_degree_rank"],
        "evidence": []
      }
    }
  ]
}
```

Frontend rendering rules:

- Render paths as source -> first intermediate -> second intermediate -> candidate.
- Use `path_count` and `score` for ranking and emphasis.
- Show `katz_score` in technical evidence panels; it is intentionally small because beta is `0.005`.
- Show `intermediate_nodes` as the bridge people, ordered by `centrality_rank`.
- Use empty `results[]` as a normal "no third-degree candidates found" state.

## Feature 5: Shared Organizations

Use this endpoint to detect hidden links through shared employers, affiliations, vendors, NGOs, and organizations.

```http
GET /api/v1/entities/person:farah-al-mansour/shared-orgs?target=person:boris-volkov
```

Example response:

```json
{
  "source_id": "person:farah-al-mansour",
  "target_id": "person:boris-volkov",
  "count": 1,
  "organizations": [
    {
      "organization": {
        "id": "org:atlas-logistics",
        "label": "Organization",
        "display_name": "Atlas Logistics",
        "properties": {
          "pagerank_score": 0.63
        }
      },
      "source_role": "Regional Manager",
      "target_role": "External Broker",
      "source_relationship_type": "WORKS_AT",
      "target_relationship_type": "WORKS_AT",
      "source_start_date": "2021-03-01",
      "source_end_date": null,
      "target_start_date": "2022-11-01",
      "target_end_date": null,
      "overlap_months": 43,
      "concurrent": true,
      "org_importance_score": 0.63,
      "score": 0.63,
      "explanation": {
        "summary": "Farah Al Mansour and Boris Volkov share Atlas Logistics with overlapping tenure.",
        "algorithms": ["bipartite_common_neighbor", "temporal_overlap", "organization_pagerank_weight"],
        "evidence": []
      }
    }
  ]
}
```

Frontend rendering rules:

- Show each shared organization as an evidence card or table row.
- Use `source_role` and `target_role` to explain why the organization matters.
- Use `concurrent` and `overlap_months` as the main temporal signal.
- Use `score` for ranking, and `org_importance_score` as supporting evidence.
- Empty `organizations[]` is a normal "no shared organizations found" state.

## Feature 6: Shared Education

Use this endpoint to detect hidden links through shared schools, universities, training programs, and attendance windows.

```http
GET /api/v1/entities/person:alice-chen/shared-edu?target=person:david-kim
```

Example response:

```json
{
  "source_id": "person:alice-chen",
  "target_id": "person:david-kim",
  "count": 1,
  "institutions": [
    {
      "institution": {
        "id": "edu:stanford",
        "label": "EducationInstitution",
        "display_name": "Stanford University",
        "properties": {
          "country": "US"
        }
      },
      "source_degree": "MS",
      "target_degree": "MS",
      "source_field": "Computer Science",
      "target_field": "Data Science",
      "source_start_year": 2010,
      "source_end_year": 2012,
      "target_start_year": 2011,
      "target_end_year": 2013,
      "attendance_overlap_years": 1,
      "field_of_study_match": false,
      "degree_level_match": true,
      "co_attendance_probability": 0.768525,
      "score": 0.803894,
      "explanation": {
        "summary": "Both people studied at Stanford University with 1 overlapping attendance year(s).",
        "algorithms": ["education_common_neighbor", "attendance_year_overlap", "degree_field_similarity", "co_attendance_probability"],
        "evidence": []
      }
    }
  ]
}
```

Frontend rendering rules:

- Show each shared institution as an evidence card or table row.
- Use `attendance_overlap_years` as the primary education timing signal.
- Use `degree_level_match` and `field_of_study_match` as supporting similarity indicators.
- Show `co_attendance_probability` as a confidence-style metric, and `score` as the backend ranking value.
- Empty `institutions[]` is a normal "no shared education found" state.

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
