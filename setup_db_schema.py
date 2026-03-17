import os
import psycopg2
from dotenv import load_dotenv
from langsmith import traceable

# Load environment variables
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "hari_persona")
DB_USER = os.getenv("DB_USER", "hari")
DB_PASSWORD = os.getenv("DB_PASSWORD")

def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        sslmode='require'
    )

@traceable(name="create_pgvector_extension")
def create_pgvector_extension(cur):
    print("Creating pgvector extension...")
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

@traceable(name="create_tables")
def create_tables(cur):
    print("Creating tables...")
    
    # 1. Independent Tables (No Foreign Keys or parents of many)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS USERS (
        user_id BIGSERIAL PRIMARY KEY,
        role VARCHAR(50),
        provider VARCHAR(50),
        social_id VARCHAR(255),
        nickname VARCHAR(100),
        profile_image VARCHAR(255),
        premium_grade SMALLINT,
        user_point BIGINT,
        refresh_tokn VARCHAR(255),
        is_blocked BOOLEAN,
        is_logged_in BOOLEAN,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS PRODUCTS (
        product_id BIGSERIAL PRIMARY KEY,
        name VARCHAR(255),
        price INT,
        premium_only_grade SMALLINT,
        is_active BOOLEAN,
        released_time TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS CHAT_SESSION (
        session_id VARCHAR(255) PRIMARY KEY,
        is_active BOOLEAN,
        user_id BIGINT  -- No explicit FK in ERD diagram notation, but conceptually links to USERS
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS GENERATED_CONTENTS (
        task_id BIGSERIAL PRIMARY KEY,
        task_type VARCHAR(100),
        status BOOLEAN,
        result_url VARCHAR(500),
        prompt_text TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # The 'hari_knowledge' table already exists in the database.
    # We will ensure that it has the 'is_active' and 'updated_at' columns.
    cur.execute("""
    ALTER TABLE hari_knowledge 
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    """)

    # 2. Level 1 Dependent Tables (Foreign Keys to Independent Tables)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS VISIT_LOGS (
        log_id BIGSERIAL PRIMARY KEY,
        user_id BIGINT REFERENCES USERS(user_id) ON DELETE CASCADE,
        visit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS SUBSCRIPTION_PAYMENTS (
        payment_id BIGSERIAL PRIMARY KEY,
        user_id BIGINT REFERENCES USERS(user_id) ON DELETE CASCADE,
        payment_type VARCHAR(100),
        amount INT,
        paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        valid_until TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS POSTS (
        post_id BIGSERIAL PRIMARY KEY,
        admin_id BIGINT REFERENCES USERS(user_id),
        title VARCHAR(255),
        content_body TEXT,
        media_url VARCHAR(500),
        media_type VARCHAR(50),
        premium_only_grade SMALLINT,
        is_published BOOLEAN,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS CHAT_MESSAGES (
        message_id BIGSERIAL PRIMARY KEY,
        user_id BIGINT REFERENCES USERS(user_id) ON DELETE CASCADE,
        sender_type BOOLEAN,
        content TEXT,
        is_read BOOLEAN,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        session_id VARCHAR(255) REFERENCES CHAT_SESSION(session_id) ON DELETE CASCADE
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS CHAT_MEMORY (
        memory_id BIGSERIAL PRIMARY KEY,
        user_id BIGINT REFERENCES USERS(user_id) ON DELETE CASCADE,
        session_id VARCHAR(255) REFERENCES CHAT_SESSION(session_id) ON DELETE CASCADE,
        summary TEXT,
        keywords VARCHAR(255),
        ended_at TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS USER_PERSONA (
        persona_id BIGSERIAL PRIMARY KEY,
        user_id BIGINT REFERENCES USERS(user_id) ON DELETE CASCADE,
        keyword VARCHAR(100),
        weight INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ORDERS (
        order_id BIGSERIAL PRIMARY KEY,
        user_id BIGINT REFERENCES USERS(user_id) ON DELETE CASCADE,
        total_amount INT,
        order_status VARCHAR(50),
        ordered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 3. Level 2 Dependent Tables (Foreign Keys to Level 1 Dependent Tables)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ORDER_ITEMS (
        order_item_id BIGSERIAL PRIMARY KEY,
        order_id BIGINT REFERENCES ORDERS(order_id) ON DELETE CASCADE,
        product_id BIGINT REFERENCES PRODUCTS(product_id),
        quantity INT,
        price_at_purchase INT
    );
    """)

@traceable(name="setup_database_schema")
def main():
    print("Starting database schema setup...")
    conn = None
    try:
        conn = get_connection()
        conn.autocommit = False
        cur = conn.cursor()

        create_pgvector_extension(cur)
        create_tables(cur)

        # Commit transactions
        conn.commit()
        print("✅ Schema created successfully!")
        
    except Exception as e:
        print(f"❌ Error setting up schema: {e}")
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            cur.close()
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    main()
