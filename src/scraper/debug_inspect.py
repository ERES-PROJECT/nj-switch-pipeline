"""Quick inspector for the saved debug HTML files."""
import os
from bs4 import BeautifulSoup

DEBUG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug")

def inspect(filename, label):
    path = os.path.join(DEBUG_DIR, filename)
    if not os.path.exists(path):
        print(f"[MISSING] {filename}")
        return
    with open(path, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")

    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")

    # Selects
    for sel in soup.find_all("select"):
        opts = [o.get_text(strip=True) for o in sel.find_all("option")]
        print(f"  <select name={sel.get('name')} id={sel.get('id')}> options: {opts}")

    # Inputs
    for inp in soup.find_all("input"):
        if inp.get("type") not in ("hidden", "checkbox", "radio"):
            print(f"  <input type={inp.get('type')} name={inp.get('name')} id={inp.get('id')} placeholder={inp.get('placeholder')!r} class={inp.get('class')}>")

    # Buttons
    for btn in soup.find_all("button")[:15]:
        print(f"  <button class={btn.get('class')}> {btn.get_text(strip=True)[:60]!r}")

    # Price/rate containers
    print("  --- Price containers ---")
    for tag in soup.find_all(True):
        txt = tag.get_text(separator=" ", strip=True)
        if ("kWh" in txt or "¢" in txt or ("cent" in txt.lower() and "per" in txt.lower())) and len(txt) < 400:
            cls = " ".join(tag.get("class") or [])
            print(f"  <{tag.name} class={cls[:70]!r}> {txt[:200]!r}")

    # All unique class names containing plan/offer/rate/card
    print("  --- Relevant class names ---")
    seen = set()
    for tag in soup.find_all(True):
        for cls in (tag.get("class") or []):
            if any(k in cls.lower() for k in ["plan","offer","rate","card","product","deal","package","energy","price","kwh"]):
                if cls not in seen:
                    seen.add(cls)
                    print(f"  .{cls}")

inspect("Constellation_Energy__PSEandG_Electric__utility_not_found.html", "CONSTELLATION")
inspect("Direct_Energy__PSEandG_Electric__error.html", "DIRECT ENERGY")
inspect("Think_Energy__PSEandG_Electric__error.html", "THINK ENERGY")
inspect("Ambit_Energy__PSEandG_Electric__error.html", "AMBIT ENERGY")
inspect("NRG__PSEandG_Electric__no_zip_input.html", "NRG")
inspect("Frontier_Utilities__PSEandG_Electric__no_zip_input.html", "FRONTIER UTILITIES")
inspect("CleanChoice_Energy__PSEandG_Electric__no_zip_input.html", "CLEANCHOICE ENERGY")
inspect("Great_American_Gas_and_Electric__PSEandG_Electric__no_submit_btn.html", "GREAT AMERICAN GAS & ELECTRIC")
