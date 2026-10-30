from decimal import Decimal
import pytest
from pydantic import ValidationError

from nj_switch.models import Query
from nj_switch.normalize import attributes, prices, rate_structure, term


@pytest.mark.parametrize("text,value,unit", [
    ("19.99 cents/kWh", "0.1999", "USD/kWh"),
    ("$0.15490 per kWh", "0.15490", "USD/kWh"),
    ("$1.20/therm", "1.20", "USD/therm"),
    ("89.95¢/therm", "0.8995", "USD/therm"),
    ("$12.01/Dth", "12.01", "USD/Dth"),
    ("$1.43/CCF", "1.43", "USD/CCF"),
])
def test_units(text, value, unit):
    result = prices(text)[0]
    assert result.value == Decimal(value)
    assert result.unit == unit


@pytest.mark.parametrize("text", ["500 kWh", "15.5 per kWh", "$100 gift card", "100% renewable"])
def test_non_prices(text):
    assert prices(text) == []


def test_missing_is_not_zero():
    values = attributes("A plan with no fee information")
    assert "monthly_fee" not in values
    assert term("no disclosed duration") == (None, None)
    assert rate_structure("Clean 12") is None


def test_fixed_initial_term_is_not_misclassified_by_variable_renewal():
    text = (
        "Your contract price is fixed for the initial term of 15 Months. "
        "After the initial term, your contract price will convert to a Variable Monthly Price."
    )
    assert rate_structure(text) == "fixed"


def test_fee_and_incentive_evidence():
    values = attributes("Monthly service fee: None\nEarly termination fee: $150\n$50 gift card after 3 months\n100% renewable wind")
    assert values["monthly_fee"] == 0
    assert values["cancellation_fee"] == 150
    assert values["renewable_percentage"] == 100
    assert values["renewable_source"] == "wind"
    assert values["incentives"] == ["$50 gift card after 3 months"]


def test_conditional_fee_stays_text():
    values = attributes("Early termination fee: $10 per remaining month")
    assert "cancellation_fee" not in values
    assert "$10" in values["fee_terms"]["cancellation_fee"]


@pytest.mark.parametrize("bad", ["7102.0", "abcde", "123456", "", "１２３４５"])
def test_invalid_zip(query, bad):
    with pytest.raises(ValidationError):
        Query.model_validate({**query.model_dump(), "zip": bad})


def test_zip_padding(query):
    assert Query.model_validate({**query.model_dump(), "zip": "7102"}).zip == "07102"


def test_monthly_fee_not_contract_term():
    assert term("Monthly fee: $4.95") == (None, None)
    assert prices("$0.77900 per THM")[0].unit == "USD/therm"
    assert "cancellation_fee" not in attributes("No cancellation fee if you move out of the territory")


def test_renewable_content_label_before_percentage():
    assert attributes("Renewable Content: 100%")["renewable_percentage"] == 100
