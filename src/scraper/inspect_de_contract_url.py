"""Check what the Direct Energy Contract Summary ASPX URL returns"""
import urllib.request, ssl, re
from bs4 import BeautifulSoup

url = "http://DirectEnergyDocuments.gesc.com/RatePlanSummary.aspx?RateID=855041&sc=RES&esco=DER"
ctx = ssl._create_unverified_context()
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
resp = urllib.request.urlopen(req, context=ctx, timeout=15)
data = resp.read()
print(f"Content-Type: {resp.getheader('Content-Type')}")
print(f"First 4 bytes: {data[:4]}")
if data[:4] == b'%PDF':
    print("=> PDF file")
else:
    text = data.decode('utf-8', errors='replace')
    soup = BeautifulSoup(text, 'lxml')
    body = soup.get_text(separator=' ', strip=True)
    print("Page text (first 2000 chars):")
    print(body[:2000])
    # Look for rate patterns
    print("\n--- Rate patterns ---")
    for m in re.finditer(r'[\d.]+\s*[¢¢]|[\d.]+\s*/\s*kWh|\$[\d.]+', body, re.I):
        print(' ', m.group())
