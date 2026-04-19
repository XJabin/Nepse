import sqlite3
import os

def initialize_database():
    conn = sqlite3.connect('nepse_data.db') 
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            close REAL,
            vol INTEGER,
            UNIQUE(symbol, date)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database Table 'daily_stock' successfully created at Root.")