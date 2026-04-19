import sqlite3
import os
import time
from playwright.sync_api import sync_playwright

def scrape_nepse_automation():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, "nepse_data.db")
    url = "https://www.nepalstock.com.np/today-price"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            ignore_https_errors=True
        )
        page = context.new_page()

        try:
            print("🚀 Navigating to NEPSE...")
            page.goto(url, wait_until="load", timeout=90000)
            
            # ५०० को फिल्टर सेट गर्ने नयाँ लजिक
            print("🔍 Setting filter to 500...")
            try:
                # पहिले select ट्याग नआउन्जेल २० सेकेन्ड कुर्ने
                page.wait_for_selector('select', timeout=20000)
                # ५०० विकल्प छान्ने
                page.select_option('select', "500")
                time.sleep(5) # डाटा रिफ्रेस हुन समय दिने
            except Exception as e:
                print(f"⚠️ Filter dropdown failed: {e}. Scraping default view.")

            # टेबलको डाटा तान्ने
            page.wait_for_selector('table tbody tr', timeout=20000)
            table_data = page.evaluate("""
                () => {
                    const rows = Array.from(document.querySelectorAll('table tbody tr'));
                    return rows.map(row => {
                        const cols = Array.from(row.querySelectorAll('td'));
                        return cols.map(col => col.innerText.trim());
                    }).filter(row => row.length >= 10);
                }
            """)

            if table_data:
                print(f"✅ Extracted {len(table_data)} rows.")
                conn = sqlite3.connect(db_path)
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS daily_stock (
                        symbol TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, vol REAL,
                        UNIQUE(symbol, date)
                    )
                ''')
                
                count = 0
                for row in table_data:
                    try:
                        symbol = row[1]
                        open_p = float(row[3].replace(',', ''))
                        high_p = float(row[4].replace(',', ''))
                        low_p = float(row[5].replace(',', ''))
                        close_p = float(row[6].replace(',', ''))
                        vol = float(row[9].replace(',', ''))
                        date_val = row[10]

                        conn.execute("""
                            INSERT OR REPLACE INTO daily_stock (symbol, date, open, high, low, close, vol)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (symbol, date_val, open_p, high_p, low_p, close_p, vol))
                        count += 1
                    except:
                        continue
                
                conn.commit()
                conn.close()
                print(f"🎉 Success: {count} records in database.")
        except Exception as e:
            print(f"💀 Critical Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_nepse_automation()