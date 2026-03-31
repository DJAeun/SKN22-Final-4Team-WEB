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

    cur.execute("DROP TABLE IF EXISTS GENERATED_CONTENTS;")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS GENERATED_CONTENTS (
        content_id      BIGSERIAL PRIMARY KEY,
        title           VARCHAR(255),
        platform        VARCHAR(50),
        script_text     TEXT NOT NULL,
        summary         TEXT,
        tags            TEXT[],
        thumbnail_url   VARCHAR(500),
        content_url     VARCHAR(500),
        is_published    BOOLEAN DEFAULT FALSE,
        content_vector  VECTOR(1536),
        uploaded_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_generated_contents_hnsw
    ON GENERATED_CONTENTS
    USING hnsw (content_vector vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
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
        is_read BOOLEAN DEFAULT FALSE,
        count SMALLINT DEFAULT 0,
        session_id VARCHAR(255) REFERENCES CHAT_SESSION(session_id) ON DELETE CASCADE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS CHAT_MEMORY (
        memory_id BIGSERIAL PRIMARY KEY,
        user_id BIGINT REFERENCES USERS(user_id) ON DELETE CASCADE,
        session_id VARCHAR(255) REFERENCES CHAT_SESSION(session_id) ON DELETE CASCADE,
        summary TEXT,
        keywords VARCHAR(500),
        ended_at TIMESTAMP
    );
    """)

    # Migrate existing CHAT_MESSAGES: add missing 'count' column, drop unused 'anonymous_id'
    cur.execute("""
    ALTER TABLE chat_messages
    ADD COLUMN IF NOT EXISTS count SMALLINT DEFAULT 0;
    """)
    cur.execute("""
    ALTER TABLE chat_messages
    ALTER COLUMN is_read SET DEFAULT FALSE;
    """)
    cur.execute("""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'chat_messages' AND column_name = 'anonymous_id'
        ) THEN
            ALTER TABLE chat_messages DROP COLUMN anonymous_id;
        END IF;
    END $$;
    """)

    # Migrate existing CHAT_MEMORY: drop unused 'anonymous_id', expand keywords
    cur.execute("""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'chat_memory' AND column_name = 'anonymous_id'
        ) THEN
            ALTER TABLE chat_memory DROP COLUMN anonymous_id;
        END IF;
    END $$;
    """)
    cur.execute("""
    ALTER TABLE chat_memory
    ALTER COLUMN keywords TYPE VARCHAR(500);
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
        print("[OK] Schema created successfully!")
        
    except Exception as e:
        print(f"[ERROR] Error setting up schema: {e}")
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
