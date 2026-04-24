from django.db import models
from django.conf import settings
from datetime import datetime
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
import random
from datetime import datetime
from django.dispatch import receiver
    
class Setting(models.Model):
    key = models.CharField( _('Key'), max_length=50, unique=True)
    name = models.CharField(_("Name"), unique=True, default="")
    value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.key}: {self.value}"

class Sample(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Sample'
        verbose_name_plural = 'Samples'

    def __str__(self):
        return f"Sample {self.id}"


class Protocol(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    sample = models.ForeignKey(
        Sample,
        on_delete=models.CASCADE,
        related_name='protocols'
    )

    class Meta:
        verbose_name = 'Protocol'

    def __str__(self):
        return f"Protocol {self.id}"


class NGSSample(models.Model):
    protocol = models.ForeignKey(
        Protocol,
        on_delete=models.CASCADE,
        related_name='ngs_samples'
    )

    class Meta:
        verbose_name = 'NGS Sample'
        db_table = 'ngs_samples'

    def __str__(self):
        return f"NGS Sample {self.id}"


class SequencingBatch(models.Model):
    ngs_sample = models.ForeignKey(
        NGSSample,
        on_delete=models.CASCADE,
        related_name='sequencing_batches'
    )

    class Meta:
        verbose_name = 'Sequencing Batch'
        db_table = 'sequencing_batches'

    def __str__(self):
        return f"Batch {self.id}"


class SequencingBatchFile(models.Model):
    sequencing_batch = models.ForeignKey(
        SequencingBatch,
        on_delete=models.CASCADE,
        related_name='files'
    )
    file = models.FileField(upload_to='sequencing_batches/')

    class Meta:
        verbose_name = 'Sequencing Batch File'
        db_table = 'sequencing_batch_files'


class SequencingProduct(models.Model):
    sequencing_batch = models.ForeignKey(
        SequencingBatch,
        on_delete=models.CASCADE,
        related_name='products'
    )

    class Meta:
        verbose_name = 'Sequencing Product'
        db_table = 'sequencing_products'

    def __str__(self):
        return f"Product {self.id}"


class Fastq(models.Model):
    sequencing_product = models.ForeignKey(
        SequencingProduct,
        on_delete=models.CASCADE,
        related_name='fastqs'
    )

    class Meta:
        verbose_name = 'FASTQ'
        verbose_name_plural = 'FASTQs'
        db_table = 'fastq'

    def __str__(self):
        return f"FASTQ {self.id}"


class FastqFile(models.Model):
    fastq = models.ForeignKey(
        Fastq,
        on_delete=models.CASCADE,
        related_name='files'
    )
    file = models.FileField(upload_to='fastq/')

    class Meta:
        verbose_name = 'FASTQ File'
        db_table = 'fastq_file'


class Pipeline(models.Model):
    fastq = models.ForeignKey(
        Fastq,
        on_delete=models.CASCADE,
        related_name='pipelines'
    )

    class Meta:
        verbose_name = 'Pipeline'
        db_table = 'pipelines'

    def __str__(self):
        return f"Pipeline {self.id}"


class Script(models.Model):
    pipeline = models.ForeignKey(
        Pipeline,
        on_delete=models.CASCADE,
        related_name='scripts'
    )

    class Meta:
        verbose_name = 'Script'
        db_table = 'scripts'

    def __str__(self):
        return f"Script {self.id}"


class Setting(models.Model):
    script = models.ForeignKey(
        Script,
        on_delete=models.CASCADE,
        related_name='settings'
    )

    class Meta:
        verbose_name = 'Setting'
        db_table = 'settings'

    def __str__(self):
        return f"Setting {self.id}"


class Count(models.Model):
    pipeline = models.ForeignKey(
        Pipeline,
        on_delete=models.CASCADE,
        related_name='counts'
    )

    class Meta:
        verbose_name = 'Count'
        db_table = 'counts'

    def __str__(self):
        return f"Count {self.id}"

    