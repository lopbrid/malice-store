import os
import sys

# Add your project directory to the sys.path
path = '/home/yourusername/malice_ecommproj'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()