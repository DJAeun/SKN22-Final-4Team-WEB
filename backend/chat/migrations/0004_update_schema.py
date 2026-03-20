from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0003_remove_chatsession_session_key'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                -- Create tables if they don't exist yet (safe on fresh DBs)
                CREATE TABLE IF NOT EXISTS chat_messages (
                    message_id   BIGSERIAL    PRIMARY KEY,
                    user_id      BIGINT       NULL REFERENCES auth_user(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,
                    sender_type  BOOLEAN      NOT NULL DEFAULT FALSE,
                    content      TEXT         NOT NULL DEFAULT '',
                    is_read      BOOLEAN      NOT NULL DEFAULT FALSE,
                    count        SMALLINT     NOT NULL DEFAULT 0,
                    anonymous_id VARCHAR(40)  NULL,
                    created_at   TIMESTAMP    NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Seoul')
                );

                CREATE TABLE IF NOT EXISTS chat_memory (
                    memory_id    BIGSERIAL    PRIMARY KEY,
                    user_id      BIGINT       NULL REFERENCES auth_user(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,
                    summary      TEXT         NULL,
                    keywords     VARCHAR(500) NULL,
                    ended_at     TIMESTAMP    NULL,
                    anonymous_id VARCHAR(40)  NULL
                );

                -- Drop session_id from chat_messages (CASCADE removes FK constraint automatically)
                ALTER TABLE chat_messages DROP COLUMN IF EXISTS session_id CASCADE;

                -- Drop session_id from chat_memory (CASCADE removes FK constraint automatically)
                ALTER TABLE chat_memory DROP COLUMN IF EXISTS session_id CASCADE;

                -- Add count column (message sequence number per user)
                ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS count SMALLINT NOT NULL DEFAULT 0;

                -- Drop chat_session table (replaced by chat_memory)
                DROP TABLE IF EXISTS chat_session CASCADE;

                -- Add anonymous_id for tracking anonymous users via Django session key
                ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS anonymous_id VARCHAR(40) NULL;
                ALTER TABLE chat_memory   ADD COLUMN IF NOT EXISTS anonymous_id VARCHAR(40) NULL;

                -- Drop leftover duplicate tables from old Django migrations
                DROP TABLE IF EXISTS chat_message CASCADE;
                DROP TABLE IF EXISTS chat_chatsession CASCADE;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
