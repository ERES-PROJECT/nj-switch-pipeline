import pandas as pd

# This list of dictionaries contains the structured data from your research.
# This is the master list your scraper will read from.
data = [
    # === PSE&G Electric ===
    {'supplier_name': 'Constellation Energy', 'website_url': 'https://constellationrates.com/state/new-jersey/', 'edc_name': 'PSE&G Electric', 'commodity': 'electric', 'test_zip': '07102', 'scraper_status': 'pending', 'notes': 'Select Utility, Press ‘See All Plans’, Enter Zipcode, Press Continue, Lists All offers in the selected utility, can get full Terms and Conditions for contract summary by pressing ‘plan details’ and then clicking ‘terms and conditions’.'},
    {'supplier_name': 'Direct Energy', 'website_url': 'https://www.directenergy.com/new-jersey', 'edc_name': 'PSE&G Electric', 'commodity': 'electric', 'test_zip': '07102', 'scraper_status': 'pending', 'notes': 'Enter zipcode, press ‘shop plans’, Press ‘View More Plans’, once all plans viewed click ‘Learn More’ to find ‘Contract Summary’. '},
    {'supplier_name': 'NRG', 'website_url': 'https://www.picknrg.com/en/', 'edc_name': 'PSE&G Electric', 'commodity': 'electric', 'test_zip': '07102', 'scraper_status': 'pending', 'notes': 'Parent company of Verde Energy'},
    {'supplier_name': 'Major Energy', 'website_url': 'https://majorenergy.com/areas/nj/', 'edc_name': 'PSE&G Electric', 'commodity': 'electric', 'test_zip': '07102', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Frontier Utilities', 'website_url': 'https://www.frontierutilities.com/', 'edc_name': 'PSE&G Electric', 'commodity': 'electric', 'test_zip': '07102', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Great American Gas & Electric', 'website_url': 'https://www.ga-ge.com/enrollment/', 'edc_name': 'PSE&G Electric', 'commodity': 'electric', 'test_zip': '07102', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Ambit Energy', 'website_url': 'https://customer.ambitenergy.com/servicearea', 'edc_name': 'PSE&G Electric', 'commodity': 'electric', 'test_zip': '07102', 'scraper_status': 'pending', 'notes': 'Prompted for zipcode - state (seems to autofill) - Customer type - Dwelling type. Should be filled as zipcode, new jersey, click ‘Residential’, then click ‘House’. Then select the utility provider button based on the EDC test zipcode. After the radio button is clicked, scroll down to find all offers. Pressing ‘View Plan Info’ followed by clicking ‘Contract Summary and Terms of Service’ will download a pdf whose first page is the required pricing information.'},
    {'supplier_name': 'Xoom Energy', 'website_url': 'https://xoomenergy.com/en/residential/new-jersey', 'edc_name': 'PSE&G Electric', 'commodity': 'electric', 'test_zip': '07102', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'CleanChoice Energy', 'website_url': 'https://cleanchoiceenergy.com/enroll#/', 'edc_name': 'PSE&G Electric', 'commodity': 'electric', 'test_zip': '07102', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Think Energy', 'website_url': 'https://thinkenergy.com/home-nj/', 'edc_name': 'PSE&G Electric', 'commodity': 'electric', 'test_zip': '07102', 'scraper_status': 'pending', 'notes': 'Enter zipcode and click ‘View Offers’, takes you to page with offers, under each offer will be a ‘View Details +’ that can be clicked and drops down to reveal soe details and documents. Click into ‘Contract Summary’ in that dropdown for the relevant details.'},

    # === JCP&L Electric ===
    {'supplier_name': 'Direct Energy', 'website_url': 'https://www.directenergy.com/new-jersey', 'edc_name': 'JCP&L Electric', 'commodity': 'electric', 'test_zip': '07701', 'scraper_status': 'pending', 'notes': 'Enter zipcode, press ‘shop plans’, Press ‘View More Plans’, once all plans viewed click ‘Learn More’ to find ‘Contract Summary’. '},
    {'supplier_name': 'Frontier Utilities', 'website_url': 'https://www.frontierutilities.com/', 'edc_name': 'JCP&L Electric', 'commodity': 'electric', 'test_zip': '07701', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Constellation Energy', 'website_url': 'https://constellationrates.com/state/new-jersey/', 'edc_name': 'JCP&L Electric', 'commodity': 'electric', 'test_zip': '07701', 'scraper_status': 'pending', 'notes': 'Select Utility, Press ‘See All Plans’, Enter Zipcode, Press Continue, Lists All offers in the selected utility, can get full Terms and Conditions for contract summary by pressing ‘plan details’ and then clicking ‘terms and conditions’.'},
    {'supplier_name': 'Smart Energy', 'website_url': 'https://account.smartenergy.com/', 'edc_name': 'JCP&L Electric', 'commodity': 'electric', 'test_zip': '07701', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Clearview Energy', 'website_url': 'https://www.clearviewenergy.com/residential/', 'edc_name': 'JCP&L Electric', 'commodity': 'electric', 'test_zip': '07701', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'CleanChoice Energy', 'website_url': 'https://cleanchoiceenergy.com/enroll#/', 'edc_name': 'JCP&L Electric', 'commodity': 'electric', 'test_zip': '07701', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Ambit Energy', 'website_url': 'https://customer.ambitenergy.com/servicearea', 'edc_name': 'JCP&L Electric', 'commodity': 'electric', 'test_zip': '07701', 'scraper_status': 'pending', 'notes': 'Prompted for zipcode - state (seems to autofill) - Customer type - Dwelling type. Should be filled as zipcode, new jersey, click ‘Residential’, then click ‘House’. Then select the utility provider button based on the EDC test zipcode. After the radio button is clicked, scroll down to find all offers. Pressing ‘View Plan Info’ followed by clicking ‘Contract Summary and Terms of Service’ will download a pdf whose first page is the required pricing information.'},
    {'supplier_name': 'Xoom Energy', 'website_url': 'https://xoomenergy.com/en/residential/new-jersey', 'edc_name': 'JCP&L Electric', 'commodity': 'electric', 'test_zip': '07701', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Think Energy', 'website_url': 'https://thinkenergy.com/home-nj/', 'edc_name': 'JCP&L Electric', 'commodity': 'electric', 'test_zip': '07701', 'scraper_status': 'pending', 'notes': 'Enter zipcode and click ‘View Offers’, takes you to page with offers, under each offer will be a ‘View Details +’ that can be clicked and drops down to reveal soe details and documents. Click into ‘Contract Summary’ in that dropdown for the relevant details.'},
    {'supplier_name': 'IDT Energy', 'website_url': 'https://idtenergy.com/', 'edc_name': 'JCP&L Electric', 'commodity': 'electric', 'test_zip': '07701', 'scraper_status': 'pending', 'notes': ''},

    # === Atlantic City Electric ===
    {'supplier_name': 'NextEra Energy Services', 'website_url': 'https://www.nexteraenergyservices.com/residential/shop-energy-plans', 'edc_name': 'ACE Electric', 'commodity': 'electric', 'test_zip': '08401', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Direct Energy', 'website_url': 'https://www.directenergy.com/new-jersey', 'edc_name': 'ACE Electric', 'commodity': 'electric', 'test_zip': '08401', 'scraper_status': 'pending', 'notes': 'Enter zipcode, press ‘shop plans’, Press ‘View More Plans’, once all plans viewed click ‘Learn More’ to find ‘Contract Summary’. '},
    {'supplier_name': 'Constellation Energy', 'website_url': 'https://constellationrates.com/state/new-jersey/', 'edc_name': 'ACE Electric', 'commodity': 'electric', 'test_zip': '08401', 'scraper_status': 'pending', 'notes': 'Select Utility, Press ‘See All Plans’, Enter Zipcode, Press Continue, Lists All offers in the selected utility, can get full Terms and Conditions for contract summary by pressing ‘plan details’ and then clicking ‘terms and conditions’.'},
    {'supplier_name': 'Major Energy', 'website_url': 'https://majorenergy.com/areas/nj/', 'edc_name': 'ACE Electric', 'commodity': 'electric', 'test_zip': '08401', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Alpha Gas & Electric', 'website_url': 'N/A', 'edc_name': 'ACE Electric', 'commodity': 'electric', 'test_zip': '08401', 'scraper_status': 'manual_check_required', 'notes': 'Requires enrollment to see prices'},
    {'supplier_name': 'Smart Energy', 'website_url': 'https://account.smartenergy.com/', 'edc_name': 'ACE Electric', 'commodity': 'electric', 'test_zip': '08401', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Clearview Energy', 'website_url': 'https://www.clearviewenergy.com/residential/', 'edc_name': 'ACE Electric', 'commodity': 'electric', 'test_zip': '08401', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'CleanChoice Energy', 'website_url': 'https://cleanchoiceenergy.com/enroll#/', 'edc_name': 'ACE Electric', 'commodity': 'electric', 'test_zip': '08401', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Ambit Energy', 'website_url': 'https://customer.ambitenergy.com/servicearea', 'edc_name': 'ACE Electric', 'commodity': 'electric', 'test_zip': '08401', 'scraper_status': 'pending', 'notes': 'Prompted for zipcode - state (seems to autofill) - Customer type - Dwelling type. Should be filled as zipcode, new jersey, click ‘Residential’, then click ‘House’. Then select the utility provider button based on the EDC test zipcode. After the radio button is clicked, scroll down to find all offers. Pressing ‘View Plan Info’ followed by clicking ‘Contract Summary and Terms of Service’ will download a pdf whose first page is the required pricing information.'},
    {'supplier_name': 'NRG', 'website_url': 'https://www.picknrg.com/en/', 'edc_name': 'ACE Electric', 'commodity': 'electric', 'test_zip': '08401', 'scraper_status': 'pending', 'notes': ''},

    # === Rockland Electric ===
    {'supplier_name': 'CleanSky Energy', 'website_url': 'https://cleanskyenergy.com/', 'edc_name': 'Rockland Electric', 'commodity': 'electric', 'test_zip': '07430', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Direct Energy', 'website_url': 'https://www.directenergy.com/new-jersey', 'edc_name': 'Rockland Electric', 'commodity': 'electric', 'test_zip': '07430', 'scraper_status': 'pending', 'notes': 'Enter zipcode, press ‘shop plans’, Press ‘View More Plans’, once all plans viewed click ‘Learn More’ to find ‘Contract Summary’. '},
    {'supplier_name': 'Green Mountain Energy', 'website_url': 'https://www.greenmountainenergy.com/en/home-energy-solutions/shop-for-electricity', 'edc_name': 'Rockland Electric', 'commodity': 'electric', 'test_zip': '07430', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Ambit Energy', 'website_url': 'https://customer.ambitenergy.com/servicearea', 'edc_name': 'Rockland Electric', 'commodity': 'electric', 'test_zip': '07430', 'scraper_status': 'pending', 'notes': 'Prompted for zipcode - state (seems to autofill) - Customer type - Dwelling type. Should be filled as zipcode, new jersey, click ‘Residential’, then click ‘House’. Then select the utility provider button based on the EDC test zipcode. After the radio button is clicked, scroll down to find all offers. Pressing ‘View Plan Info’ followed by clicking ‘Contract Summary and Terms of Service’ will download a pdf whose first page is the required pricing information.'},
    {'supplier_name': 'IDT Energy', 'website_url': 'https://idtenergy.com/get-started/', 'edc_name': 'Rockland Electric', 'commodity': 'electric', 'test_zip': '07430', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Xoom Energy', 'website_url': 'https://xoomenergy.com/en/residential/new-jersey', 'edc_name': 'Rockland Electric', 'commodity': 'electric', 'test_zip': '07430', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'NRG', 'website_url': 'https://www.picknrg.com/en/', 'edc_name': 'Rockland Electric', 'commodity': 'electric', 'test_zip': '07430', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Think Energy', 'website_url': 'https://thinkenergy.com/home-nj/', 'edc_name': 'Rockland Electric', 'commodity': 'electric', 'test_zip': '07430', 'scraper_status': 'pending', 'notes': 'Enter zipcode and click ‘View Offers’, takes you to page with offers, under each offer will be a ‘View Details +’ that can be clicked and drops down to reveal soe details and documents. Click into ‘Contract Summary’ in that dropdown for the relevant details.'},
    {'supplier_name': 'Smart Energy', 'website_url': 'https://account.smartenergy.com/', 'edc_name': 'Rockland Electric', 'commodity': 'electric', 'test_zip': '07430', 'scraper_status': 'pending', 'notes': ''},
    
    # === PSE&G Gas ===
    {'supplier_name': 'Constellation Energy', 'website_url': 'https://constellationrates.com/state/new-jersey/', 'edc_name': 'PSE&G Gas', 'commodity': 'gas', 'test_zip': '07102', 'scraper_status': 'pending', 'notes': 'Select Utility, Press ‘See All Plans’, Enter Zipcode, Press Continue, Lists All offers in the selected utility, can get full Terms and Conditions for contract summary by pressing ‘plan details’ and then clicking ‘terms and conditions’.'},
    {'supplier_name': 'Direct Energy', 'website_url': 'https://www.directenergy.com/new-jersey', 'edc_name': 'PSE&G Gas', 'commodity': 'gas', 'test_zip': '07102', 'scraper_status': 'pending', 'notes': 'Enter zipcode, press ‘shop plans’, Press ‘View More Plans’, once all plans viewed click ‘Learn More’ to find ‘Contract Summary’. '},
    {'supplier_name': 'Frontier Utilities', 'website_url': 'https://www.frontierutilities.com/', 'edc_name': 'PSE&G Gas', 'commodity': 'gas', 'test_zip': '07102', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Major Energy', 'website_url': 'https://majorenergy.com/areas/nj/', 'edc_name': 'PSE&G Gas', 'commodity': 'gas', 'test_zip': '07102', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Xoom Energy', 'website_url': 'https://xoomenergy.com/en/residential/new-jersey', 'edc_name': 'PSE&G Gas', 'commodity': 'gas', 'test_zip': '07102', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'NRG', 'website_url': 'https://www.picknrg.com/en/', 'edc_name': 'PSE&G Gas', 'commodity': 'gas', 'test_zip': '07102', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'IDT Energy', 'website_url': 'https://idtenergy.com/get-started/', 'edc_name': 'PSE&G Gas', 'commodity': 'gas', 'test_zip': '07102', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Residents Energy', 'website_url': 'https://residentsenergy.com/', 'edc_name': 'PSE&G Gas', 'commodity': 'gas', 'test_zip': '07102', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'CleanSky Energy', 'website_url': 'https://cleanskyenergy.com/', 'edc_name': 'PSE&G Gas', 'commodity': 'gas', 'test_zip': '07102', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'American Power & Gas', 'website_url': 'https://americanpowerandgas.com/', 'edc_name': 'PSE&G Gas', 'commodity': 'gas', 'test_zip': '07102', 'scraper_status': 'manual_check_required', 'notes': 'Site requires full address, not just zip'},

    # === New Jersey Natural Gas ===
    {'supplier_name': 'NJG&E', 'website_url': 'https://www.njgande.com/', 'edc_name': 'NJNG Gas', 'commodity': 'gas', 'test_zip': '07712', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Constellation Energy', 'website_url': 'https://constellationrates.com/state/new-jersey/', 'edc_name': 'NJNG Gas', 'commodity': 'gas', 'test_zip': '07712', 'scraper_status': 'pending', 'notes': 'Select Utility, Press ‘See All Plans’, Enter Zipcode, Press Continue, Lists All offers in the selected utility, can get full Terms and Conditions for contract summary by pressing ‘plan details’ and then clicking ‘terms and conditions’.'},
    {'supplier_name': 'Direct Energy', 'website_url': 'https://www.directenergy.com/new-jersey', 'edc_name': 'NJNG Gas', 'commodity': 'gas', 'test_zip': '07712', 'scraper_status': 'pending', 'notes': 'Enter zipcode, press ‘shop plans’, Press ‘View More Plans’, once all plans viewed click ‘Learn More’ to find ‘Contract Summary’. '},
    {'supplier_name': 'Frontier Utilities', 'website_url': 'https://www.frontierutilities.com/', 'edc_name': 'NJNG Gas', 'commodity': 'gas', 'test_zip': '07712', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Major Energy', 'website_url': 'https://majorenergy.com/areas/nj/', 'edc_name': 'NJNG Gas', 'commodity': 'gas', 'test_zip': '07712', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Xoom Energy', 'website_url': 'https://xoomenergy.com/en/residential/new-jersey', 'edc_name': 'NJNG Gas', 'commodity': 'gas', 'test_zip': '07712', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Residents Energy', 'website_url': 'https://residentsenergy.com/', 'edc_name': 'NJNG Gas', 'commodity': 'gas', 'test_zip': '07712', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'IDT Energy', 'website_url': 'https://idtenergy.com/', 'edc_name': 'NJNG Gas', 'commodity': 'gas', 'test_zip': '07712', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Clearview Energy', 'website_url': 'https://www.clearviewenergy.com/', 'edc_name': 'NJNG Gas', 'commodity': 'gas', 'test_zip': '07712', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Eligo Energy', 'website_url': 'https://www.eligoenergy.com/', 'edc_name': 'NJNG Gas', 'commodity': 'gas', 'test_zip': '07712', 'scraper_status': 'pending', 'notes': ''},

    # === South Jersey Gas ===
    {'supplier_name': 'NJG&E', 'website_url': 'https://www.njgande.com/', 'edc_name': 'SJG Gas', 'commodity': 'gas', 'test_zip': '08094', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Clearview Energy', 'website_url': 'https://www.clearviewenergy.com/', 'edc_name': 'SJG Gas', 'commodity': 'gas', 'test_zip': '08094', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Constellation Energy', 'website_url': 'https://constellationrates.com/state/new-jersey/', 'edc_name': 'SJG Gas', 'commodity': 'gas', 'test_zip': '08094', 'scraper_status': 'pending', 'notes': 'Select Utility, Press ‘See All Plans’, Enter Zipcode, Press Continue, Lists All offers in the selected utility, can get full Terms and Conditions for contract summary by pressing ‘plan details’ and then clicking ‘terms and conditions’.'},
    {'supplier_name': 'Direct Energy', 'website_url': 'https://www.directenergy.com/new-jersey', 'edc_name': 'SJG Gas', 'commodity': 'gas', 'test_zip': '08094', 'scraper_status': 'pending', 'notes': 'Enter zipcode, press ‘shop plans’, Press ‘View More Plans’, once all plans viewed click ‘Learn More’ to find ‘Contract Summary’. '},
    {'supplier_name': 'Major Energy', 'website_url': 'https://majorenergy.com/areas/nj/', 'edc_name': 'SJG Gas', 'commodity': 'gas', 'test_zip': '08094', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Xoom Energy', 'website_url': 'https://xoomenergy.com/en/residential/new-jersey', 'edc_name': 'SJG Gas', 'commodity': 'gas', 'test_zip': '08094', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'NRG', 'website_url': 'https://www.picknrg.com/en/', 'edc_name': 'SJG Gas', 'commodity': 'gas', 'test_zip': '08094', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'CleanSky Energy', 'website_url': 'https://cleanskyenergy.com/', 'edc_name': 'SJG Gas', 'commodity': 'gas', 'test_zip': '08094', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Residents Energy', 'website_url': 'https://residentsenergy.com/', 'edc_name': 'SJG Gas', 'commodity': 'gas', 'test_zip': '08094', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Smart Energy', 'website_url': 'https://www.smartenergy.com/', 'edc_name': 'SJG Gas', 'commodity': 'gas', 'test_zip': '08094', 'scraper_status': 'pending', 'notes': ''},

    # === Elizabethtown Gas ===
    {'supplier_name': 'Constellation Energy', 'website_url': 'https://constellationrates.com/state/new-jersey/', 'edc_name': 'ETG Gas', 'commodity': 'gas', 'test_zip': '07201', 'scraper_status': 'pending', 'notes': 'Select Utility, Press ‘See All Plans’, Enter Zipcode, Press Continue, Lists All offers in the selected utility, can get full Terms and Conditions for contract summary by pressing ‘plan details’ and then clicking ‘terms and conditions’.'},
    {'supplier_name': 'Direct Energy', 'website_url': 'https://www.directenergy.com/new-jersey', 'edc_name': 'ETG Gas', 'commodity': 'gas', 'test_zip': '07201', 'scraper_status': 'pending', 'notes': 'Enter zipcode, press ‘shop plans’, Press ‘View More Plans’, once all plans viewed click ‘Learn More’ to find ‘Contract Summary’. '},
    {'supplier_name': 'Major Energy', 'website_url': 'https://majorenergy.com/areas/nj/', 'edc_name': 'ETG Gas', 'commodity': 'gas', 'test_zip': '07201', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Frontier Utilities', 'website_url': 'https://www.frontierutilities.com/', 'edc_name': 'ETG Gas', 'commodity': 'gas', 'test_zip': '07201', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'CleanSky Energy', 'website_url': 'https://cleanskyenergy.com/', 'edc_name': 'ETG Gas', 'commodity': 'gas', 'test_zip': '07201', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'Smart Energy', 'website_url': 'https://www.smartenergy.com/', 'edc_name': 'ETG Gas', 'commodity': 'gas', 'test_zip': '07201', 'scraper_status': 'pending', 'notes': ''},
    {'supplier_name': 'American Power & Gas', 'website_url': 'https://americanpowerandgas.com/', 'edc_name': 'ETG Gas', 'commodity': 'gas', 'test_zip': '07201', 'scraper_status': 'manual_check_required', 'notes': 'Site requires full address, not just zip'},
]

# Create a pandas DataFrame from the list of dictionaries
df = pd.DataFrame(data)

# Define the desired column order
column_order = [
    'supplier_name',
    'edc_name',
    'commodity',
    'test_zip',
    'website_url',
    'scraper_status',
    'notes'
]
df = df[column_order]

# Save the DataFrame to a CSV file
output_filename = 'master_third_party_supplier_list.csv'
df.to_csv(output_filename, index=False)

print(f"Successfully created '{output_filename}' with {len(df)} entries.")
print("\nDataFrame Preview:")
print(df.head())