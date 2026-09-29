from django.db import migrations

TASK_NAME = 'api.tasks.cleanup_stale_chunked_uploads'
OLD_NAME = 'Nettoyage des envois FASTQ abandonnés'
NEW_NAME = 'Cleanup abandoned FASTQ uploads'


def rename_forward(apps, schema_editor):
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')
    PeriodicTask.objects.filter(task=TASK_NAME, name=OLD_NAME).update(name=NEW_NAME)


def rename_backward(apps, schema_editor):
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')
    PeriodicTask.objects.filter(task=TASK_NAME, name=NEW_NAME).update(name=OLD_NAME)


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0006_alter_chunkedupload_options_alter_manualrun_options_and_more'),
    ]

    operations = [
        migrations.RunPython(rename_forward, rename_backward),
    ]
