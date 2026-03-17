import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

print(f"DATABASE: {settings.DATABASES['default']['ENGINE']}")
print(f"DB_NAME: {settings.DATABASES['default']['NAME']}")
print(f"CHANNEL_LAYERS: {settings.CHANNEL_LAYERS['default']['BACKEND']}")
if 'CONFIG' in settings.CHANNEL_LAYERS['default']:
    print(f"CHANNEL_CONFIG: {settings.CHANNEL_LAYERS['default']['CONFIG']}")
