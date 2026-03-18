from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0003_remove_chatsession_session_key'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                -- Drop session_id from chat_messages (CASCADE removes FK constraint automatically)
                ALTER TABLE chat_messages DROP COLUMN IF EXISTS session_id CASCADE;

                -- Drop session_id from chat_memory (CASCADE removes FK constraint automatically)
                ALTER TABLE chat_memory DROP COLUMN IF EXISTS session_id CASCADE;

                -- Add count column (message sequence number per user)
                ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS count SMALLINT NOT NULL DEFAULT 0;

                -- Drop chat_session table (replaced by chat_memory)
                DROP TABLE IF EXISTS chat_session CASCADE;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
