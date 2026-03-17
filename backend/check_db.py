import sqlite3
import os

db_path = 'db.sqlite3'
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found")
else:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(chat_chatsession)")
        columns = cursor.fetchall()
        print("Columns in chat_chatsession:")
        for col in columns:
            print(col)
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
