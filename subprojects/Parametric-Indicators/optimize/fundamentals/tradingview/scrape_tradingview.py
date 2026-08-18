import requests
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time

API_URL = "https://economic-calendar.tradingview.com/events"

HEADERS = {
    "Origin": "https://www.tradingview.com",
    "Referer": "https://www.tradingview.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

COUNTRIES = "US"
START_DATE = datetime(2010, 1, 1)
END_DATE = datetime(2026, 8, 7)
MAX_RETRIES = 5  # Number of times to retry a failed request

all_events = []

current = START_DATE

# Use a session to reuse the underlying TCP connection (faster and more stable)
session = requests.Session()
session.headers.update(HEADERS)

while current <= END_DATE:
    next_month = current + relativedelta(months=1)

    from_time = current.strftime("%Y-%m-%dT00:00:00Z")
    to_time = (next_month - relativedelta(seconds=1)).strftime("%Y-%m-%dT23:59:59Z")

    print(f"Downloading {from_time} -> {to_time}")

    # Retry loop for network stability
    for attempt in range(MAX_RETRIES):
        try:
            response = session.get(
                API_URL,
                params={
                    "from": from_time,
                    "to": to_time,
                    "countries": COUNTRIES
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if "result" in data:
                all_events.extend(data["result"])
            
            # Break out of the retry loop if successful
            break 
            
        except requests.exceptions.RequestException as e:
            print(f"  [!] Attempt {attempt + 1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                sleep_time = (attempt + 1) * 5  # Wait 5s, 10s, 15s...
                print(f"  [*] Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                print(f"  [X] Failed to fetch data for {from_time} after {MAX_RETRIES} attempts. Skipping.")

    current = next_month
    time.sleep(1)  # Be polite to the API

df = pd.DataFrame(all_events)
print(f"\nDownloaded {len(df)} events total.")

# Save to CSV
df.to_csv("tradingview_us_2010_2026.csv", index=False)
print("Saved to tradingview_us_2010_2026.csv")