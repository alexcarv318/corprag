from collections.abc import Callable
from typing import cast

from neo4j import Driver

from corporate_rag.graph.neo4j_client import (
    Neo4jClient,
    build_corporate_graph_client,
    build_law_graph_client,
)
from corporate_rag.settings import Neo4jSettings


class FakeDriver:
    def __init__(self) -> None:
        self.close_count = 0

    def close(self) -> None:
        self.close_count += 1


class DriverFactoryRecorder:
    def __init__(self) -> None:
        self.driver = FakeDriver()
        self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def __call__(self, *args: object, **kwargs: object) -> Driver:
        self.calls.append((args, kwargs))
        return cast(Driver, self.driver)


def test_corporate_and_law_client_builders_select_database() -> None:
    settings = Neo4jSettings(corporate_database="corporate", law_database="law")

    corporate_client = build_corporate_graph_client(settings)
    law_client = build_law_graph_client(settings)

    assert corporate_client.database == "corporate"
    assert law_client.database == "law"


def test_neo4j_client_opens_driver_lazily_with_settings() -> None:
    settings = Neo4jSettings(
        uri="bolt://graph.example.test:7687",
        user="reader",
        password="secret",
        max_connection_lifetime_seconds=111,
        connection_acquisition_timeout_seconds=22.0,
        connection_timeout_seconds=3.0,
        keep_alive=False,
        notifications_min_severity="OFF",
    )
    recorder = DriverFactoryRecorder()
    driver_factory = cast(Callable[..., Driver], recorder)
    client = Neo4jClient(settings, database="corporate", driver_factory=driver_factory)

    assert recorder.calls == []

    client.open()
    client.open()

    assert len(recorder.calls) == 1
    args, kwargs = recorder.calls[0]
    assert args == ("bolt://graph.example.test:7687",)
    assert kwargs == {
        "auth": ("reader", "secret"),
        "max_connection_lifetime": 111,
        "connection_acquisition_timeout": 22.0,
        "connection_timeout": 3.0,
        "keep_alive": False,
        "notifications_min_severity": "OFF",
    }


def test_neo4j_client_context_manager_closes_driver() -> None:
    settings = Neo4jSettings()
    recorder = DriverFactoryRecorder()
    driver_factory = cast(Callable[..., Driver], recorder)

    with Neo4jClient(settings, database="corporate", driver_factory=driver_factory):
        assert recorder.driver.close_count == 0

    assert recorder.driver.close_count == 1
