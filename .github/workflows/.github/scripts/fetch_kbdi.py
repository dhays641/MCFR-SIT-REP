#!/usr/bin/env python3
"""
MCFR Sitrep Auto-Updater
Fetches KBDI data for Martin County from Florida Forest Service
and updates index.html with the latest values.

Runs via GitHub Actions every day at 2:00 PM Eastern.
"""

import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime

# ── CONFIG ────────────────────────────────────────────────────
KBDI_URL      = "https://weather.fdacs.gov/KBDI/current-report.html"
BURN_URL      = "https://weather.fdacs.gov/BA/burn-auth.html"
COUNTY_NAME   = "Martin"
HTML_FILE     = "index.html"
HEADERS       = {"User-Agent": "Mozilla/5.0 (compatible; MCFR-SitRep-Bot/1.0)"}

# ── FETCH KBDI ────────────────────────────────────────────────
def fetch_kbdi():
    print(f"Fetching KBDI from {KBDI_URL}...")
    try:
        r = requests.get(KBDI_URL, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Find the table row for Martin County
        # The page has a table with county rows
        for row in soup.find_all("tr"):
            cells = row.find_all(["td", "th"])
            cell_texts = [c.get_text(strip=True) for c in cells]
            
            # Look for Martin County row
            if any(COUNTY_NAME.lower() in t.lower() for t in cell_texts):
                print(f"Found row: {cell_texts}")
                
                # Typical column order: County | Mean | Change | Min | Max
                # Extract numeric values
                numbers = []
                for t in cell_texts:
                    # Strip county name, keep numbers
                    clean = t.replace(',', '')
                    if re.match(r'^-?\d+\.?\d*$', clean):
                        numbers.append(clean)
                
                if len(numbers) >= 2:
                    mean   = numbers[0]
                    change = ('+' if not numbers[1].startswith('-') else '') + numbers[1]
                    min_v  = numbers[2] if len(numbers) > 2 else '--'
                    max_v  = numbers[3] if len(numbers) > 3 else '--'
                    print(f"KBDI — Mean: {mean}, Change: {change}, Min: {min_v}, Max: {max_v}")
                    return {"mean": mean, "change": change, "min": min_v, "max": max_v}

        print("Martin County row not found in KBDI table.")
        return None

    except Exception as e:
        print(f"KBDI fetch failed: {e}")
        return None


# ── FETCH BURN AUTH ───────────────────────────────────────────
def fetch_burn_auth():
    print(f"Fetching burn authorization...")
    try:
        r = requests.get(BURN_URL, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        for row in soup.find_all("tr"):
            cells = row.find_all(["td", "th"])
            cell_texts = [c.get_text(strip=True) for c in cells]
            
            if any(COUNTY_NAME.lower() in t.lower() for t in cell_texts):
                print(f"Burn auth row: {cell_texts}")
                # Look for YES/NO/RESTRICTED in the row
                for t in cell_texts:
                    upper = t.upper().strip()
                    if upper in ["YES", "NO", "RESTRICTED", "AUTHORIZED", "NOT AUTHORIZED"]:
                        result = "YES" if upper in ["YES", "AUTHORIZED"] else \
                                 "RESTRICTED" if upper == "RESTRICTED" else "NO"
                        print(f"Burn auth: {result}")
                        return result
        
        print("Burn auth for Martin County not found.")
        return None

    except Exception as e:
        print(f"Burn auth fetch failed: {e}")
        return None


# ── UPDATE HTML ───────────────────────────────────────────────
def update_html(kbdi, burn_auth):
    print(f"\nUpdating {HTML_FILE}...")
    
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    updated = False

    # Update KBDI values in the state object in the JS
    # The state object has: kbdi: { mean:'402', change:'+7', rhDay:'53%', rhNight:'100%' }
    if kbdi:
        # Update mean
        html = re.sub(
            r"(kbdi:\s*\{[^}]*mean\s*:)\s*'[^']*'",
            f"\\1 '{kbdi['mean']}'",
            html
        )
        # Update change
        html = re.sub(
            r"(kbdi:\s*\{[^}]*change\s*:)\s*'[^']*'",
            f"\\1 '{kbdi['change']}'",
            html
        )
        print(f"✓ KBDI updated — Mean: {kbdi['mean']}, Change: {kbdi['change']}")
        updated = True

    # Update burn auth
    if burn_auth:
        html = re.sub(
            r"(burn\s*:\s*)'[^']*'",
            f"\\1'{burn_auth}'",
            html
        )
        print(f"✓ Burn auth updated — {burn_auth}")
        updated = True

    # Add a last-auto-updated comment near the top for tracking
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M ET")
    html = re.sub(
        r'<!-- AUTO-UPDATED:.*?-->',
        f'<!-- AUTO-UPDATED: {timestamp} -->',
        html
    )
    if '<!-- AUTO-UPDATED:' not in html:
        html = html.replace('<body>', f'<!-- AUTO-UPDATED: {timestamp} -->\n<body>', 1)

    if updated:
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"\n✓ {HTML_FILE} saved successfully.")
    else:
        print("\n⚠ No updates made — check parsing above.")

    return updated


# ── MAIN ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("MCFR Sitrep Auto-Updater")
    print(f"Running at: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    kbdi      = fetch_kbdi()
    burn_auth = fetch_burn_auth()

    if kbdi or burn_auth:
        update_html(kbdi, burn_auth)
    else:
        print("\n⚠ No data retrieved. index.html not modified.")
        print("The duty officer should update KBDI manually today.")

    print("\nDone.")
