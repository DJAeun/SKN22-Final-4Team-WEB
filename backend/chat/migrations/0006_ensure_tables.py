from django.db import migrations


class Migration(migrations.Migration):
    """
    Ensures chat_messages, chat_memory, and hari_knowledge tables exist.
    Safe to run on both fresh and existing databases (CREATE TABLE IF NOT EXISTS).
    """

    dependencies = [
        ('chat', '0005_add_anonymous_id'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
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

                CREATE TABLE IF NOT EXISTS hari_knowledge (
                    persona_id   BIGSERIAL    PRIMARY KEY,
                    category     VARCHAR(255) NULL,
                    trait_key    VARCHAR(255) NULL,
                    trait_value  TEXT         NULL,
                    is_active    BOOLEAN      NOT NULL DEFAULT TRUE,
                    updated_at   TIMESTAMP    NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Seoul'),
                    weight       JSONB        NULL
                );
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
