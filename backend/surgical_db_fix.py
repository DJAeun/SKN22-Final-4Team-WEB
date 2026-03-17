
import sqlite3
import os

db_path = 'db.sqlite3'
print(f"Applying surgical fix to {db_path}...")

try:
    conn = sqlite3.connect(db_path, timeout=10)
    cursor = conn.cursor()
    
    # 1. Get original schema
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='chat_chatsession';")
    original_sql = cursor.fetchone()[0]
    print(f"Original SQL: {original_sql}")
    
    # 2. Modify SQL to make user_id NULL
    # Original usually looks like: CREATE TABLE "chat_chatsession" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, ...)
    # We want to replace "user_id" integer NOT NULL with "user_id" integer
    
    new_sql = original_sql.replace('"user_id" integer NOT NULL', '"user_id" integer')
    # Also handle alternate formats
    new_sql = new_sql.replace('user_id integer NOT NULL', 'user_id integer')
    
    print(f"New SQL: {new_sql}")
    
    if new_sql == original_sql:
        print("Schema already matches or replacement failed. No changes made.")
    else:
        # Move data
        cursor.execute("BEGIN TRANSACTION;")
        cursor.execute("ALTER TABLE chat_chatsession RENAME TO chat_chatsession_old;")
        cursor.execute(new_sql)
        cursor.execute("INSERT INTO chat_chatsession SELECT * FROM chat_chatsession_old;")
        cursor.execute("DROP TABLE chat_chatsession_old;")
        conn.commit()
        print("Success! Table recreated with nullable user_id.")
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
    if 'conn' in locals():
        conn.rollback()
        conn.close()
