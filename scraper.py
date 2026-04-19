import asyncio
from playwright.async_api import async_playwright
import sqlite3
import random

async def scrape_nepse_data():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            url = "https://www.nepalstock.com.np/today-price"
            print(f"Navigating to {url}...")
            await page.goto(url, wait_until="networkidle", timeout=90000)
            
            all_data = []
            page_num = 1

            while True:
                print(f"Scraping Page {page_num}...")
                
                rows_data = await page.evaluate('''() => {
                    const rows = Array.from(document.querySelectorAll('table tbody tr'));
                    const results = [];
                    const today = new Date().toISOString().split('T')[0];
                    
                    rows.forEach(row => {
                        const cols = row.querySelectorAll('td');
                        if (cols.length >= 10) {
                            results.push({
                                // 'SCRAPED_DATA' को सट्टा वास्तविक सिम्बोल (NTC, NABIL, etc.) लिने
                                symbol: cols[1] ? cols[1].innerText.trim() : 'UNKNOWN',
                                date: today,
                                open: cols[3] ? cols[3].innerText.replace(/,/g, '') : '0',
                                high: cols[4] ? cols[4].innerText.replace(/,/g, '') : '0',
                                low: cols[5] ? cols[5].innerText.replace(/,/g, '') : '0',
                                close: cols[6] ? cols[6].innerText.replace(/,/g, '') : '0',
                                vol: cols[9] ? cols[9].innerText.replace(/,/g, '') : '0'
                            });
                        }
                    });
                    return results;
                }''')
                
                if rows_data:
                    all_data.extend(rows_data)

                next_btn = page.locator('li.pagination-next:not(.disabled)')
                if await next_btn.count() > 0:
                    await next_btn.click()
                    await page.wait_for_timeout(random.randint(3000, 5000))
                    page_num += 1
                else:
                    break

            if all_data:
                conn = sqlite3.connect('nepse_data.db')
                cursor = conn.cursor()
                
                cursor.execute('''CREATE TABLE IF NOT EXISTS daily_stock (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    symbol TEXT, 
                    date TEXT, 
                    open REAL, 
                    high REAL, 
                    low REAL, 
                    close REAL, 
                    vol REAL,
                    UNIQUE(symbol, date)
                )''')
                
                print(f"Pushing {len(all_data)} records to database...")
                for item in all_data:
                    cursor.execute('''
                        INSERT OR IGNORE INTO daily_stock (symbol, date, open, high, low, close, vol)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (item['symbol'], item['date'], item['open'], item['high'], item['low'], item['close'], item['vol']))
                
                conn.commit()
                conn.close()
                print("Success: New historical data added!")

        except Exception as e:
            print(f"Error occurred: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_nepse_data())