# crm/context_processors.py
import os
from django.conf import settings

def global_logo_path(request):
    # First try STATIC_ROOT (production), fallback to STATICFILES_DIRS[0] (local dev)
    logo_path = os.path.join(settings.STATIC_ROOT, "images/logo.png")
    if not os.path.exists(logo_path):
        # fallback for local dev
        logo_path = os.path.join(settings.STATICFILES_DIRS[0], "images/logo.png")
    return {"logo_path": logo_path}
