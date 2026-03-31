from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0012_set_site_domain'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS session_id VARCHAR(255) NULL;
                ALTER TABLE chat_memory  ADD COLUMN IF NOT EXISTS session_id VARCHAR(255) NULL;
            """,
            reverse_sql="""
                ALTER TABLE chat_messages DROP COLUMN IF EXISTS session_id;
                ALTER TABLE chat_memory  DROP COLUMN IF EXISTS session_id;
            """,
        ),
    ]
