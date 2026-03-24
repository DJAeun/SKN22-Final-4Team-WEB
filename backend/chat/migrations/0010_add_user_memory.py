"""
Create user_memory table for per-user extracted facts (pgvector + HNSW index).
Also ensure hari_knowledge has is_active / updated_at columns needed by the
memory-extraction pipeline (safe no-ops if those columns already exist from
setup_db_schema.py or the ingest script).
"""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('chat', '0009_add_summary_vector'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                -- ── user_memory ────────────────────────────────────────────
                CREATE TABLE IF NOT EXISTS user_memory (
                    id              BIGSERIAL PRIMARY KEY,
                    user_id         BIGINT       NOT NULL
                                    REFERENCES auth_user(id) ON DELETE CASCADE,
                    category        TEXT         NOT NULL,
                    trait_key       TEXT         NOT NULL,
                    trait_value     TEXT         NOT NULL,
                    importance      SMALLINT     NOT NULL DEFAULT 5
                                    CHECK (importance BETWEEN 1 AND 10),
                    content_vector  VECTOR(1536),
                    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
                    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
                );

                -- Fast lookup by user + active status
                CREATE INDEX IF NOT EXISTS idx_user_memory_user_active
                    ON user_memory (user_id, is_active);

                -- HNSW index for cosine similarity search
                CREATE INDEX IF NOT EXISTS idx_user_memory_vector_hnsw
                    ON user_memory
                    USING hnsw (content_vector vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64);

                -- ── hari_knowledge safety columns ──────────────────────────
                -- These may already exist from ingest_to_pgvector.py /
                -- setup_db_schema.py; IF NOT EXISTS guards make this idempotent.
                ALTER TABLE hari_knowledge
                    ADD COLUMN IF NOT EXISTS is_active   BOOLEAN     NOT NULL DEFAULT TRUE,
                    ADD COLUMN IF NOT EXISTS updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW();
            """,
            reverse_sql="""
                DROP TABLE IF EXISTS user_memory;
            """,
        ),
    ]
