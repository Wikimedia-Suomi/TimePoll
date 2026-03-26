import os

from django.core.asgi import get_asgi_application

from timepoll.runtime_guard import install_runtime_audit_guard

install_runtime_audit_guard()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "timepoll.settings")

application = get_asgi_application()
