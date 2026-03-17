
import sqlite3
import os

db_path = 'db.sqlite3'
log_path = 'migration_log.txt'

with open(log_path, 'w', encoding='utf-8') as f:
    if not os.path.exists(db_path):
        f.write(f"Database not found at {db_path}\n")
    else:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("PRAGMA table_info(chat_chatsession);")
            columns = cursor.fetchall()
            f.write("Columns in chat_chatsession:\n")
            for col in columns:
                f.write(f"{col}\n")
                
            cursor.execute("SELECT name FROM django_migrations WHERE app='chat';")
            migrations = cursor.fetchall()
            f.write("\nApplied migrations for 'chat':\n")
            for m in migrations:
                f.write(f"{m}\n")
                
        except Exception as e:
            f.write(f"Error: {e}\n")
        finally:
            conn.close()
    f.write("\nFinished.\n")
