from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0013_add_session_id_columns'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE chat_messages
                    ADD COLUMN IF NOT EXISTS used_web_search BOOLEAN NOT NULL DEFAULT FALSE;
            """,
            reverse_sql="""
                ALTER TABLE chat_messages DROP COLUMN IF EXISTS used_web_search;
            """,
        ),
    ]
