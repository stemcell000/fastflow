from django.db import migrations

TASK_NAME = 'api.tasks.cleanup_stale_chunked_uploads'


def create_periodic_task(apps, schema_editor):
    IntervalSchedule = apps.get_model('django_celery_beat', 'IntervalSchedule')
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')

    schedule, _ = IntervalSchedule.objects.get_or_create(every=1, period='days')
    PeriodicTask.objects.get_or_create(
        task=TASK_NAME,
        defaults={
            'name': 'Nettoyage des envois FASTQ abandonnés',
            'interval': schedule,
            'enabled': True,
        },
    )


def remove_periodic_task(apps, schema_editor):
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')
    PeriodicTask.objects.filter(task=TASK_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_alter_script_options_remove_pipelinestep_script_file_and_more'),
        ('django_celery_beat', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_periodic_task, remove_periodic_task),
    ]
