import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

KBDI_URL    = "https://weather.fdacs.gov/KBDI/current-report.html"
BURN_URL    = "https://weather.fdacs.gov/BA/burn-auth.html"
COUNTY_NAME = "Martin"
HTML_FILE   = "index.html"
HEADERS     = {"User-Agent": "Mozilla/5.0 (compatible; MCFR-SitRep-Bot/1.0)"}

def fetch_kbdi():
    try:
        r = requests.get(KBDI_URL, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for row in soup.find_all("tr"):
            cells = [c.get_text(strip=True) for c in row.find_all(["td","th"])]
            if any(COUNTY_NAME.lower() in t.lower() for t in cells):
                numbers = [t for t in cells if re.match(r'^-?\d+\.?\d*$', t.replace(',',''))]
                if len(numbers) >= 2:
                    mean = numbers[0]
                    change = ('+' if not numbers[1].startswith('-') else '') + numbers[1]
                    print(f"KBDI Mean: {mean}, Change: {change}")
                    return {"mean": mean, "change": change}
    except Exception as e:
        print(f"KBDI fetch failed: {e}")
    return None

def fetch_burn_auth():
    try:
        r = requests.get(BURN_URL, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for row in soup.find_all("tr"):
            cells = [c.get_text(strip=True) for c in row.find_all(["td","th"])]
            if any(COUNTY_NAME.lower() in t.lower() for t in cells):
                for t in cells:
                    upper = t.upper().strip()
                    if upper in ["YES","NO","RESTRICTED","AUTHORIZED","NOT AUTHORIZED"]:
                        result = "YES" if upper in ["YES","AUTHORIZED"] else "RESTRICTED" if upper == "RESTRICTED" else "NO"
                        print(f"Burn auth: {result}")
                        return result
    except Exception as e:
        print(f"Burn auth fetch failed: {e}")
    return None

def update_html(kbdi, burn_auth):
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()
    if kbdi:
        html = re.sub(r"(kbdi:\s*\{[^}]*mean\s*:)\s*'[^']*'", f"\\1 '{kbdi['mean']}'", html)
        html = re.sub(r"(kbdi:\s*\{[^}]*change\s*:)\s*'[^']*'", f"\\1 '{kbdi['change']}'", html)
    if burn_auth:
        html = re.sub(r"(burn\s*:\s*)'[^']*'", f"\\1'{burn_auth}'", html)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M ET")
    if '<!-- AUTO-UPDATED:' in html:
        html = re.sub(r'<!-- AUTO-UPDATED:.*?-->', f'<!-- AUTO-UPDATED: {timestamp} -->', html)
    else:
        html = html.replace('<body>', f'<!-- AUTO-UPDATED: {timestamp} -->\n<body>', 1)
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"index.html updated at {timestamp}")

if __name__ == "__main__":
    kbdi      = fetch_kbdi()
    burn_auth = fetch_burn_auth()
    if kbdi or burn_auth:
        update_html(kbdi, burn_auth)
    else:
        print("No data retrieved — index.html not modified.")
