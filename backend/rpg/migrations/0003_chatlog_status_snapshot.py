from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rpg', '0002_lorebook_is_constant_lorebook_priority_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatlog',
            name='status_snapshot',
            field=models.JSONField(blank=True, help_text='Parsed in-game status snapshot for this message', null=True),
        ),
    ]
