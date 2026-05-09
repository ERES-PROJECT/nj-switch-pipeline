"""Check Direct Energy T&C URL (TCPage.aspx)"""
import urllib.request, ssl, io
from bs4 import BeautifulSoup
import re

url = "http://DirectEnergyDocuments.gesc.com/TCPage.aspx?Doc=DERNJDTDTCE"
ctx = ssl._create_unverified_context()
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
resp = urllib.request.urlopen(req, context=ctx, timeout=15)
data = resp.read()
ct = resp.getheader('Content-Type')
print(f"Content-Type: {ct}")
print(f"First 4 bytes: {data[:4]}")
if data[:4] == b'%PDF':
    import pdfplumber
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages[:3])
    print("PDF TEXT (first 2000 chars):")
    print(text[:2000])
else:
    text = data.decode('utf-8', errors='replace')
    soup = BeautifulSoup(text, 'lxml')
    body = soup.get_text(separator=' ', strip=True)
    print("HTML TEXT (first 2000 chars):")
    print(body[:2000])
    # Look for rates
    for m in re.finditer(r'[\d.]+\s*[¢¢\u00a2]|[\d.]+\s*/\s*kWh|\$[\d.]+', body, re.I):
        print('  rate match:', m.group())
