from collections.abc import Callable
from typing import Any, TypeVar

from neo4j import Driver, GraphDatabase, ManagedTransaction

from corporate_rag.graph.interfaces import BaseGraphReader
from corporate_rag.settings import Neo4jSettings

TransactionResult = TypeVar("TransactionResult")


class Neo4jClient(BaseGraphReader):
    def __init__(
        self,
        settings: Neo4jSettings,
        *,
        database: str,
        driver_factory: Callable[..., Driver] = GraphDatabase.driver,
    ) -> None:
        self.settings = settings
        self.database = database
        self.driver_factory = driver_factory
        self.driver_instance: Driver | None = None

    def __enter__(self) -> "Neo4jClient":
        self.open()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def open(self) -> None:
        if self.driver_instance is not None:
            return

        self.driver_instance = self.driver_factory(
            self.settings.uri,
            auth=(self.settings.user, self.settings.password),
            max_connection_lifetime=self.settings.max_connection_lifetime_seconds,
            connection_acquisition_timeout=self.settings.connection_acquisition_timeout_seconds,
            connection_timeout=self.settings.connection_timeout_seconds,
            keep_alive=self.settings.keep_alive,
            notifications_min_severity=self.settings.notifications_min_severity,
        )

    @property
    def driver(self) -> Driver:
        self.open()
        if self.driver_instance is None:
            raise RuntimeError("Neo4j driver was not initialized")
        return self.driver_instance

    def close(self) -> None:
        if self.driver_instance is None:
            return

        self.driver_instance.close()
        self.driver_instance = None

    def read(self, cypher: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        def run_read(transaction: ManagedTransaction) -> list[dict[str, Any]]:
            return [dict(record) for record in transaction.run(cypher, parameters or {})]

        with self.driver.session(database=self.database) as session:
            return session.execute_read(run_read)

    def write(self, cypher: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        def run_write(transaction: ManagedTransaction) -> list[dict[str, Any]]:
            return [dict(record) for record in transaction.run(cypher, parameters or {})]

        with self.driver.session(database=self.database) as session:
            return session.execute_write(run_write)

    def write_transaction(
        self,
        transaction_function: Callable[[ManagedTransaction], TransactionResult],
    ) -> TransactionResult:
        with self.driver.session(database=self.database) as session:
            return session.execute_write(transaction_function)


def build_corporate_graph_client(settings: Neo4jSettings) -> Neo4jClient:
    return Neo4jClient(settings, database=settings.corporate_database)


def build_law_graph_client(settings: Neo4jSettings) -> Neo4jClient:
    return Neo4jClient(settings, database=settings.law_database)
