"""Fetch and print the text content of a Direct Energy Contract Summary PDF"""
import urllib.request, ssl, io
import pdfplumber

url = "http://DirectEnergyDocuments.gesc.com/RatePlanSummary.aspx?RateID=855041&sc=RES&esco=DER"
ctx = ssl._create_unverified_context()
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
resp = urllib.request.urlopen(req, context=ctx, timeout=15)
data = resp.read()

with pdfplumber.open(io.BytesIO(data)) as pdf:
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        print(f"=== PAGE {i+1} ({len(text)} chars) ===")
        print(text[:2000])
        print()
