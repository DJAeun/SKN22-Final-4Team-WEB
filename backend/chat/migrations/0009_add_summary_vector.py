"""
Add summary_vector column (pgvector VECTOR(1536)) and HNSW index
to chat_memory for semantic conversation recall.
"""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('chat', '0008_fix_visit_logs'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE chat_memory
                ADD COLUMN IF NOT EXISTS summary_vector VECTOR(1536);

                CREATE INDEX IF NOT EXISTS idx_chat_memory_summary_hnsw
                ON chat_memory
                USING hnsw (summary_vector vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS idx_chat_memory_summary_hnsw;
                ALTER TABLE chat_memory DROP COLUMN IF EXISTS summary_vector;
            """,
        ),
    ]
