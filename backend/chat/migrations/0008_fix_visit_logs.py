from django.db import migrations


class Migration(migrations.Migration):
    """
    Fix visit_logs table:
    1. FK user_id -> auth_user(id) instead of users(user_id)
    2. Make user_id nullable for anonymous visitors
    3. Set visit_time default to KST
    """

    dependencies = [
        ('chat', '0007_fix_fk_to_auth_user'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                -- Fix FK: users -> auth_user
                ALTER TABLE visit_logs DROP CONSTRAINT IF EXISTS visit_logs_user_id_fkey;
                ALTER TABLE visit_logs
                    ADD CONSTRAINT visit_logs_user_id_fkey
                    FOREIGN KEY (user_id) REFERENCES auth_user(id)
                    ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;

                -- Make user_id nullable (for anonymous visitors)
                ALTER TABLE visit_logs ALTER COLUMN user_id DROP NOT NULL;

                -- Change visit_time default to KST
                ALTER TABLE visit_logs
                    ALTER COLUMN visit_time SET DEFAULT (NOW() AT TIME ZONE 'Asia/Seoul');
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
