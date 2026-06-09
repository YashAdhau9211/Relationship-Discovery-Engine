from app.seed import (
    COMMUNITIES,
    EDUCATION_INSTITUTIONS,
    EVENTS,
    LOCATIONS,
    ORGANIZATIONS,
    PEOPLE,
    RELATIONSHIPS,
    seed_summary,
)


def known_ids() -> set[str]:
    return {
        *(person["canonical_id"] for person in PEOPLE),
        *(org["canonical_id"] for org in ORGANIZATIONS),
        *(school["institution_id"] for school in EDUCATION_INSTITUTIONS),
        *(location["location_id"] for location in LOCATIONS),
        *(event["event_id"] for event in EVENTS),
        *(community["community_id"] for community in COMMUNITIES),
    }


def test_complex_seed_is_large_enough_for_discovery_workflows() -> None:
    summary = seed_summary()
    assert summary["people"] >= 45
    assert summary["organizations"] >= 10
    assert summary["education_institutions"] >= 8
    assert summary["locations"] >= 10
    assert summary["events"] >= 10
    assert summary["communities"] >= 7
    assert summary["relationships"] >= 250


def test_complex_seed_covers_required_capability_edges() -> None:
    edge_types = {rel_type for _, rel_type, _, _ in RELATIONSHIPS}
    assert {
        "FOLLOWS",
        "FRIENDS_WITH",
        "WORKS_AT",
        "MEMBER_OF",
        "STUDIED_AT",
        "LOCATED_AT",
        "INTERACTED_WITH",
        "CO_OCCURRED_IN",
        "PREDICTED_LINK",
    }.issubset(edge_types)


def test_complex_seed_relationships_reference_existing_nodes() -> None:
    ids = known_ids()
    missing = [(source, rel_type, target) for source, rel_type, target, _ in RELATIONSHIPS if source not in ids or target not in ids]
    assert missing == []


def test_complex_seed_preserves_known_demo_scenarios() -> None:
    triples = {(source, rel_type, target) for source, rel_type, target, _ in RELATIONSHIPS}
    assert ("person:alice-chen", "FOLLOWS", "person:ben-ortiz") in triples
    assert ("person:ben-ortiz", "FOLLOWS", "person:carla-singh") in triples
    assert ("person:carla-singh", "FOLLOWS", "person:david-kim") in triples
    assert ("person:alice-chen", "STUDIED_AT", "edu:stanford") in triples
    assert ("person:david-kim", "STUDIED_AT", "edu:stanford") in triples
    assert ("person:alice-chen", "PREDICTED_LINK", "person:david-kim") in triples
