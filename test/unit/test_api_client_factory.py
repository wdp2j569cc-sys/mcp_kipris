import pytest

from mcp_kipris.kipris.api_client_factory import (
    ApiClientConfig,
    ApiClientFactory,
    get_api_client_factory,
    reset_factory,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _reset_global_factory():
    reset_factory()
    yield
    reset_factory()


def test_factory_caches_clients_per_type():
    factory = ApiClientFactory(ApiClientConfig(api_key="dummy"))

    first = factory.get_korean_patent_search_client()
    second = factory.get_korean_patent_search_client()

    assert first is second


def test_factory_returns_distinct_clients_per_type():
    factory = ApiClientFactory(ApiClientConfig(api_key="dummy"))

    patent_client = factory.get_korean_patent_search_client()
    trademark_client = factory.get_korean_trademark_search_client()

    assert patent_client is not trademark_client


def test_get_all_clients_covers_every_registered_tool_api():
    """Regression test: Korean and foreign clients share some key names
    (e.g. "applicant_search"), so a naive dict merge in get_all_clients()
    used to silently drop 3 Korean clients. Namespacing by country fixes it.
    """
    factory = ApiClientFactory(ApiClientConfig(api_key="dummy"))

    all_clients = factory.get_all_clients()

    assert len(all_clients) == 10 + 5  # Korean + foreign client count
    assert "korean_applicant_search" in all_clients
    assert "foreign_applicant_search" in all_clients
    assert all_clients["korean_applicant_search"] is not all_clients["foreign_applicant_search"]


def test_get_api_client_factory_returns_singleton():
    first = get_api_client_factory("dummy")
    second = get_api_client_factory("a-different-key-is-ignored-once-cached")

    assert first is second


def test_reset_factory_clears_the_singleton():
    first = get_api_client_factory("dummy")
    reset_factory()
    second = get_api_client_factory("dummy")

    assert first is not second
