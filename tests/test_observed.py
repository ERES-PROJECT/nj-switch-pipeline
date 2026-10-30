"""Historical captured responses, not assertions about today's market rates."""
from pathlib import Path
from decimal import Decimal
import pytest

from nj_switch.pipeline import replay
from nj_switch.reporting import write_report, verify_report, slug

OBSERVED = Path(__file__).parent / "fixtures/observed"


@pytest.mark.parametrize("name,count", [
    ("constellation_electric", 2), ("constellation_jcpl_electric", 2),
    ("constellation_ace_electric", 2),
    ("direct_energy_electric", 5), ("direct_energy_jcpl_electric", 5),
    ("direct_energy_ace_electric", 5), ("direct_energy_rockland_electric", 5),
    ("direct_energy_gas", 3), ("direct_energy_njng_gas", 3),
    ("direct_energy_sjg_gas", 3), ("direct_energy_etg_gas", 3),
    ("ambit_electric", 4), ("ambit_jcpl_electric", 4),
    ("ambit_ace_electric", 4), ("ambit_rockland_electric", 4),
    ("think_energy_electric", 1), ("think_energy_jcpl_electric", 1),
    ("major_energy_electric", 4), ("major_energy_ace_electric", 4),
    ("major_energy_gas", 2), ("major_energy_njng_gas", 2),
    ("major_energy_sjg_gas", 2), ("major_energy_etg_gas", 1),
    ("xoom_energy_electric", 5), ("xoom_energy_jcpl_electric", 5),
    ("xoom_energy_rockland_electric", 5), ("xoom_energy_gas", 4),
    ("xoom_energy_njng_gas", 4), ("xoom_energy_njng_20261016", 4),
    ("xoom_energy_sjg_gas", 4),
    ("nrg_electric", 18), ("nrg_ace_electric", 18),
    ("nrg_rockland_electric", 18), ("nrg_pseg_gas", 11),
    ("nrg_sjg_gas", 11),
    ("smart_energy_jcpl_electric", 1), ("smart_energy_ace_electric", 1),
    ("smart_energy_rockland_electric", 1),
    ("clearview_jcpl_electric", 5), ("clearview_ace_electric", 5),
    ("clearview_ace_electric_20261013", 10),
    ("clearview_jcpl_electric_20261013", 12),
    ("clearview_njng_gas_20261013", 1),
    ("clearview_sjg_gas_20261013", 1),
    ("idt_energy_jcpl_electric", 6), ("idt_energy_rockland_electric", 6),
    ("residents_energy_njng_gas", 2), ("eligo_energy_njng_gas", 3),
    ("nordic_etg_gas_20261013", 1), ("nordic_njng_gas_20261013", 1),
    ("nordic_pseg_gas_20261013", 1), ("nordic_sjg_gas_20261013", 1),
    ("nordic_ace_electric_20261013", 1), ("nordic_jcpl_electric_20261013", 1),
    ("nordic_pseg_electric_20261013", 1),
    ("indra_etg_gas_20261013", 2), ("indra_njng_gas_20261013", 2),
    ("indra_pseg_gas_20261013", 2), ("indra_sjg_gas_20261013", 2),
    ("indra_ace_electric_20261013", 3),
    ("indra_jcpl_electric_20261013", 3),
    ("indra_pseg_electric_20261013", 3),
    ("indra_rockland_electric_20261013", 3),
    ("cleanchoice_pseg_electric_20261013", 3),
    ("cleanchoice_jcpl_electric_20261013", 3),
    ("cleanchoice_ace_electric_20261013", 3),
    ("american_power_gas_pseg_gas_20261013", 1),
    ("cleansky_rockland_electric_20261013", 3),
    ("cleansky_pseg_gas_07102_20261013", 5),
    ("cleansky_pseg_gas_07430_20261013", 5),
    ("cleansky_sjg_gas_20261013", 5),
    ("cleansky_etg_gas_20261013", 5),
    ("cleansky_njng_gas_20261013", 5),
])
def test_observed_regression(name, count, tmp_path):
    import json
    from nj_switch.models import Query
    fixture = OBSERVED / (name + ".json")
    query = Query.model_validate(json.loads(fixture.read_text(encoding="utf-8"))["query"])
    result = replay(fixture, tmp_path / slug(query))
    assert result.replayed
    assert len(result.offers) == count
    assert len({o.key for o in result.offers}) == count
    assert all(o.utility == query.utility and o.commodity == query.commodity for o in result.offers)
    assert all((o.price.unit == "USD/kWh") == (query.commodity == "electric") for o in result.offers)
    write_report([result], tmp_path)
    assert verify_report(tmp_path) == []
    if name == "direct_energy_electric":
        summaries = [c for c in result.contracts if c.document_kind == "contract_summary"]
        assert len(summaries) == 5
        assert all(c.status == "parsed" and len(c.sections) == 12 for c in summaries)
        assert any(c.fields["prices"][0]["value"] == "0.20690" for c in summaries)
    if name.startswith("xoom_energy"):
        if name in {"xoom_energy_electric", "xoom_energy_gas"}:
            assert result.status == "success"
        flex = next(o for o in result.offers if o.name == "SimpleFlex")
        assert flex.term_kind == "month_to_month" and flex.term_months is None
        assert flex.intro_duration_billing_cycles == 3
    if name == "ambit_electric":
        assert all(o.rate_structure == "fixed" and o.cancellation_fee == 0 for o in result.offers)
        assert {o.term_months for o in result.offers} == {12, 24}
    if name == "think_energy_electric":
        assert result.offers[0].renewable_percentage == 100
        assert "solar" in result.offers[0].renewable_source
        assert result.offers[0].price.value == Decimal("0.202")
    if name in {"think_energy_electric", "think_energy_jcpl_electric"}:
        offer = result.offers[0]
        assert len(offer.documents) == 6
        assert all(document.product_id == offer.product_id for document in offer.documents)
        assert all(document.offer_key == offer.key for document in offer.documents)
    if name in {"nrg_pseg_gas", "nrg_sjg_gas"}:
        assert all(o.price.unit == "USD/therm" and o.commodity == "gas" for o in result.offers)
        assert all(o.documents for o in result.offers)
        assert all(
            any(
                document.url ==
                "https://www.picknrg.com/en/getLegalDocument?format=pdf&docType=tos&sku=" + o.product_id
                and document.product_id == o.product_id
                and document.offer_key == o.key
                for document in o.documents
            )
            for o in result.offers
        )
    if name in {"nrg_ace_electric", "nrg_rockland_electric"}:
        assert all(o.price.unit == "USD/kWh" and o.utility == query.utility for o in result.offers)


def test_wrong_utility_cannot_promote_nrg(tmp_path):
    import json
    from nj_switch.models import Query
    from nj_switch.profiles import nrg
    data = json.loads((OBSERVED / "nrg_electric.json").read_text(encoding="utf-8"))
    query = Query.model_validate({**data["query"], "utility": "ACE Electric"})
    assert nrg([(p["body"], p["url"], "hash") for p in data["payloads"]], query) == []


def test_xoom_njng_repair_fixture_is_strictly_complete(tmp_path):
    fixture = OBSERVED / "xoom_energy_njng_20261016.json"
    result = replay(fixture, tmp_path / "xoom-njng-repair")

    assert result.status == "success"
    assert result.context_verified
    assert result.source_offer_count == len(result.offers) == 4
    assert len({offer.product_id for offer in result.offers}) == 4
    assert all(offer.utility == "NJNG Gas" and offer.commodity == "gas" for offer in result.offers)
    assert all(offer.price.unit == "USD/therm" for offer in result.offers)
    assert all(len(offer.documents) == 2 and len(offer.contract_ids) == 2 for offer in result.offers)
    assert len(result.contracts) == 9
    assert sum(contract.document_kind == "contract_summary" for contract in result.contracts) == 4
    assert result.completion_issues == []
