
import os
from django.conf import settings

def global_logo_path(request):
    return {
        'logo_path': os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')
    }
