
import sqlite3
import os

db_path = 'db.sqlite3'
print(f"Opening database at {db_path}...")

if not os.path.exists(db_path):
    print("Database file not found.")
    exit(1)

try:
    conn = sqlite3.connect(db_path, timeout=5)
    cursor = conn.cursor()
    
    # 1. Check current schema
    cursor.execute("PRAGMA table_info(chat_chatsession);")
    columns = cursor.fetchall()
    print("Current columns in chat_chatsession:")
    for col in columns:
        print(col)
        # col format: (id, name, type, notnull, default_value, pk)
        if col[1] == 'user_id':
            if col[3] == 1:
                print("!!! CRITICAL: user_id has NOT NULL constraint. Fixing...")
    
    # 2. SQLite doesn't support ALTER TABLE DROP CONSTRAINT or ALTER COLUMN.
    # We must do the "move data" approach if we want to fix it properly.
    # But first, let's see if we can just try to make it nullable via a simple update if possible (standard SQL doesn't allow this in SQLite).
    
    # Let's try to just insert a Null row to verify the constraint.
    try:
        cursor.execute("INSERT INTO chat_chatsession (started_at, updated_at, summary) VALUES (CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'test_null');")
        print("Success! Inserted a session with NULL user_id. Constraint is NOT active.")
        conn.rollback()
    except sqlite3.IntegrityError as e:
        print(f"Failed! Constraint IS active: {e}")
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
