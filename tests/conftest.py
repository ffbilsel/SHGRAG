import pytest

from shgrag.loader import load_scenarios


@pytest.fixture(scope="session")
def scenarios():
    return {s.id: s for s in load_scenarios()}


@pytest.fixture(scope="session")
def cases(scenarios):
    return {c.id: (s, c) for s in scenarios.values() for c in s.cases}
