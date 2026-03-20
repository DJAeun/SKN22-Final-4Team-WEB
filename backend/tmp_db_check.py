import os
import psycopg
from dotenv import load_dotenv
from pathlib import Path

def check_db():
    BASE_DIR = Path(__file__).resolve().parent
    load_dotenv(BASE_DIR / '.env')
    load_dotenv(BASE_DIR.parent / '.env')

    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = os.environ.get("DB_PORT", "5432")
    db_name = os.environ.get("DB_NAME", "hari_persona")
    db_user = os.environ.get("DB_USER", "postgres")
    db_password = os.environ.get("DB_PASSWORD", "")
    
    conninfo = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?sslmode=require"
    
    try:
        with psycopg.connect(conninfo=conninfo) as conn:
            with conn.cursor() as cur:
                print("--- chat_messages Schema ---")
                cur.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'chat_messages'
                """)
                for row in cur.fetchall():
                    print(row)
                
                print("\n--- Recent Messages ---")
                cur.execute("SELECT * FROM chat_messages ORDER BY created_at DESC LIMIT 5")
                for row in cur.fetchall():
                    print(row)
                    
                print("\n--- Checkpoints (LangGraph Tables) ---")
                cur.execute("SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'checkpoint%'")
                for row in cur.fetchall():
                    print(row)
                    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db()
