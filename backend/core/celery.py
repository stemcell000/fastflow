import os
from celery import Celery

# Tells Celery which Django settings module to use
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')

# Loads Celery configuration from Django settings (CELERY_-prefixed keys)
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discovers tasks in each app's tasks.py file
app.autodiscover_tasks()
