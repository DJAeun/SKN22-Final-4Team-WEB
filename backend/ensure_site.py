import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.sites.models import Site

# Ensure Site ID 1 exists (needed for dj-rest-auth and allauth)
site_id = 1
domain = os.environ.get('SITE_DOMAIN', 'chating-hari.com')
name = 'Chating Hari'

site, created = Site.objects.get_or_create(
    id=site_id,
    defaults={'domain': domain, 'name': name}
)

if not created:
    site.domain = domain
    site.name = name
    site.save()

print(f"✅ Site setup completed for ID {site_id} ({domain})")
