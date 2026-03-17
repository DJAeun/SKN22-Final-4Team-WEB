
import sqlite3
import os
import subprocess

db_path = 'db.sqlite3'
print(f"--- Nuclear Database Fix for 'chat' app ---")

try:
    conn = sqlite3.connect(db_path, timeout=10)
    cursor = conn.cursor()
    
    # 1. Disable foreign keys temporarily
    cursor.execute("PRAGMA foreign_keys = OFF;")
    
    # 2. Get list of tables to clear
    tables_to_clear = ['chat_message', 'chat_chatsession']
    
    for table in tables_to_clear:
        print(f"Checking table {table}...")
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}';")
        if cursor.fetchone():
            print(f"Clearing and dropping {table}...")
            cursor.execute(f"DROP TABLE {table};")
    
    # Also drop the renamed legacy table if it exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chat_chatsession_old';")
    if cursor.fetchone():
        print("Dropping chat_chatsession_old...")
        cursor.execute("DROP TABLE chat_chatsession_old;")

    # 3. Clear migration history for 'chat' app to allow clean start
    print("Clearing migration history for 'chat' app...")
    cursor.execute("DELETE FROM django_migrations WHERE app='chat';")
    
    conn.commit()
    conn.close()
    print("Database cleared. Now running Django migrations...")
    
    # 4. Run migrations
    subprocess.run(["python", "manage.py", "makemigrations", "chat"], check=True)
    subprocess.run(["python", "manage.py", "migrate", "chat"], check=True)
    
    print("\n--- Success! Database is now clean and synced. ---")
    print("You can now restart your server.")

except Exception as e:
    print(f"Error: {e}")
    if 'conn' in locals():
        conn.close()
