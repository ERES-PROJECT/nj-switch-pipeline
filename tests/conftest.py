import pytest

from nj_switch.models import Query


@pytest.fixture
def query():
    return Query(supplier="Example Energy", utility="PSE&G Electric", commodity="electric",
                 zip="07102", url="https://example.com/plans", adapter="direct_energy")

