import os
from django.core.wsgi import get_wsgi_application as _app

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = _app()
app = application
