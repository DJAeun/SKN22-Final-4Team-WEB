from django.db import migrations


class Migration(migrations.Migration):
    """
    Fixes chat_messages and chat_memory FK constraints on existing databases.
    0006 used CREATE TABLE IF NOT EXISTS, so existing tables kept the old FK
    pointing to users.user_id instead of auth_user.id — causing silent FK
    violations on every Message.objects.create() call for authenticated users.
    """

    dependencies = [
        ('chat', '0006_ensure_tables'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                -- chat_messages: drop old FK (whatever it's named) and re-add pointing to auth_user
                ALTER TABLE chat_messages DROP CONSTRAINT IF EXISTS chat_messages_user_id_fkey;
                ALTER TABLE chat_messages ADD CONSTRAINT chat_messages_user_id_fkey
                    FOREIGN KEY (user_id) REFERENCES auth_user(id)
                    ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;

                -- chat_memory: same fix
                ALTER TABLE chat_memory DROP CONSTRAINT IF EXISTS chat_memory_user_id_fkey;
                ALTER TABLE chat_memory ADD CONSTRAINT chat_memory_user_id_fkey
                    FOREIGN KEY (user_id) REFERENCES auth_user(id)
                    ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
