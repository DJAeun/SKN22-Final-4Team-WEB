from django.db import migrations


def set_site_domain(apps, schema_editor):
    Site = apps.get_model('sites', 'Site')
    Site.objects.update_or_create(
        id=1,
        defaults={'domain': 'chatting-hari.com', 'name': 'HARI'},
    )


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0011_drop_user_memory_alter_user_persona'),
        ('sites', '0002_alter_domain_unique'),
    ]

    operations = [
        migrations.RunPython(set_site_domain, migrations.RunPython.noop),
    ]
