from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from app.core.config import Settings


class Neo4jClient:
    def __init__(self, settings: Settings) -> None:
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:
            raise RuntimeError("Install backend requirements to use Neo4j: pip install -r backend/requirements.txt") from exc

        self._database = settings.neo4j_database
        self._driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    @contextmanager
    def session(self) -> Iterator[Any]:
        with self._driver.session(database=self._database) as session:
            yield session

    def close(self) -> None:
        self._driver.close()
