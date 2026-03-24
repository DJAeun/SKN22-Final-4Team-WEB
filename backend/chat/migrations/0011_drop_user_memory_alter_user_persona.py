"""
Drop user_memory table and reshape user_persona to match its schema:
  - Rename keyword → trait_key, add trait_value, category, importance, etc.
  - Add content_vector VECTOR(1536) + HNSW index
  - Add is_active, updated_at columns
  - Drop old weight column (integer → replaced by importance)
"""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('chat', '0010_add_user_memory'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                -- ── Drop user_memory (replaced by user_persona) ──────────
                DROP TABLE IF EXISTS user_memory;

                -- ── Reshape user_persona ─────────────────────────────────
                -- Rename keyword → trait_key
                ALTER TABLE user_persona
                    RENAME COLUMN keyword TO trait_key;

                -- Change trait_key type from varchar to text
                ALTER TABLE user_persona
                    ALTER COLUMN trait_key TYPE TEXT;

                -- Rename weight → importance and change type to smallint
                ALTER TABLE user_persona
                    RENAME COLUMN weight TO importance;
                ALTER TABLE user_persona
                    ALTER COLUMN importance TYPE SMALLINT USING COALESCE(importance, 5)::SMALLINT,
                    ALTER COLUMN importance SET NOT NULL,
                    ALTER COLUMN importance SET DEFAULT 5;
                ALTER TABLE user_persona
                    ADD CONSTRAINT chk_user_persona_importance
                    CHECK (importance BETWEEN 1 AND 10);

                -- Add new columns
                ALTER TABLE user_persona
                    ADD COLUMN IF NOT EXISTS category       TEXT NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS trait_value     TEXT NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS content_vector  VECTOR(1536),
                    ADD COLUMN IF NOT EXISTS is_active       BOOLEAN NOT NULL DEFAULT TRUE,
                    ADD COLUMN IF NOT EXISTS updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW();

                -- Change created_at to timestamptz
                ALTER TABLE user_persona
                    ALTER COLUMN created_at TYPE TIMESTAMPTZ
                    USING COALESCE(created_at, NOW());

                -- FK constraint if not already present
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'user_persona_user_id_fkey'
                    ) THEN
                        ALTER TABLE user_persona
                            ADD CONSTRAINT user_persona_user_id_fkey
                            FOREIGN KEY (user_id) REFERENCES auth_user(id) ON DELETE CASCADE;
                    END IF;
                END $$;

                -- Indexes
                CREATE INDEX IF NOT EXISTS idx_user_persona_user_active
                    ON user_persona (user_id, is_active);

                CREATE INDEX IF NOT EXISTS idx_user_persona_vector_hnsw
                    ON user_persona
                    USING hnsw (content_vector vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64);
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS idx_user_persona_vector_hnsw;
                DROP INDEX IF EXISTS idx_user_persona_user_active;
                ALTER TABLE user_persona DROP CONSTRAINT IF EXISTS chk_user_persona_importance;
                ALTER TABLE user_persona DROP COLUMN IF EXISTS updated_at;
                ALTER TABLE user_persona DROP COLUMN IF EXISTS is_active;
                ALTER TABLE user_persona DROP COLUMN IF EXISTS content_vector;
                ALTER TABLE user_persona DROP COLUMN IF EXISTS trait_value;
                ALTER TABLE user_persona DROP COLUMN IF EXISTS category;
                ALTER TABLE user_persona RENAME COLUMN importance TO weight;
                ALTER TABLE user_persona
                    ALTER COLUMN weight TYPE INTEGER,
                    ALTER COLUMN weight DROP NOT NULL,
                    ALTER COLUMN weight DROP DEFAULT;
                ALTER TABLE user_persona RENAME COLUMN trait_key TO keyword;
                ALTER TABLE user_persona
                    ALTER COLUMN keyword TYPE CHARACTER VARYING;
            """,
        ),
    ]
