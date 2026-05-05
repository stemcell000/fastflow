import os
from celery import Celery

# Indique à Celery quel settings Django utiliser
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')

# Charge la configuration Celery depuis Django settings (clés préfixées CELERY_)
app.config_from_object('django.conf:settings', namespace='CELERY')

# Découverte automatique des tâches dans les fichiers tasks.py de chaque app
app.autodiscover_tasks()