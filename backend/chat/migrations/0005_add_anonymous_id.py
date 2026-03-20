from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0004_update_schema'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS anonymous_id VARCHAR(40) NULL;
                ALTER TABLE chat_memory   ADD COLUMN IF NOT EXISTS anonymous_id VARCHAR(40) NULL;

                DROP TABLE IF EXISTS chat_message CASCADE;
                DROP TABLE IF EXISTS chat_chatsession CASCADE;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
