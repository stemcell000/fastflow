from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
from django.template.loader import render_to_string
from .models import Setting
from django.db.models import Q

@shared_task
def send_reminders():
    """
        Nothing yet ...
    """
    