# RDNAE Infrastructure Notes

The first backend milestone uses root-level `docker-compose.yml` for local infrastructure:

- `neo4j`: graph database for PRD node and edge data.
- `redis`: cache dependency reserved for scoring/path features.
- `backend`: FastAPI service.

Later milestones should add production infrastructure here: Kafka/Flink, OpenSearch, Prometheus/Grafana, Kubernetes manifests, and deployment-specific Neo4j/Redis configuration.
