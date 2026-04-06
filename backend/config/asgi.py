import os
from pathlib import Path
from dotenv import load_dotenv
import django

# 1. Setup Environment
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 2. Initialize Django
django.setup()

# 3. Import Channels & Routing (AFTER django.setup)
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import chat.routing
import roleplay.routing

# 4. Define Application
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            chat.routing.websocket_urlpatterns + 
            roleplay.routing.websocket_urlpatterns
        )
    ),
})
