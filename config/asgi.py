import os
from django.core.asgi import get_asgi_application as _app
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = _app()
