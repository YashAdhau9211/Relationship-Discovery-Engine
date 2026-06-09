from app.db.schema import NODE_CONSTRAINTS, NODE_INDEXES
from app.repositories.neo4j_entities import entity_id_expr
from app.seed import node_identity_cypher


def test_schema_statements_use_neo4j_5_text_index_syntax() -> None:
    assert NODE_CONSTRAINTS
    assert NODE_INDEXES
    for statement in NODE_INDEXES:
        assert "CREATE TEXT INDEX" in statement
        assert " ON (" in statement
        assert "ON EACH" not in statement


def test_identity_expressions_are_label_aware_for_events() -> None:
    repo_expr = entity_id_expr("n")
    seed_expr = node_identity_cypher("target")
    assert "WHEN n:Event THEN n.event_id" in repo_expr
    assert "WHEN target:Event THEN target.event_id" in seed_expr
    assert repo_expr.index("WHEN n:Location") < repo_expr.index("WHEN n:Event")
    assert "ELSE coalesce" in repo_expr
