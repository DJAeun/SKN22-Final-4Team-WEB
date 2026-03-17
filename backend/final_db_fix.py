import sqlite3
import os

db_path = 'db.sqlite3'
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Check if column exists first
    cursor.execute("PRAGMA table_info(chat_chatsession)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'session_key' not in columns:
        print("Adding session_key column...")
        cursor.execute("ALTER TABLE chat_chatsession ADD COLUMN session_key VARCHAR(64) NULL")
        cursor.execute("CREATE INDEX IF NOT EXISTS chat_chatsession_session_key_idx ON chat_chatsession(session_key)")
        conn.commit()
        print("Successfully added column and index.")
    else:
        print("Column already exists.")
    conn.close()
except Exception as e:
    print(f"Error during manual fix: {e}")
    # If it's locked, just wait or try later.
