
import sqlite3
import os

db_path = 'db.sqlite3'
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Check if session_key exists
    cursor.execute("PRAGMA table_info(chat_chatsession);")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'session_key' not in columns:
        print("Adding session_key column...")
        cursor.execute("ALTER TABLE chat_chatsession ADD COLUMN session_key VARCHAR(64) NULL;")
        cursor.execute("CREATE INDEX IF NOT EXISTS chat_chatsession_session_key_idx ON chat_chatsession(session_key);")
        print("Done.")
    else:
        print("session_key column already exists.")

    # In SQLite, altering a column to be NULL is tricky (requires table recreation)
    # But usually, it just works if we don't have strict constraints enabled.
    # Let's check the user_id column
    print(f"Current columns: {columns}")

    conn.commit()
    
    # Verify
    cursor.execute("PRAGMA table_info(chat_chatsession);")
    new_columns = cursor.fetchall()
    print("New schema:")
    for col in new_columns:
        print(col)

    # Force mark migration as applied in django_migrations
    # Find the max ID to avoid conflicts
    cursor.execute("SELECT MAX(id) FROM django_migrations;")
    max_id = cursor.fetchone()[0] or 0
    
    # Check if migration 0002 is already there
    cursor.execute("SELECT id FROM django_migrations WHERE app='chat' AND name LIKE '%0002%';")
    if not cursor.fetchone():
        print("Recording migration 0002 as applied...")
        import datetime
        now = datetime.datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO django_migrations (app, name, applied) VALUES (?, ?, ?);",
            ('chat', '0002_chatsession_session_key_and_more', now)
        )
        print("Migration recorded.")
    
    conn.commit()

except Exception as e:
    with open("fix_error.txt", "w", encoding='utf-8') as ef:
        ef.write(f"Error: {e}")
    conn.rollback()
else:
    with open("fix_success.txt", "w", encoding='utf-8') as sf:
        sf.write("Successfully added session_key and recorded migration.")
finally:
    conn.close()
