from nj_switch.offers import parse_html, parse_json
from nj_switch.profiles import indra_energy


def test_same_price_is_not_identity(query):
    html = ''.join(f'<div class="product-card plan__wrapper" data-product-id="{i}"><h2>Plan {i}</h2><p>20¢/kWh</p><p>{i} months Fixed</p></div>' for i in [12, 24])
    offers = parse_html(html, query, query.url, "a")
    assert len(offers) == 2
    assert {o.term_months for o in offers} == {12, 24}


def test_whole_page_not_an_offer(query):
    assert parse_html('<h1>Compare energy</h1><p>Example 20 cents/kWh for 12 months</p>', query, query.url, "a") == []


def test_wrong_commodity(query):
    assert parse_html('<div class="product-card plan__wrapper"><h2>Gas</h2>$1.20/therm</div>', query, query.url, "a") == []


def test_constellation_ids_and_documents(query):
    query.adapter = "constellation"
    html = '<div data-planid="123" data-term="12"><h4>12 Month Power Plan</h4>Rate per kWh: 20.99¢<a href="/contract.pdf">Terms and Conditions</a></div>'
    offer = parse_html(html, query, query.url, "a")[0]
    assert offer.product_id == "123"
    assert offer.documents[0].offer_key == offer.key
    assert offer.documents[0].url == "https://example.com/contract.pdf"
    assert offer.rate_structure is None


def test_constellation_current_zip_route_card(query):
    from decimal import Decimal

    query.adapter = "constellation"
    html = '''
    <div id="individual-electricity-options"><ul><li>
      <div class="name-above-plan">15 Month Electricity Plan</div>
      <div class="individual-cost">23.49¢ per kWh</div>
      <div>15 Month Term</div>
      <button data-selected-plan="15115">Select Plan</button>
      <a href="/bin/residential/GetPlanContractPDF?planId=15115">Contract</a>
    </li></ul></div>
    <div id="individual-gas-options"><ul><li>
      <div class="name-above-plan">24 Month Natural Gas Plan</div>
      <div class="individual-cost">92.9¢ per Therm</div>
      <div>24 Month Term</div>
      <button data-selected-plan="4674">Select Plan</button>
    </li></ul></div>
    '''
    offer = parse_html(html, query, query.url, "a")[0]
    assert offer.name == "15 Month Electricity Plan"
    assert offer.product_id == "15115"
    assert offer.price.value == Decimal("0.2349")
    assert offer.term_months == 15
    assert offer.documents[0].url.endswith("GetPlanContractPDF?planId=15115")


def test_constellation_card_ignores_estimate_and_price_to_compare(query):
    from decimal import Decimal

    query.adapter = "constellation"
    html = '''
    <div id="individual-electricity-options"><ul><li>
      <div class="name-above-plan">15 Month Electricity Plan</div>
      <div class="individual-cost">23.49¢ per kWh</div>
      <div>Estimated Monthly Cost: $234.90</div>
      <div>Price to Compare is 19.7926 cents per kWh</div>
      <div>15 Month Term</div>
      <button data-selected-plan="15115">Select Plan</button>
    </li></ul></div>
    '''
    offer = parse_html(html, query, query.url, "a")[0]
    assert offer.price.value == Decimal("0.2349")
    assert "Multiple prices in offer; review price stages/tiers against raw text" not in offer.warnings


def test_constellation_keeps_card_special_offer_over_unrelated_dialog_discount(query):
    query.adapter = "constellation"
    html = '''
    <div id="individual-gas-options"><ul><li>
      <div class="name-above-plan">12 Month Natural Gas Plan</div>
      <div class="individual-cost">83.9¢ per Therm</div>
      <div>Special Offer:\n90-Day Risk Free Guarantee</div>
      <div>12 Month Term</div>
      <button data-selected-plan="6366">Select Plan</button>
    </li></ul></div>
    <div id="dialog6366">Cost to fund the Senior Citizen Discount program</div>
    '''
    query.commodity = "gas"
    offer = parse_html(html, query, query.url, "artifact")[0]
    assert offer.incentives == ["90-Day Risk Free Guarantee"]


def test_think_card_scoping(query):
    query.adapter = "think_energy"
    html = '<div><div font-size="1.8rem">Think Clean 12</div><div font-size="4.5rem">19.90</div>¢/kWh 12 months Fixed 100% renewable</div>'
    result = parse_html(html, query, query.url, "a")
    assert len(result) == 1
    assert result[0].renewable_percentage == 100


def test_xoom_renewable_not_rate_structure(query):
    query.adapter = "xoom_energy"
    html = '<div class="myRateData"><div class="utility-choice-title">SimpleClean 12</div><div class="utility-choice-price">$0.1989/kWh</div><div class="utility-choice-rate">12 months</div><img alt="Renewable Electric"></div>'
    offer = parse_html(html, query, query.url, "a")[0]
    assert offer.rate_structure is None
    assert offer.renewable_claim


def test_ambit_unknown_term(query):
    query.adapter = "ambit"
    offer = parse_html('<div class="ngdialog-content"><h5>Ambit Plan</h5>25.99 cents/kWh</div>', query, query.url, "a")[0]
    assert offer.term_months is None
    assert offer.rate_structure is None


def test_json_unknown_unit_rejected(query):
    assert parse_json({"planName": "Plan", "rate": 19.9}, query, query.url, "a") == []


def test_generic_candidate_requires_explicit_currency(query):
    result = parse_json({"planName": "Plan", "rate": "$0.199/kWh", "termMonths": 12}, query, query.url, "a")
    assert result[0].source_kind == "json_candidate"


def test_json_cents_never_treated_as_dollars(query):
    from decimal import Decimal
    offer = parse_json({"planName": "Plan", "rate": "20", "unit": "kWh", "currency": "cents"}, query, query.url, "a")[0]
    assert offer.price.value == Decimal("0.2")
    assert parse_json({"planName": "Plan", "rate": "20", "unit": "kWh", "currency": "GBP"}, query, query.url, "a") == []


def test_indra_profile_scopes_utility_and_converts_display_cents(query):
    from decimal import Decimal

    query.supplier = "Indra Energy"
    query.utility = "ETG Gas"
    query.commodity = "gas"
    query.zip = "07201"
    query.adapter = "indra_energy"
    url = "https://indraenergy.com/wp-json/indra-energy/v1/rates?zip=07201"
    shared = {
        "state": "NJ", "zipCode": "07201", "commodityType": "G",
        "rateUnit": "therm", "termType": "Fixed", "termLength": 12,
        "enrollmentFee": 0, "cancellationFee": 0,
    }
    payload = {"success": True, "data": {"rates": {"electric": [], "gas": [
        {**shared, "utilityName": "E-Town - Elizabethtown Gas", "initialRate": 144.99,
         "rateCode": "ETOWN-12", "planName": "Renewable Secure Rate 12"},
        {**shared, "utilityName": "PSEG - Public Service Electric and Gas", "initialRate": 154.99,
         "rateCode": "PSEG-12", "planName": "Wrong Utility"},
    ]}}}
    offers = indra_energy([(payload, url, "artifact")], query)
    assert len(offers) == 1
    assert offers[0].product_id == "ETOWN-12"
    assert offers[0].price.value == Decimal("1.4499")
    assert offers[0].price.unit == "USD/therm"
    assert offers[0].rate_structure == "fixed"


def test_indra_profile_combines_reused_rate_code_with_unique_system_id(query):
    query.supplier = "Indra Energy"
    query.utility = "NJNG Gas"
    query.commodity = "gas"
    query.zip = "07712"
    query.adapter = "indra_energy"
    url = "https://indraenergy.com/wp-json/indra-energy/v1/rates?zip=07712"
    shared = {
        "state": "NJ", "zipCode": "07712", "commodityType": "G",
        "utilityName": "NJNG - New Jersey Natural Gas", "rateUnit": "therm",
        "initialRate": 134.99, "termType": "Fixed", "rateCode": "NJNG-FIXED",
        "enrollmentFee": 0, "cancellationFee": 0,
    }
    payload = {"success": True, "data": {"rates": {"electric": [], "gas": [
        {**shared, "id": 72756, "sysId": 72756, "termLength": 12,
         "planName": "Renewable Secure Rate 12"},
        {**shared, "id": 72757, "sysId": 72757, "termLength": 6,
         "planName": "Renewable Secure Rate 6"},
    ]}}}

    offers = indra_energy([(payload, url, "artifact")], query)

    assert {offer.product_id for offer in offers} == {
        "NJNG-FIXED|72756", "NJNG-FIXED|72757",
    }


def test_indra_profile_rejects_wrong_zip_or_commodity(query):
    query.supplier = "Indra Energy"
    query.utility = "PSE&G Gas"
    query.commodity = "gas"
    query.zip = "07102"
    query.adapter = "indra_energy"
    product = {
        "state": "NJ", "zipCode": "07102", "commodityType": "E",
        "utilityName": "PSEG", "rateUnit": "kWh", "initialRate": 18.99,
        "termType": "Variable", "termLength": 2, "rateCode": "PSEG-E",
        "planName": "Electric Plan",
    }
    payload = {"success": True, "data": {"rates": {"electric": [product], "gas": []}}}
    assert indra_energy([(
        payload,
        "https://indraenergy.com/wp-json/indra-energy/v1/rates?zip=07102",
        "artifact",
    )], query) == []


def test_indra_electric_profile_scopes_rockland_and_converts_cents(query):
    from decimal import Decimal

    query.supplier = "Indra Energy"
    query.utility = "Rockland Electric"
    query.commodity = "electric"
    query.zip = "07430"
    query.adapter = "indra_energy"
    url = "https://indraenergy.com/wp-json/indra-energy/v1/rates?zip=07430"
    product = {
        "state": "NJ", "zipCode": "07430", "commodityType": "E",
        "utilityName": "RECO - Rockland Electric", "rateUnit": "kWh",
        "initialRate": 15.49, "termType": "Variable", "termLength": 2,
        "rateCode": "ROCKLAND-FREEDOM", "planName": "Renewable Freedom Plan",
        "enrollmentFee": 0, "cancellationFee": 0,
    }
    payload = {"success": True, "data": {"rates": {"electric": [product], "gas": []}}}
    offers = indra_energy([(payload, url, "artifact")], query)
    assert len(offers) == 1
    assert offers[0].price.value == Decimal("0.1549")
    assert offers[0].price.unit == "USD/kWh"
    assert offers[0].rate_structure == "variable"


def test_clearview_gas_is_scoped_by_commodity_and_utility(query):
    from decimal import Decimal

    query.supplier = "Clearview Energy"
    query.utility = "NJNG Gas"
    query.commodity = "gas"
    query.adapter = "clearview_energy"
    html = """
    <label class="pricing-label"><h3>NJNG Fixed 12</h3>
      <input class="price-card__input" data-type="G" data-utilname="NJNG" id="gas-12">
      <div class="price-card__head-price">74.9</div><p>12 months Fixed</p>
    </label>
    <label class="pricing-label"><h3>JCPL Electric</h3>
      <input class="price-card__input" data-type="E" data-utilname="JCPL" id="electric-12">
      <div class="price-card__head-price">19.9</div><p>12 months Fixed</p>
    </label>
    """
    offers = parse_html(html, query, query.url, "a")
    assert len(offers) == 1
    assert offers[0].product_id == "gas-12"
    assert offers[0].price.value == Decimal("0.749")
    assert offers[0].price.unit == "USD/therm"


def test_clearview_ornj_is_scoped_to_rockland_electric(query):
    from decimal import Decimal

    query.supplier = "Clearview Energy"
    query.utility = "Rockland Electric"
    query.commodity = "electric"
    query.adapter = "clearview_energy"
    html = """
    <label class="pricing-label"><h3>Rockland Fixed 12</h3>
      <input class="price-card__input" data-type="E" data-utilname="ORNJ" id="ornj-electric-12">
      <div class="price-card__head-price">18.75</div><p>12 months Fixed</p>
    </label>
    <label class="pricing-label"><h3>NJNG Gas</h3>
      <input class="price-card__input" data-type="G" data-utilname="NJNG" id="njng-gas-12">
      <div class="price-card__head-price">72.5</div><p>12 months Fixed</p>
    </label>
    """
    offers = parse_html(html, query, query.url, "artifact")
    assert len(offers) == 1
    assert offers[0].product_id == "ornj-electric-12"
    assert offers[0].price.value == Decimal("0.1875")
    assert offers[0].price.unit == "USD/kWh"


def test_idt_gas_uses_gas_offer_code_and_therm(query):
    query.supplier = "IDT Energy"
    query.utility = "NJNG Gas"
    query.commodity = "gas"
    query.adapter = "idt_energy"
    html = """
    <table class="rate-table"><tbody><tr><td>Gas offer</td><td>
      <a href="/enroll?filter_utility=NJNG&filter_commodity=G&filter_offerid=G12&filter_rate=0.799&filter_ratetype=Fixed&filter_energytype=Standard">Enroll</a>
    </td></tr><tr class="more-info"><td>12 months Fixed</td></tr></tbody></table>
    """
    offers = parse_html(html, query, query.url, "a")
    assert len(offers) == 1
    assert offers[0].product_id == "G12"
    assert offers[0].price.unit == "USD/therm"
    assert offers[0].rate_structure == "fixed"
    assert offers[0].warnings == []


def test_idt_price_to_compare_is_not_an_offer_tier(query):
    from decimal import Decimal

    query.supplier = "IDT Energy"
    query.utility = "SJG Gas"
    query.commodity = "gas"
    query.adapter = "idt_energy"
    html = """
    <table class="rate-table"><tbody>
      <tr><td>SJG variable offer $0.53100/Therm</td><td>
        <a href="/enroll?filter_utility=SJG&filter_commodity=G&filter_offerid=SJGV&filter_rate=0.53100&filter_ratetype=Variable&filter_energytype=Standard">Enroll</a>
      </td></tr>
      <tr class="more-info"><td>Month-to-month Variable. Compare to Utility Rate $0.55095/Therm.</td></tr>
    </tbody></table>
    """
    offer = parse_html(html, query, query.url, "artifact")[0]
    assert offer.price.value == Decimal("0.53100")
    assert offer.rate_structure == "variable"
    assert not any("Multiple prices" in warning for warning in offer.warnings)


def test_idt_sjg_gas_filters_the_confirmed_utility(query):
    query.supplier = "IDT Energy"
    query.utility = "SJG Gas"
    query.commodity = "gas"
    query.adapter = "idt_energy"
    html = """
    <table class="rate-table"><tbody>
      <tr><td>SJG offer</td><td><a href="/enroll?filter_utility=SJG&filter_commodity=G&filter_offerid=SJG12&filter_rate=0.749&filter_ratetype=Fixed&filter_energytype=Standard">Enroll</a></td></tr>
      <tr class="more-info"><td>12 months Fixed</td></tr>
      <tr><td>NJNG offer</td><td><a href="/enroll?filter_utility=NJNG&filter_commodity=G&filter_offerid=NJNG12&filter_rate=0.699&filter_ratetype=Fixed&filter_energytype=Standard">Enroll</a></td></tr>
      <tr class="more-info"><td>12 months Fixed</td></tr>
    </tbody></table>
    """
    offers = parse_html(html, query, query.url, "artifact")
    assert len(offers) == 1
    assert offers[0].product_id == "SJG12"
    assert offers[0].price.unit == "USD/therm"


def test_residents_current_gas_table_filters_utility(query):
    from decimal import Decimal

    query.supplier = "Residents Energy"
    query.utility = "NJNG Gas"
    query.commodity = "gas"
    query.adapter = "residents_energy"
    html = """
    <table><tbody>
      <tr><td>PSEG</td><td>0.18</td><td>0.20</td><td>Brown</td><td>8</td></tr>
      <tr><td colspan="5">NJ Natural Gas ResiSURE Price Comparison</td></tr>
      <tr><td>Utility</td><td>PTC</td><td>IDT Energy Rate</td><td>Supply</td><td>Term (Bill Cycles)</td></tr>
      <tr><td>NJNG</td><td>0.45</td><td>1.04780</td><td>Brown</td><td>8</td></tr>
      <tr><td>SJG</td><td>0.58</td><td>1.04100</td><td>Brown</td><td>8</td></tr>
      <tr><td>NJNG</td><td>0.45</td><td>1.23780</td><td>Green</td><td>8</td></tr>
    </tbody></table>
    """
    offers = parse_html(html, query, query.url, "a")
    assert len(offers) == 2
    assert {offer.price.value for offer in offers} == {Decimal("1.04780"), Decimal("1.23780")}
    assert {offer.term_months for offer in offers} == {8}


def test_eligo_utility_rate_cards(query):
    from decimal import Decimal

    query.supplier = "Eligo Energy"
    query.utility = "NJNG Gas"
    query.commodity = "gas"
    query.adapter = "eligo_energy"
    html = """
    <div class="flow-result-card"><span class="flow-card-title"><strong>12 Month Fixed Rate</strong></span>
      <p>Secure a fixed rate for your gas supply throughout your term</p>
      <span class="flow-card-price">69.9 cents/</span><span class="flow-card-unit">Therm</span>
      <a href="/signup/standard_residential_gas?z=njng_gas_nj&t=12&p=69900&g=0">Sign up</a>
    </div>
    """
    offer = parse_html(html, query, query.url, "a")[0]
    assert offer.price.value == Decimal("0.699")
    assert offer.term_months == 12
    assert offer.product_id == "njng_gas_nj-12-69900-0"


def test_american_power_and_gas_collapses_bill_examples_to_one_offer(query):
    from decimal import Decimal

    query.supplier = "American Power & Gas"
    query.utility = "PSE&G Gas"
    query.commodity = "gas"
    query.adapter = "american_power_and_gas"
    html = """
    <h2>Rates - Gas</h2>
    <div class="mt-4 grid grid-cols-4">
      <div>Utility</div><div>Monthly Usage</div><div>Utility Price</div><div>AP&amp;G Price</div>
      <div>Public Service Electric and Gas Residential</div><div>50</div><div>18.17</div><div>27.75</div>
      <div>Public Service Electric and Gas Residential</div><div>100</div><div>36.34</div><div>55.50</div>
      <div>Public Service Electric and Gas Residential</div><div>150</div><div>54.51</div><div>83.25</div>
      <div>Public Service Electric and Gas Residential</div><div>200</div><div>72.68</div><div>111.00</div>
    </div>
    """
    offers = parse_html(html, query, query.url, "artifact")
    assert len(offers) == 1
    assert offers[0].price.value == Decimal("0.555")
    assert offers[0].rate_structure == "variable"
    assert offers[0].term_kind == "month_to_month"
    assert len(offers[0].tiers) == 4


def test_american_power_and_gas_current_shopping_card(query):
    from decimal import Decimal

    query.supplier = "American Power & Gas"
    query.utility = "PSE&G Gas"
    query.commodity = "gas"
    query.adapter = "american_power_and_gas"
    html = """
    <div id="plans-scroller">
      <div class="plan-item"><div class="most-popular">
        <p>Gas</p><span>Variable</span><h3>Super Gas</h3>
        <span>84.90¢ / <span>therms</span></span>
        <p>Term: Monthly</p>
        <p>Monthly term with no cancellation or enrollment fees!</p>
      </div></div>
    </div>
    """
    offers = parse_html(html, query, query.url, "artifact")
    assert len(offers) == 1
    assert offers[0].name == "Super Gas"
    assert offers[0].product_id == "apg-pse-g-gas-super-gas"
    assert offers[0].price.value == Decimal("0.849")
    assert offers[0].rate_structure == "variable"
    assert offers[0].term_kind == "month_to_month"


def test_alpha_public_rate_sheet_card(query):
    from decimal import Decimal

    query.supplier = "Alpha Gas & Electric"
    query.utility = "ACE Electric"
    query.commodity = "electric"
    query.adapter = "alpha_gas_and_electric"
    html = """
    <article class="alpha-offer" data-product-id="alpha-ace-renewable-24">
      <h3>Alpha Renewable Energy 24-Month Fixed</h3>
      <p>$0.1499/kWh</p><p>24 months</p><p>Fixed rate</p>
      <p>Monthly fee: $4.99</p><p>Renewable Energy</p>
    </article>
    """
    offer = parse_html(html, query, query.url, "artifact")[0]
    assert offer.price.value == Decimal("0.1499")
    assert offer.monthly_fee == Decimal("4.99")
    assert offer.term_months == 24
    assert offer.rate_structure == "fixed"


def test_cleanchoice_rendered_cards_are_scoped(query):
    from decimal import Decimal

    query.supplier = "CleanChoice Energy"
    query.adapter = "cleanchoice"
    html = """
    <main><div class="plan-card"><h3>100% Wind and Solar</h3><p>19.5¢/kWh</p>
      <p>12 Months Fixed Rate</p><p>Enrollment fee: $0</p><p>Cancellation fee: $0</p>
      <button data-testid="select-plan-button">Select</button></div></main>
    """
    offers = parse_html(html, query, query.url, "artifact")
    assert len(offers) == 1
    assert offers[0].price.value == Decimal("0.195")
    assert offers[0].term_months == 12
    assert offers[0].renewable_percentage == 100


def test_cleanchoice_uses_displayed_rate_type_instead_of_generic_details_heading(query):
    query.supplier = "CleanChoice Energy"
    query.adapter = "cleanchoice"
    html = """
    <main><div class="plan-card"><h5>Plan details</h5><p>Rate: 20.5¢/kWh</p>
      <p>Rate type: 24 Month Fixed Rate</p><p>Energy mix: 100% Wind and Solar</p>
      <button data-testid="select-plan-button">Sign up now</button></div></main>
    """
    offer = parse_html(html, query, query.url, "artifact")[0]
    assert offer.name == "CleanChoice 24 Month Fixed Rate 100% Renewable"


def test_nextera_card_uses_data_rate_identity(query):
    from decimal import Decimal

    query.supplier = "NextEra Energy Services"
    query.utility = "ACE Electric"
    query.adapter = "nextera_energy_services"
    html = """
    <div class="pricing_plan_item plan_card"><h3>NextEra Eco Power 6</h3>
      <span class="plan_price_value">15.40</span><span>¢/kWh</span>
      <a class="learnMoreDetails" data-rate="7561|3887|1033|36136">Details</a>
      <div class="modal"><h3>NextEra Eco Power 12</h3><span>15.30¢/kWh</span>
        <p>Term: 12 Months</p></div></div>
    """
    offer = parse_html(html, query, query.url, "artifact")[0]
    assert offer.product_id == "7561|3887|1033|36136"
    assert offer.price.value == Decimal("0.154")
    assert offer.term_months == 6
    assert not any("Multiple prices" in warning for warning in offer.warnings)
    assert "Eco Power 12" not in offer.raw_fields["text"]


def test_major_energy_uses_sibling_details_and_plan_scoped_terms(query):
    from decimal import Decimal

    query.supplier = "Major Energy"
    query.utility = "PSE&G Electric"
    query.adapter = "major_energy"
    html = """
    <div class="card"><div class="card-body">
      <h3>Select 12</h3><span>Term: 12 Months</span><span>Rate Type: Fixed</span>
      <h3>$0.16990</h3><span>per kWh</span>
      <a href="/Signup/SelectProduct?productid=148074">Enroll Now</a>
    </div></div>
    <div class="collapse" id="productDetail-148074"><div class="card-body">
      <p>Energy Rate: $0.16990</p><p>Early Termination Fee: $0</p>
      <a href="/getdocument/?getproductpdf=1&amp;ProductID=148074&amp;type=TOS">Terms of Service</a>
    </div></div>
    """

    offer = parse_html(html, query, "https://signup.majorenergy.com/Plans", "artifact")[0]

    assert offer.product_id == "148074"
    assert offer.price.value == Decimal("0.16990")
    assert offer.cancellation_fee == Decimal("0")
    assert offer.raw_fields["details"].startswith("Energy Rate")
    assert len(offer.documents) == 1
    assert offer.documents[0].product_id == "148074"
    assert offer.documents[0].offer_key == offer.key


def test_cleansky_cards_use_product_term_and_explicit_rate_attributes(query):
    from decimal import Decimal

    query.supplier = "CleanSky Energy"
    query.utility = "PSE&G Gas"
    query.commodity = "gas"
    query.adapter = "cleansky_energy"
    html = """
    <div id="PlanDiv_52225_12" data-productid="52225" data-termfilter="12">
      <div id="PlanName1">Ultra Clean Gas 12</div>
      <p>12 month locked-in rate</p>
      <button data-energychargedollar="0.7990" data-term="12">Select</button>
      <a href="/NE_Home/EFL?productCode=RN0001&amp;term=12">CS</a>
      <a href="/NE_Home/TOS?productId=52225">TOS</a>
    </div>
    """
    offer = parse_html(html, query, query.url, "artifact")[0]
    assert offer.product_id == "52225"
    assert offer.price.value == Decimal("0.7990")
    assert offer.price.unit == "USD/therm"
    assert offer.term_months == 12
    assert offer.rate_structure == "fixed"
    assert {document.label for document in offer.documents} == {"CS", "TOS"}


def test_njgande_rate_cards_remain_individual_offers(query):
    from decimal import Decimal

    query.supplier = "NJG&E"
    query.utility = "NJNG Gas"
    query.commodity = "gas"
    query.adapter = "njgande"
    html = """
    <div class="ds_plan_item item_v1"><h5>Carbon Smart 36</h5><p>$0.9999/Therm</p>
      <p>36 months Fixed</p><p>100% carbon offsets</p><p>$50 Reward Dollars every month</p></div>
    <div class="ds_plan_item item_v1"><h5>Carbon Smart 24</h5><p>$0.9299/Therm</p><p>24 months Fixed</p></div>
    """
    offers = parse_html(html, query, query.url, "artifact")
    assert len(offers) == 2
    assert {offer.price.value for offer in offers} == {Decimal("0.9999"), Decimal("0.9299")}
    assert {offer.term_months for offer in offers} == {24, 36}


def test_njgande_prefers_detailed_card_with_product_id_and_rate_type(query):
    query.supplier = "NJG&E"
    query.utility = "NJNG Gas"
    query.commodity = "gas"
    query.adapter = "njgande"
    html = """
    <div class="ds_plan_item item_v1"><h5>Carbon Smart 36</h5>
      <p>$0.9999/Therm</p><p>36 months</p></div>
    <div class="ds_plan_item item_v2" data-product-id="gas-36"><h5>Carbon Smart 36</h5>
      <p>$0.9999/Therm</p><p>Term: 36 months</p><p>Rate Type: Fixed</p></div>
    """
    offers = parse_html(html, query, query.url, "artifact")
    assert len(offers) == 1
    assert offers[0].product_id == "gas-36"
    assert offers[0].rate_structure == "fixed"
    assert offers[0].warnings == []


def test_njgande_electric_cards_use_kwh_without_gas_leakage(query):
    from decimal import Decimal

    query.supplier = "NJG&E"
    query.utility = "JCP&L Electric"
    query.commodity = "electric"
    query.adapter = "njgande"
    html = """
    <div class="ds_plan_item item_v1"><h5>Power Lock Green 12</h5>
      <p>$0.1599/kWh</p><p>12 months Fixed</p><p>100% renewable energy</p></div>
    <div class="ds_plan_item item_v1"><h5>Carbon Smart Gas 12</h5>
      <p>$0.9299/Therm</p><p>12 months Fixed</p></div>
    """
    offers = parse_html(html, query, query.url, "artifact")
    assert len(offers) == 1
    assert offers[0].price.value == Decimal("0.1599")
    assert offers[0].price.unit == "USD/kWh"


def test_nordic_electric_card_uses_electric_section_and_unit(query):
    from decimal import Decimal

    query.supplier = "Nordic Energy Services"
    query.utility = "ACE Electric"
    query.commodity = "electric"
    query.adapter = "nordic_energy_services"
    html = """
    <section class="electric"><div class="utility-offer" data-id="4224">
      <span data-bind="text:promotionPrice">0.16999</span>
      <span data-bind="text:unitOfMeasure">kWh</span>
      <span data-bind="text:promotionDuration">2</span>
      <span data-bind="text:rateType">Fixed</span>
      <span data-bind="text:utilityName">Atlantic City Electric</span>
    </div></section>
    <section class="gas"><div class="utility-offer" data-id="gas-wrong">
      <span data-bind="text:promotionPrice">0.549</span>
      <span data-bind="text:unitOfMeasure">therm</span>
      <span data-bind="text:promotionDuration">2</span>
      <span data-bind="text:rateType">Fixed</span>
      <span data-bind="text:utilityName">Elizabethtown Gas</span>
    </div></section>
    """
    offers = parse_html(html, query, query.url, "artifact")
    assert len(offers) == 1
    assert offers[0].product_id == "4224"
    assert offers[0].name.endswith("Fixed Electric")
    assert offers[0].price.value == Decimal("0.16999")
    assert offers[0].price.unit == "USD/kWh"
