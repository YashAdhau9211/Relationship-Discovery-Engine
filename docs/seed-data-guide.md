# RDNAE Complex Seed Data Guide

The synthetic seed is designed to behave like a realistic relationship-intelligence graph rather than a toy dataset.

## Dataset Size

- 48 `Person` nodes
- 12 `Organization` nodes
- 8 `EducationInstitution` nodes
- 12 `Location` nodes
- 12 `Event` nodes
- 7 `Community` nodes
- 426 relationships

## Capability Coverage

- Friend/follower analysis: `FOLLOWS` and `FRIENDS_WITH` edges across dense local communities and cross-community bridge paths.
- Following analysis: directed `FOLLOWS` edges include asymmetric relationships and reciprocal relationships.
- Second-degree connections: dense friend/follow clusters create friends-of-friends and followers-of-followers.
- Third-degree connections: `person:alice-chen -> person:ben-ortiz -> person:carla-singh -> person:david-kim`.
- Shared organizations: `WORKS_AT` and `MEMBER_OF` edges include overlapping employment and affiliation windows.
- Shared education history: `person:alice-chen` and `person:david-kim` both connect to `edu:stanford`.
- Shared locations: physical locations plus `loc:asn-64512` model city, venue, and IP/ASN signals.
- Common interactions: `INTERACTED_WITH` and `CO_OCCURRED_IN` edges connect people through calls, events, reviews, and shared activity.

## High-Value Demo Scenarios

- Hidden education-backed link: `person:alice-chen` and `person:david-kim`.
- Logistics broker scenario: `person:farah-al-mansour`, `person:boris-volkov`, `org:atlas-logistics`, and `event:dubai-shipment-exception`.
- Payments risk scenario: `person:elena-petrova`, `person:rafael-costa`, `org:quantum-bridge-capital`, and `event:mumbai-payments-audit`.
- Telecom signal scenario: `person:hugo-martinez`, `person:uri-cohen`, `person:wei-zhang`, and `event:singapore-signal-review`.
- Common call/event scenario: `event:encrypted-call-alpha` links Alice, David, Boris, and Farah.
- Second-degree social discovery: `person:alice-chen -> person:ben-ortiz -> person:carla-singh`.
- Third-degree social discovery: `person:alice-chen -> person:ben-ortiz -> person:carla-singh -> person:david-kim`.
- Shared organization discovery: `person:farah-al-mansour -> org:atlas-logistics <- person:boris-volkov`.
- Shared education discovery: `person:alice-chen -> edu:stanford <- person:david-kim`.

## Commands

Preview without writing:

```powershell
$env:PYTHONPATH='backend'
python -m app.seed --summary
```

Reset and load into running Docker Neo4j:

```powershell
docker compose exec backend python -m app.seed --reset
```
