from bs4 import BeautifulSoup
from pathlib import Path

path = Path(__file__).resolve().parent / "debug/Constellation_Energy__PSEandG_Electric__utility_not_found.html"
with path.open(encoding='utf-8') as f:
    html = f.read()
soup = BeautifulSoup(html, 'lxml')

print("FULL Terms and Conditions link hrefs:")
for a in soup.find_all('a', href=True):
    t = a.get_text(strip=True)
    h = a['href']
    if 'terms' in t.lower() or 'terms' in h.lower() or 'tand' in h.lower():
        print(f'  text={repr(t)}')
        print(f'  href={h}')
        print()

# Also look at all links in the page
print("\n--- ALL links in plan area ---")
for el in soup.find_all(class_=lambda c: c and ('rate' in str(c).lower() or 'plan' in str(c).lower() or 'rateCost' in str(c))):
    if el.find('a', href=True):
        print(f'Container class: {el.get("class")}')
        for a in el.find_all('a', href=True):
            print(f'  link: {repr(a.get_text(strip=True)[:50])} -> {a["href"]}')
        break
