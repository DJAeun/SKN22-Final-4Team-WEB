from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rpg', '0003_chatlog_status_snapshot'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatlog',
            name='image_command',
            field=models.CharField(
                blank=True,
                help_text='Validated image command for this message, e.g. "daily_thinking"',
                max_length=100,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='chatlog',
            name='image_url',
            field=models.CharField(
                blank=True,
                help_text='Resolved character image URL for this message',
                max_length=500,
                null=True,
            ),
        ),
    ]
